import os
from openai import OpenAI
from typing import List, Any
import threading
import time
from datetime import datetime
from logging import Logger

from Workers.Reflector.MicroReflector import MicroReflector
from Workers.Reflector.MacroReflector import MacroReflector
from Workers.Reflector.MemorySchema import MicroMemory, MacroMemory
from Layers.L2.L2 import MemoryLayer
from Core.SessionState import ChatMessage
from Core.EventBus import EventBus
from Core.Schema import Event, EventType, EventContentType, EventSource
from Logger import setup_logger
from Config.Config import ReflectorConfig, MemoryReflectorConfig, MicroReflectorConfig, MacroReflectorConfig
from Core.PromptManager import PromptManager

class Reflector:
    """
    Reflector Worker (包装器)
    负责调度 MemoryReflector 在后台运行，不阻塞主对话流程。
    """
    def __init__(self, event_bus: EventBus, 
                 config: ReflectorConfig, 
                 memory_layer: MemoryLayer,  # 传入全局单例
                 prompt_manager: PromptManager
                 ):
        self.config: ReflectorConfig = config
        self.logger: Logger = setup_logger(self.config.logger_name)
        self.bus: EventBus = event_bus
        self.running: bool = False
        
        # 1. 核心反思模块
        self.reflector = MemoryReflector(logger=self.logger.getChild("MemoryReflector"), 
                                         config=self.config.MemoryReflector, 
                                         memory_layer=memory_layer,
                                         prompt_manager=prompt_manager)     # MemoryLayer 是全局单例

        # 2. 缓冲池(用于Micro Reflection)
        self.buffer: List[ChatMessage] = []
        self.buffer_lock = threading.Lock()
        
        # 3. 触发配置
        # TODO 待修改，我想让micro reflector有多种触发模式
        # 比如 1. 空闲10分钟触发 2. buffer满触发 
        # 此处简单的以 buffer 满足一定数量触发
        self.micro_threshold: int = self.config.micro_threshold
        self.macro_interval_seconds: int = self.config.macro_interval_seconds  # 24小时触发一次
        
        self.last_macro_run: datetime = datetime.now()
        
        # 4. 后台线程
        self._worker_thread = None
        self.worker_sleep_interval: float = self.config.worker_sleep_interval  # 后台线程sleep间隔
        
        self.logger.info(">>> Reflector Worker Initialized.")
    
    # =============================================================
    # 接口: 被 DashBoard 调用
    # =============================================================    
    
    def get_status(self) -> dict:
        """获取 Reflector Worker 状态 Dashboard 用"""
        status = {
            "running": self.running,
            "buffer_size": len(self.buffer),
            "micro_threshold": self.micro_threshold,
            "macro_interval_seconds": self.macro_interval_seconds,
            "last_macro_run": self.last_macro_run.strftime("%Y-%m-%d %H:%M:%S"),
            "micro_reflector_status": self.reflector.micro_reflector.get_status(),
            "macro_reflector_status": self.reflector.macro_reflector.get_status(),
        }
        return status
    
    # =============================================================
    # 接口: 被 CheckPointManager 调用
    # =============================================================
    
    def dump_state(self) -> dict:
        """导出当前状态为字典 (供 CheckPointManager 使用)"""
        state = {
            "buffer": [msg.to_dict() for msg in self.buffer],
            "last_macro_run": self.last_macro_run.timestamp(),
            "micro_reflector_state": self.reflector.micro_reflector.dump_state(),
            "macro_reflector_state": self.reflector.macro_reflector.dump_state()
        }
        return state
    
    
    def load_state(self, state: dict):
        """从字典加载状态 (供 CheckPointManager 使用)"""
        with self.buffer_lock:
            self.buffer = [ChatMessage.from_dict(msg_dict) for msg_dict in state.get("buffer", [])]
        
        last_macro_run_ts = state.get("last_macro_run", 0)
        if last_macro_run_ts > 0:
            self.last_macro_run = datetime.fromtimestamp(last_macro_run_ts)
        
        self.reflector.micro_reflector.load_state(state.get("micro_reflector_state", {}))
        self.reflector.macro_reflector.load_state(state.get("macro_reflector_state", {}))

        self.logger.info(">>> Reflector Worker State Loaded from Checkpoint.")
    
    # =============================================================
    # 接口: 被系统调用
    # =============================================================

    def start(self):
        """启动后台监视线程"""
        self.logger.info(">>> Reflector Worker Starting (Background)...")
        self.running = True
        self._worker_thread = threading.Thread(target=self._background_loop, daemon=True)
        self._worker_thread.start()
        self.logger.info(">>> Reflector Worker Started (Background)")


    def stop(self):
        self.logger.info(">>> Reflector Worker Stopping...")
        self.running = False
    
    
    def force_save(self):
        """
        [接口方法] 强制保存当前缓冲区的内容 (例如在系统关闭前调用)
        """
        self.logger.info(">>> Reflector Worker Force Saving Pending Reflections...")
        data_to_process = []
        
        with self.buffer_lock:
            if len(self.buffer) > 0:
                data_to_process = self.buffer[:]
                self.buffer = []
        
        if data_to_process:
            try:
                self.logger.info(f"[Reflector] Running Forced Micro-Reflection on {len(data_to_process)} messages...")
                
                results = self.reflector.run_micro_reflection(conversations=data_to_process)
                self.reflector.micro_reflector.save_reflection_results(results)
                
            except Exception as e:
                self.logger.error(f"[Reflector Error] Forced Micro-reflection failed: {e}")
        else:
            self.logger.info(">>> Reflector Worker No Pending Reflections to Save.")
        self.logger.info(">>> Reflector Worker Forced Save Completed.")

    # =============================================================
    # 接口: 被 Dispatcher 调用
    # =============================================================

    def on_new_message(self, msg: ChatMessage):
        """
        [新增接口] 供 Dispatcher 或 EventBus 调用，将新对话推入缓冲池
        """
        self.logger.info(f"New message received for reflection.")
        self.logger.debug(f"    {msg.to_dict()}")
        with self.buffer_lock:
            self.buffer.append(msg)
            self.logger.info(f"Buffer size: {len(self.buffer)}")

    # =============================================================
    # 内部循环
    # =============================================================

    def _background_loop(self):
        """后台循环：检查缓冲池是否满了，如果满了就执行反思"""
        while self.running:
            # 1. 检查 Micro Reflection 
            if self._should_run_micro():
                self._run_micro_reflection_sync()   # 同步执行

            # 2. 检查 Macro Reflection 
            if self._should_run_macro():
                self._trigger_macro_reflection()    # 异步执行
            
            time.sleep(self.worker_sleep_interval) # 休息一下，避免死循环空转
            
        self.logger.info(">>> Reflector Worker Stopped.")
    
    # =============================================================
    # Micro Reflection 相关方法
    # =============================================================
    
    def _should_run_micro(self) -> bool:
        """策略：判断是否满足微观反思的触发条件"""
        # 当前策略：缓冲区消息数量达到阈值
        with self.buffer_lock:
            return len(self.buffer) >= self.micro_threshold

    def _run_micro_reflection_sync(self):
        """执行：执行微观反思任务 (同步执行，因为很快且需要阻塞buffer处理)"""
        # 1. 获取数据 (原子操作)
        data_to_process = []
        with self.buffer_lock:
            if self.buffer:
                data_to_process = self.buffer[:]
                self.buffer = []
        
        # 2. 执行业务逻辑
        if data_to_process:
            try:
                self.logger.info(f"[Reflector] Running Micro-Reflection on {len(data_to_process)} messages...")
                
                results = self.reflector.run_micro_reflection(
                    conversations=data_to_process, 
                    store_flag=True
                )
                
                self.bus.publish(
                    Event(type=EventType.REFLECTION_DONE, 
                          content_type=EventContentType.TEXT,
                          content=f"Created {len(results)} micro-memories",
                          source=EventSource.REFLECTOR
                    )
                )
            except Exception as e:
                self.logger.error(f"[Reflector Error] Micro-reflection failed: {e}")
    
    # =============================================================
    # Macro Reflection 相关方法
    # =============================================================
    def _should_run_macro(self) -> bool:
        """检查是否应该运行宏观反思"""
        now = datetime.now()
        res = (now - self.last_macro_run).total_seconds() > self.macro_interval_seconds  
        if res:
            self.logger.info("[Reflector] Macro Reflection Triggered by Time Interval.")
        else:
            self.logger.debug("[Reflector] Macro Reflection Not Triggered Yet.")
        return   res
    
    
    def _trigger_macro_reflection(self):
        """ 触发宏观反思 (异步执行) """
        threading.Thread(target=self._run_macro_async).start()
        self.last_macro_run = datetime.now() # 更新状态通常跟随执行动作


    def _run_macro_async(self):
        """异步执行宏观反思"""
        try:
            self.logger.info("[Reflector] Starting Daily Macro-Reflection...")
            # 执行Macro反思
            self.reflector.run_macro_reflection(store_flag=True)
            # 通知系统反思完成
            self.bus.publish(
                Event(type=EventType.REFLECTION_DONE,
                      content_type=EventContentType.TEXT,
                      content="Daily Macro-memory updated",
                      source=EventSource.REFLECTOR
                )
            )
        except Exception as e:
            self.logger.error(f"[Reflector Error] Macro-reflection failed: {e}", exc_info=True)




