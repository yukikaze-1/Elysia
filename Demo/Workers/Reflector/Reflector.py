import os
from dotenv import load_dotenv
from openai import OpenAI
from typing import List, Any
import threading
import time
from datetime import datetime
from logging import Logger

from Workers.Reflector.MicroReflector import MicroReflector, MicroMemory
from Workers.Reflector.MacroReflector import MacroReflector, MacroMemory
from Layers.L2.L2 import MemoryLayer
from Layers.L2.SessionState import ChatMessage
from Core.EventBus import EventBus, global_event_bus
from Core.Schema import Event, EventType, EventContentType, EventSource
from Logger import setup_logger


class Reflector:
    """
    Reflector Worker (包装器)
    负责调度 MemoryReflector 在后台运行，不阻塞主对话流程。
    """
    def __init__(self, event_bus: EventBus = global_event_bus):
        self.logger: Logger = setup_logger("Reflector")
        self.bus: EventBus = event_bus
        self.running: bool = False
        
        # 1. 实例化你的业务逻辑核心
        # 注意：这里我们让 MemoryReflector 自己管理它的 MemoryLayer 连接
        self.reflector = MemoryReflector(self.logger) 

        # 2. 缓冲池
        self.buffer: List[ChatMessage] = []
        self.buffer_lock = threading.Lock()
        
        # 3. 触发配置
        # TODO 待修改，我想让micro reflector有多种触发模式
        # 比如 1. 空闲10分钟触发 2. buffer满触发 
        # 此处简单的以 buffer 满足一定数量触发
        self.micro_threshold: int = 10
        self.macro_interval_seconds: int = 86400  # 24小时触发一次
        
        # TODO 应该写在文件中，记录上次运行时间，每次启动时从文件中读取
        self.last_macro_run: datetime = datetime.now()
        
        # 4. 后台线程
        self._worker_thread = None
        # 后台线程sleep间隔
        self.worker_sleep_interval: float = 2.0  # 2秒
        
        self.logger.info(">>> Reflector Worker Initialized.")
        
    
    def get_status(self) -> dict:
        """获取 Reflector Worker 状态"""
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

    # =========================================
    # 接口: 被 Dispatcher 调用
    # =========================================

    # TODO 思考这个方法以及谁来启动macro reflect
    # def check_and_trigger(self, l2_layer: Any):
    #     """
    #     [接口方法] Dispatcher 每次对话后调用此方法。
    #     注意：Dispatcher 传进来 l2_layer 是为了获取最新的上下文，
    #     但为了解耦，我们最好让 Dispatcher 直接把新发生的对话传进来，
    #     或者让 Reflector 自己去 l2 取。
        
    #     这里我们采用简单的推模式：利用 EventBus 监听或手动添加。
    #     (为了适配之前的 main.py，我们在 add_dialogue 里做实际工作)
    #     """
    #     # 这个方法在当前架构可以是空的，因为我们通过 add_dialogue 收集数据
    #     # 或者在这里检查是否需要运行 Macro 反思
    #     self._check_macro_trigger()


    def on_new_message(self, msg: ChatMessage):
        """
        [新增接口] 供 Dispatcher 或 EventBus 调用，将新对话推入缓冲池
        """
        self.logger.info(f"New message received for reflection.")
        self.logger.debug(f"    {msg.to_dict()}")
        with self.buffer_lock:
            self.buffer.append(msg)
            self.logger.info(f"Buffer size: {len(self.buffer)}")

    # =========================================
    # 内部循环
    # =========================================

    def _background_loop(self):
        """后台循环：检查缓冲池是否满了，如果满了就执行反思"""
        while self.running:
            # 1. 检查 Micro Reflection (基于缓冲数量)
            data_to_process = []
            
            with self.buffer_lock:
                if len(self.buffer) >= self.micro_threshold:
                    # 取出当前缓冲，清空列表
                    data_to_process = self.buffer[:]
                    self.buffer = []
            
            # 如果有数据，执行耗时的反思逻辑 (在锁外面执行，不阻塞写入)
            if data_to_process:
                try:
                    self.logger.info(f"[Reflector] Running Micro-Reflection on {len(data_to_process)} messages...")
                    self.logger.debug(f"Data to process: {data_to_process}")
                    # === 调用你的业务代码 ===
                    # results 是 list[MicroMemory]
                    results = self.reflector.run_micro_reflection(
                        conversations=data_to_process, 
                        store_flag=True
                    )
                    
                    # 通知系统反思完成 (可选)
                    self.bus.publish(
                        Event(type=EventType.REFLECTION_DONE, 
                              content_type=EventContentType.TEXT,
                              content=f"Created {len(results)} micro-memories",
                              source=EventSource.REFLECTOR
                        )
                    )
                    
                except Exception as e:
                    self.logger.error(f"[Reflector Error] Micro-reflection failed: {e}")

            # 2. 检查 Macro Reflection (基于时间，例如每天凌晨)
            # TODO 逻辑在 _check_macro_trigger 中处理
            # 这里的【检查是否需要运行宏观反思】是否应该由dispatcher调用？
            # 毕竟dispatcher有时间心跳，可以更精准地控制
            # 方法： 让dispatcher 决定macro reflector何时运行，
            # 此时往event bus上push一个MACRO REFLECTION START event
            # 算了，到时候问问ai
            # 先测试一下
            self._check_macro_trigger()
            
            time.sleep(self.worker_sleep_interval) # 休息一下，避免死循环空转
            
        self.logger.info(">>> Reflector Worker Stopped.")
        

    def _check_macro_trigger(self):
        """检查是否需要运行宏观反思 (例如: 每天一次)"""
        now = datetime.now()

        if (now - self.last_macro_run).total_seconds() > self.macro_interval_seconds:
            threading.Thread(target=self._run_macro_async).start()
            self.last_macro_run = now


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
            self.logger.error(f"[Reflector Error] Macro-reflection failed: {e}")




