"""
L0 模块：
    1. 感知环境 ---> 输出环境信息
    2. 生成本能反应 ---> 输出本能反应
    
    运行在独立线程中，持续监听用户和环境变化，产生事件推送给 L1 模块。
"""

import logging
from openai import OpenAI
from typing import Optional
import threading
import time
import sys
import os
from datetime import datetime

from Demo.Layers.L0.Sensor import SensoryProcessor, EnvironmentInformation
from Demo.Layers.L0.Amygdala import AmygdalaOutput, Amygdala
from Demo.Layers.Session import UserMessage
from Demo.Core.Schema import Event, EventType, EventContentType, EventSource
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
        self.sensory_processor = SensoryProcessor(self.logger)
        self.amygdala = Amygdala(self.openai_client, self.logger)
        
        # 对接逻辑
        self.bus: EventBus = event_bus
        self.running: bool = False
        self._input_thread: Optional[threading.Thread] = None
        self._tick_thread: Optional[threading.Thread] = None

        self.logger.info("L0 SensorLayer initialized.")


    def start_threads(self):
        """[接口方法] 启动感知线程"""
        # 防止重复启动
        if self.running:
            return
        
        self.running = True
        
        # 1. 启动输入监听线程 (Input Loop)
        self.logger.info("L0 SensorLayer starting input thread...")
        self._input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self._input_thread.start()
        self.logger.info("L0 SensorLayer input thread started.")
        
        # 2. 启动心跳线程 (Heartbeat Loop)
        self.logger.info("L0 SensorLayer starting tick thread...")
        self._tick_thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._tick_thread.start()
        self.logger.info("L0 SensorLayer tick thread started.")
        
        
    def stop_threads(self):
        """[接口方法] 停止感知"""
        self.running = False
        # 线程会随着 while 循环条件变为 False 而自然结束
        self.logger.info("L0 SensorLayer threads stopping...")
        
        
    def output(self, public_reply:str, inner_thought: str):
        """
        [接口实现] 简单的控制台打印
        """
        # 同时记录日志
        logger = logging.getLogger("Main")
        
        # 使用颜色区分 AI 和用户的发言 (例如：绿色)
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        RESET = "\033[0m"
        
        # 打印 formatted output
        print(f"\n{GREEN}[Elysia]: {public_reply}{RESET}")
        logger.info(f"Elysia Public Reply: {public_reply}")
        print(f"{YELLOW}(Inner Thought): {inner_thought}{RESET}\n")
        logger.info(f"Elysia Inner Thought: {inner_thought}")
        
        # 强制刷新缓冲区，确保字立刻显示出来
        sys.stdout.flush()
    
    
    def _input_loop(self):
        """
        内部逻辑: 持续监听用户输入 -> 调用业务组件处理 -> 发送事件
        """
        print(">>> L0 Sensor is listening...")
        while self.running:
            try:
                # 1. 获取原始输入 (阻塞式)
                # 实际项目中这里可能是 WebSocket.recv() 或 API 轮询
                # TODO 用户如何输入？
                self.logger.info("Waiting for user input...")
                raw_input = input("User: ")
                if not raw_input.strip():
                    continue
                
                self.logger.info(f"User input received: {raw_input}")
                raw_input = UserMessage(role="妖梦", content=raw_input)

                # 2. [业务集成] 感官预处理 (SensoryProcessor)
                # 主动感知环境信息
                env_info: EnvironmentInformation = self.sensory_processor.active_perception_envs()
                self.logger.info(f"Environment information perceived: {env_info}")
                
                # 3. [业务集成] 杏仁核反应 (Amygdala)
                try:
                    amygdala_reaction: AmygdalaOutput = self.amygdala.react(
                        user_message=raw_input,
                        current_env=env_info
                    )
                    self.logger.info(f"Amygdala reaction: {amygdala_reaction}")
                except Exception as e:
                    self.logger.warning(f"Amygdala error: {e}", exc_info=True)

                # 4. 封装并发送事件
                # TODO 这里封装的有问题,conten和metadata具体怎么分配
                event = Event(
                    type=EventType.USER_INPUT,
                    content_type=EventContentType.USERMESSAGE,
                    content=raw_input,
                    source=EventSource.L0_SENSOR,
                    metadata={
                        "AmygdalaOutput": amygdala_reaction
                    }
                )
                self.bus.publish(event)
                self.logger.info("User input event published to EventBus.")

            except EOFError:
                # 处理 Ctrl+D
                self.stop_threads()
                break
            except Exception as e:
                self.logger.error(f"L0 Error: Input loop failed: {e}", exc_info=True)

    
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

      