class MemoryReflector:
    """
    ORP System: MemoryReflector 模块，用于从对话中提取长期记忆节点
    """
    def __init__(self, logger: Logger, 
                 config: MemoryReflectorConfig, 
                 prompt_manager: PromptManager,
                 memory_layer: MemoryLayer):
        self.config: MemoryReflectorConfig = config
        self.logger: Logger = logger
        self.openai_client = OpenAI(api_key=self.config.MicroReflector.LLM_API_KEY, 
                                    base_url=self.config.MicroReflector.LLM_URL)
        
        # 配置openai client
        # TODO 目前micro和macro共用一个client
        micro_client = self.openai_client
        macro_client = self.openai_client
        
        # 配置数据库
        self.milvus_agent = memory_layer  # MemoryLayer 是全局单例
        
        # 配置logger
        micro_logger = self.logger.getChild("MicroReflector")
        macro_logger = self.logger.getChild("MacroReflector")

        self.micro_reflector = MicroReflector(openai_client=micro_client, 
                                              milvus_agent=self.milvus_agent, 
                                              logger=micro_logger,
                                              config=self.config.MicroReflector,
                                              prompt_manager=prompt_manager)
        
        self.macro_reflector = MacroReflector(openai_client=macro_client, 
                                              milvus_agent=self.milvus_agent, 
                                              logger=macro_logger,
                                              config=self.config.MacroReflector,
                                              prompt_manager=prompt_manager)
        
    def run_macro_reflection(self, store_flag: bool = True) -> list[MacroMemory]:
        """运行 Macro 反思，从 Micro Memories 中提炼 Macro Memories"""
        return self.macro_reflector.run_macro_reflection()

    def run_micro_reflection(self, conversations: list[ChatMessage], store_flag: bool = True) -> list[MicroMemory]:
        """运行 Micro 反思，从对话中提取 Micro Memories"""
        micro_memories: list[MicroMemory] = self.micro_reflector.run_micro_reflection(conversations)
        return micro_memories
    

    