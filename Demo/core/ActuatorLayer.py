
from typing import List, Any
import logging
from enum import Enum

from core.OutputChannel import OutputChannel
from core.EventBus import EventBus
from core.Schema import ChatMessage
from Logger import setup_logger
from config.Config import ActuatorConfig

class ActionType(str, Enum):
    SPEECH = "SPEECH"
    COMMAND = "COMMAND"
    

class ActuatorLayer:
    """
    执行层/表达层：负责将 AI 的决策转化为外部世界的行动 (说话、动作、指令)
    """
    def __init__(self, event_bus: EventBus, config: ActuatorConfig):
        self.config: ActuatorConfig = config
        self.logger: logging.Logger = setup_logger(self.config.logger_name)
        self.bus: EventBus = event_bus
        self.channels: List[OutputChannel] = []
        
        # 动作策略映射表
        self._action_handlers = {
            ActionType.SPEECH: self._speak,
            ActionType.COMMAND: self._execute_command
        }
        
        self.logger.info(">>> ActuatorLayer Initialized.")
    
    # ==========================================================================================================================
    # 外部接口
    # ==========================================================================================================================    
    def get_status(self) -> dict:
        """获取 ActuatorLayer 状态"""
        status = {
            "registered_channels": [channel.__class__.__name__ for channel in self.channels]
        }
        return status


    def add_channel(self, channel: OutputChannel):
        """注册输出通道 (如 WebSocketManager, Speaker, Terminal)"""
        self.channels.append(channel)
        self.logger.info(f"Output channel {channel.__class__.__name__} added to ActuatorLayer.")


    def perform_action(self, action_type: ActionType, content: Any):
        """
        执行动作的总入口
        Dispatcher调用 
        采用查表法(策略模式)分发动作
        """
        # 查表分发
        handler = self._action_handlers.get(action_type)
        
        # 执行对应的处理函数
        if handler:
            try:
                handler(content)
            except Exception as e:
                self.logger.error(f"Error executing action {action_type}: {e}", exc_info=True)
        else:
            self.logger.warning(f"Unknown action type: {action_type}")

    # ==========================================================================================================================
    # 内部方法实现
    # ==========================================================================================================================
    
    def _speak(self, message: ChatMessage):
        """处理说话 (TTS + 广播)"""
        self.logger.info(f"ActuatorLayer speaking: {message.content}")
        # 1. 这里可以加 TTS 转换逻辑 -> 生成 audio_data
        
        # 2. 广播给所有通道
        for channel in self.channels:
            try:
                # 可以封装成更复杂的 OutputPayload (含音频, 文本, 表情)
                channel.send_message(message) 
            except Exception as e:
                print(f"[Actuator Error] {e}")


    def _execute_command(self, cmd: dict):
        # 处理非语言的动作，比如前端换装、动作
        pass