class MemoryReflector:
    """
    ORP System: MemoryReflector 模块，用于从对话中提取长期记忆节点
    """
    def __init__(self, logger: Logger):
        self.logger: Logger = logger
        load_dotenv()
        self.openai_client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=os.getenv("DEEPSEEK_API_BETA"))
        
        # 配置openai client
        # TODO 目前micro和macro共用一个client
        micro_client = self.openai_client
        macro_client = self.openai_client
        
        # 配置数据库
        self.micro_memory_collection_name = "micro_memory"
        self.macro_memory_collection_name = "macro_memory"
        self.milvus_agent = MemoryLayer()   # MemoryLayer 是全局单例
        
        # 配置logger
        micro_logger = self.logger.getChild("MicroReflector")
        macro_logger = self.logger.getChild("MacroReflector")

        self.micro_reflector = MicroReflector(openai_client=micro_client, 
                                              milvus_agent=self.milvus_agent, 
                                              collection_name=self.micro_memory_collection_name, 
                                              logger=micro_logger)
        
        self.macro_reflector = MacroReflector(openai_client=macro_client, 
                                              milvus_agent=self.milvus_agent, 
                                              collection_name=self.macro_memory_collection_name, 
                                              logger=macro_logger)

    def run_macro_reflection(self, store_flag: bool = True) -> list[MacroMemory]:
        """运行 Macro 反思，从 Micro Memories 中提炼 Macro Memories"""
        return self.macro_reflector.run_macro_reflection()

    def run_micro_reflection(self, conversations: list[ChatMessage], store_flag: bool = True) -> list[MicroMemory]:
        """运行 Micro 反思，从对话中提取 Micro Memories"""
        micro_memories: list[MicroMemory] = self.micro_reflector.run_micro_reflection(conversations)
        return micro_memories
    

    