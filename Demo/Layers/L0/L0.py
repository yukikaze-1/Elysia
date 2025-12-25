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
import os
import queue
from datetime import datetime

from Demo.Core.OutputChannel import OutputChannel, ConsoleChannel
from Demo.Layers.L0.Sensor import SensoryProcessor, EnvironmentInformation
from Demo.Layers.L0.Amygdala import AmygdalaOutput, Amygdala
from Demo.Core.Schema import Event, EventType, EventContentType, EventSource, ChatMessage, UserMessage
from Demo.Core.EventBus import EventBus, global_event_bus
from Demo.Logger import setup_logger

from dotenv import load_dotenv


class SensorLayer:
    """L0 模块"""
    def __init__(self, event_bus: EventBus = global_event_bus):
        load_dotenv()
        self.logger = setup_logger("L0_SensorLayer")
        self.openai_client: OpenAI = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=os.getenv("DEEPSEEK_API_BASE"))
        
        # 业务组件
        self.sensory_processor: SensoryProcessor = SensoryProcessor(self.logger)    # 感官处理器
        self.amygdala: Amygdala = Amygdala(self.openai_client, self.logger)         # 本能反应器
        self.channels: list[OutputChannel] = [ConsoleChannel()]                     # 输出通道 
        
        # 输入缓冲队列
        self.input_queue: queue.Queue = queue.Queue()
        
        # 对接逻辑
        self.bus: EventBus = event_bus  # 事件总线
        self.running: bool = False
        
        # 线程句柄
        # self._listener_thread: Optional[threading.Thread] = None  # 输入监听线程 // 已弃用
        self._processor_thread: Optional[threading.Thread] = None # 新增处理线程
        self._tick_thread: Optional[threading.Thread] = None    # 心跳线程

        self.logger.info("L0 SensorLayer initialized.")

    # ===============================================================================================
    # === 对外接口方法 ===
    # ===============================================================================================

    def start_threads(self):
        """[接口方法] 启动感知线程"""
        # 防止重复启动
        if self.running:
            return
        
        self.running = True
        
        # 弃用控制台监听，改为外部推送输入
        # # 1. 启动console 监听线程 (Producer) 
        # self._listener_thread = threading.Thread(target=self._console_listener_loop, daemon=True)
        # self._listener_thread.start()
        # self.logger.info("L0 SensorLayer listener thread started.")
        
        # 2. 启动处理线程 (Consumer) 
        self.logger.info("L0 SensorLayer starting processor thread...")
        self._processor_thread = threading.Thread(target=self._input_processing_loop, daemon=True)
        self._processor_thread.start()
        self.logger.info("L0 SensorLayer processor thread started.")
        
        # 3. 启动心跳线程 (Heartbeat Loop)
        self.logger.info("L0 SensorLayer starting tick thread...")
        self._tick_thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._tick_thread.start()
        self.logger.info("L0 SensorLayer tick thread started.")
        
        
    def stop_threads(self):
        """[接口方法] 停止感知"""
        self.running = False
        # 线程会随着 while 循环条件变为 False 而自然结束
        self.logger.info("L0 SensorLayer threads stopping...")
    
    
    def add_channel(self, channel: OutputChannel):
        """[接口方法] 添加输出通道"""
        self.channels.append(channel)
        self.logger.info(f"Output channel {channel.__class__.__name__} added to L0 SensorLayer.")    
        
        
    def output(self, msg: ChatMessage):
        """[接口方法] 遍历所有通道进行广播"""
        for channel in self.channels:
            try:
                channel.send_message(msg)
            except Exception as e:
                print(f"[L0 Error] Channel send failed: {e}")
                
    # TODO 这个data可以封装一下，让fastapi封装好之后转发过来            
    def push_external_input(self, data: dict):
        """
        [生产者] 供外部（如 FastAPI, TelegramBot）投喂数据
        """
        self.input_queue.put(data)
    
    # ===============================================================================================
    # === 内部线程方法 ===
    # ===============================================================================================
    
    # 已弃用
    # def _console_listener_loop(self):
    #     """
    #     [生产者] 纯粹的 IO 监听。
    #     只负责：阻塞等待用户输入 -> 放入队列。
    #     """
    #     self.logger.info(">>> IO Listener started (Console Mode)")
    #     while self.running:
    #         try:
    #             # 这一步是阻塞的，如果是 WebSocket，这里就是 await websocket.recv()
    #             raw_input: str = input("User: ")
                
    #             if not raw_input.strip():
    #                 continue
                    
    #             # 将原始素材放入队列，立即返回监听下一句，不阻塞 IO
    #             self.input_queue.put(raw_input)
                
    #         except EOFError:
    #             self.stop_threads()
    #             break
    #         except Exception as e:
    #             self.logger.error(f"Listener Error: {e}")
                
                
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
                    input_item = self.input_queue.get(timeout=1.0)
                except queue.Empty:
                    continue # 队列为空，继续循环检查 self.running

                # 2. 执行具体的业务逻辑 (封装成单独的方法，代码更清晰)
                self._handle_logic(input_item)
                
                # 3. 标记队列任务完成
                self.input_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Processor Error: {e}", exc_info=True)
                
                
    def _tick_loop(self):
        """
        内部逻辑: 产生时间心跳
        """
        while self.running:
            # 每 10 秒产生一次心跳
            time.sleep(10)
            self.logger.info("L0 SensorLayer tick event generated.")
            # TODO 你也可以在这里让 Amygdala 检查是否有持续的环境威胁
            # ...
            timestamp = time.time()
            event = Event(
                type=EventType.SYSTEM_TICK,
                content_type=EventContentType.TIME,
                content=timestamp,
                source=EventSource.L0_CLOCK,
                timestamp=timestamp
            )
            self.bus.publish(event)
            self.logger.info(f"System tick event published to EventBus at {datetime.fromtimestamp(timestamp).isoformat()}.")      
        
    # ===============================================================================================
    # === 内部业务逻辑方法 ===
    # ===============================================================================================      
                
    def _handle_logic(self, input_item: str | dict):
        """
        处理单条用户输入的业务逻辑
         1. 感官预处理
         2. 杏仁核反应
         3. 封装并发送事件
         现在 input_item 可能是字符串(控制台) 或 字典(WebSocket)
        """
        raw_text: str = ""
        role: str = "妖梦"
        input_time = time.time()
        
        # A. 解析数据
        if isinstance(input_item, str):
            # 来自 Console
            raw_text = input_item
        elif isinstance(input_item, dict) and input_item.get("source") == "websocket":
            # 来自 WebSocket
            raw_text = input_item.get("content", "")
            role = input_item.get("role", "妖梦")  # 支持前端传角色名
            input_time = input_item.get("timestamp", time.time()) # 支持前端传时间戳
        
        if not raw_text:
            return
        
        self.logger.info(f"Processing Text: {raw_text}")

        # B. 感官预处理
        env_info: EnvironmentInformation = self.sensory_processor.active_perception_envs()
        user_input = UserMessage(role=role, 
                                 content=raw_text, 
                                 timestamp=input_time)
        
        # C. 杏仁核反应
        amygdala_reaction = None
        try:
            amygdala_reaction = self.amygdala.react(
                user_message=user_input,
                current_env=env_info
            )
            self.logger.info(f"Amygdala reaction: {amygdala_reaction.debug()}")
        except Exception as e:
            self.logger.error(f"Amygdala error: {e}", exc_info=True)

        # C. 封装并发送事件
        event = Event(
            type=EventType.USER_INPUT,
            content_type=EventContentType.USERMESSAGE,
            content=user_input,
            source=EventSource.L0_SENSOR if isinstance(input_item, str) else EventSource.WEB_CLIENT,
            timestamp=time.time(),
            metadata={
                "AmygdalaOutput": amygdala_reaction,
            }
        )
        self.bus.publish(event)
        self.logger.info("Event published.")
                
    
    

      
