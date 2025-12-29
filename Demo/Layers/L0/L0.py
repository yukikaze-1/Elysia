"""
L0 模块：
    1. 感知环境 ---> 输出环境信息
    2. 生成本能反应 ---> 输出本能反应
    
    运行在独立线程中，持续监听用户和环境变化，产生事件推送给 L1 模块。
"""

from openai import OpenAI
from typing import Optional
import threading
import time
import queue
from datetime import datetime
from pydantic import ValidationError

from Layers.L0.Sensor import SensoryProcessor, EnvironmentInformation
from Layers.L0.Amygdala import AmygdalaOutput, Amygdala
from Core.Schema import (Event, EventType, EventContentType, EventSource, 
                              ChatMessage, UserMessage, WebClientMessage, 
                              L0InputSourceType, ExternalInputEvent,
                              L0InternalQueueItem)
from Core.EventBus import EventBus
from Config import L0Config
from Logger import setup_logger



class SensorLayer:
    """L0 模块"""
    def __init__(self, event_bus: EventBus, config: L0Config):
        # 配置
        self.config: L0Config = config
        self.logger = setup_logger(self.config.SensorLayer.logger_name)
        # 初始化 OpenAI 客户端
        self.openai_client: OpenAI = OpenAI(api_key=self.config.SensorLayer.LLM_API_KEY, 
                                            base_url=self.config.SensorLayer.LLM_URL)
        
        amygdala_client = self.openai_client  # 目前使用同一个 LLM 客户端，未来可以分开配置
        amygdala_logger = self.logger.getChild("Amygdala")
        
        sensor_logger = self.logger.getChild("SensoryProcessor")
        
        # 业务组件
        self.sensory_processor: SensoryProcessor = SensoryProcessor(logger=sensor_logger, 
                                                                    config=self.config.Sensor)    # 感官处理器
        self.amygdala: Amygdala = Amygdala(openai_client=amygdala_client, 
                                           logger=amygdala_logger,
                                           config=self.config.Amygdala)         # 本能反应器
        
        # 输入缓冲队列
        self.input_queue: queue.Queue = queue.Queue()
        
        # 对接逻辑
        self.bus: EventBus = event_bus  # 事件总线
        self.running: bool = False
        
        # 线程句柄
        self._processor_thread: Optional[threading.Thread] = None # 新增处理线程

        self.logger.info("L0 SensorLayer initialized.")

    # ===============================================================================================
    # === 对外接口方法 ===
    # ===============================================================================================
    
    def get_status(self) -> dict:
        """获取 L0 模块状态"""
        status = {
            "sensory_processor": self.sensory_processor.get_status(),
            "amygdala": self.amygdala.get_status(),
            "running": self.running,
            "input_queue_size": self.input_queue.qsize()
        }
        return status
    

    def start_threads(self):
        """[接口方法] 启动感知线程"""
        # 防止重复启动
        if self.running:
            return
        
        self.running = True

        # 2. 启动处理线程 (Consumer) 
        self.logger.info("L0 SensorLayer starting processor thread...")
        self._processor_thread = threading.Thread(target=self._input_processing_loop, daemon=True)
        self._processor_thread.start()
        self.logger.info("L0 SensorLayer processor thread started.")

        
    def stop_threads(self):
        """[接口方法] 停止感知"""
        self.running = False
        # 线程会随着 while 循环条件变为 False 而自然结束
        self.logger.info("L0 SensorLayer threads stopping...")
                
                
    def push_external_input(self, data: dict):
        """
        [生产者] 供外部（如 FastAPI, TelegramBot）投喂数据
        """
        # 1. 安全检查
        if not self.running:
            self.logger.warning("L0 SensorLayer is not running. Cannot accept external input.")
            return
        
        # 2. Pydantic 核心校验逻辑
        try:
            event = ExternalInputEvent.model_validate(data)
        except ValidationError as e:
            error_msg = e.json(include_url=False) # include_url=False 去掉文档链接，精简日志
            self.logger.warning(f"Rejected invalid external input: {error_msg}")
            return

        source_enum: L0InputSourceType = event.source
        self.logger.info(f"Received external input from source: {source_enum.value}")
        
        # 4. 推送到内部队列
        self._push_external_input(source_enum, event.model_dump(exclude={"source"}))
            
    
    # =================================================================================================
    # === 内部线程方法 ===
    # =================================================================================================
    
    def _push_external_input(self, source: L0InputSourceType, data: dict):
        """ 根据不同来源构造不同消息类型 """
        #  WebSocket 来源
        if source == L0InputSourceType.WEBSOCKET:
            try:
                # 1. 强校验：如果 data 缺少 content 或 timestamp，这里直接抛出异常
                msg: WebClientMessage = WebClientMessage.model_validate(data)
                
                # 2. 包装成QueueItem
                queue_item = L0InternalQueueItem(
                    source=source,
                    payload=msg
                )
                # 3. 入队
                self.input_queue.put(queue_item)
                self.logger.debug(f"Queued message from {msg.role}: reaction_latency={msg.reaction_latency:.2f}s")

            except ValidationError as e:
                error_msg = e.json(include_url=False)
                self.logger.error(f"Failed to create WebClientMessage: {error_msg}")
                return
        else:
            self.logger.warning(f"Unsupported external input source: {source}. Input ignored.")
                
    def _input_processing_loop(self):
        """
        [消费者] 业务逻辑处理。
        只负责：从队列取数据 -> 感知/情感计算 -> 发送事件
        """
        self.logger.info(">>> Input Processor started")
        while self.running:
            try:
                # 1. 从队列获取输入 (设置 timeout 允许线程定期检查 self.running 状态退出)
                try:
                    input_item: L0InternalQueueItem = self.input_queue.get(timeout=1.0)
                except queue.Empty:
                    continue # 队列为空，继续循环检查 self.running

                # 2. 执行具体的业务逻辑 (封装成单独的方法，代码更清晰)
                self._handle_logic(input_item)
                
                # 3. 标记队列任务完成
                self.input_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Processor Error: {e}", exc_info=True)
                
                
    
    # ===============================================================================================
    # === 内部业务逻辑方法 ===
    # ===============================================================================================      
                
    def _handle_logic(self, item: L0InternalQueueItem):
        """
        处理单条用户输入的业务逻辑
         1. 感官预处理
         2. 杏仁核反应
         3. 封装并发送事件
         现在 input_item 可能是字典(WebSocket)
        """
        self.logger.info("L0 SensorLayer handling new input item...")
        
        # A. 解析数据
        if isinstance(item.payload, WebClientMessage):
            # 来自 WebSocket
            raw_text = item.payload.content
            role = item.payload.role  # 支持前端传角色名
            input_time = item.payload.timestamp # 支持前端传时间戳
        else:
            self.logger.warning(f"Unsupported input payload type: {type(item.payload)}. Skipping.")
            return
        
        if not raw_text:
            self.logger.warning("Empty input text received. Ignoring.")
            return
        
        self.logger.info(f"Processing Text: {raw_text}")

        # B. 感官预处理
        env_info: EnvironmentInformation = self.sensory_processor.active_perception_envs() # 里面存储了ai感知的时间
        user_input = UserMessage(role=role, 
                                 content=raw_text, 
                                 timestamp=input_time) # 用户消息时间 使用前端传来的时间戳
        
        # C. 杏仁核反应
        amygdala_reaction = None
        try:
            amygdala_reaction = self.amygdala.react(
                user_message=user_input,
                current_env=env_info,
                user_reaction_latency=item.payload.reaction_latency
            )
            self.logger.info(f"Amygdala reaction: {amygdala_reaction.debug()}")
        except Exception as e:
            self.logger.error(f"Amygdala error: {e}", exc_info=True)

        # C. 封装并发送事件
        event = Event(
            type=EventType.USER_INPUT,
            content_type=EventContentType.USERMESSAGE,
            content=user_input,
            source=EventSource.L0_SENSOR,
            timestamp=time.time(),  # 事件时间戳，并非用户消息时间戳
            metadata={
                "AmygdalaOutput": amygdala_reaction,
            }
        )
        self.bus.publish(event)
        self.logger.info("Event published.")
                
    
    

      
