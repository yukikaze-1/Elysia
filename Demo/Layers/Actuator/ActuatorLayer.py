
from typing import List, Any
from enum import Enum

from Demo.Core.OutputChannel import OutputChannel
from Demo.Core.EventBus import EventBus, global_event_bus
from Demo.Core.Schema import ChatMessage
from Demo.Logger import setup_logger

class ActionType(str, Enum):
    SPEECH = "SPEECH"
    COMMAND = "COMMAND"
    

class ActuatorLayer:
    """
    执行层/表达层：负责将 AI 的决策转化为外部世界的行动 (说话、动作、指令)
    """
    def __init__(self, event_bus: EventBus = global_event_bus):
        self.logger = setup_logger("ActuatorLayer")
        self.bus: EventBus = event_bus
        self.channels: List[OutputChannel] = []
        self.logger.info(">>> ActuatorLayer Initialized.")


    def add_channel(self, channel: OutputChannel):
        """注册输出通道 (如 WebSocketManager, Speaker, Terminal)"""
        self.channels.append(channel)
        self.logger.info(f"Output channel {channel.__class__.__name__} added to ActuatorLayer.")

    def perform_action(self, action_type: ActionType, content: Any):
        """
        执行动作的总入口
        Dispatcher 不再调用 l0.output，而是调用 actuator.perform_action
        """
        if action_type == ActionType.SPEECH:
            self._speak(content)
        elif action_type == ActionType.COMMAND:
            self._execute_command(content)
        else:
            self.logger.warning(f"Unknown action type: {action_type}")


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