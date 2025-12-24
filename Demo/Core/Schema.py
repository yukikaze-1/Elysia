"""
定义数据模式
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime
import time
import uuid


class EventType(str, Enum):
    """事件类型枚举"""
    USER_INPUT = "user_input"
    SYSTEM_TICK = "system_tick"
    MICRO_REFLECTION_DONE = "micro_reflection_done"
    MACRO_REFLECTION_DONE = "macro_reflection_done"
    REFLECTION_DONE = "reflection_done"


class EventSource(str, Enum):
    """事件来源枚举"""
    L0 = "L0"
    L0_SENSOR = "L0_SENSOR"
    L0_CLOCK = "L0_CLOCK"
    L1 = "L1"
    REFLECTOR = "REFLECTOR"
    SYSTEM = "SYSTEM"    
    WEB_CLIENT = "WEB_CLIENT"       # 来自 Web 前端客户端
    ACTIVE_SENSOR = "ACTIVE_SENSOR" # 来自主动传感器模块(L0主动感知)

class EventContentType(str, Enum):
    """事件内容类型枚举"""
    USERMESSAGE = "UserMessage"
    TEXT = "Text"
    STRUCTURED_DATA = "StructuredData"
    TIME = "Time"

@dataclass
class Event:
    """系统内传递的标准事件对象"""
    type: EventType         # 事件类型
    content_type: EventContentType  # 事件载荷类型
    content: Any                  # 事件载荷
    source: EventSource           # 来源
    timestamp: float = field(default_factory=time.time) # 事件发生时间戳
    id: str = field(default_factory=lambda: str(uuid.uuid4()))      # 唯一ID，便于追踪
    metadata: Dict[str, Any] | None = None     # 额外元数据

    def __str__(self):
        return f"[{datetime.fromtimestamp(self.timestamp).strftime('%H:%M:%S')}] {self.type} from {self.source}: {str(self.content)[:50]}..."
    

DEFAULT_ERROR_PUBLIC_REPLY = "抱歉，我刚刚有点走神了。能再说一遍吗？"    
DEFAULT_ERROR_INNER_THOUGHT = "(系统想法: 模型输出格式错误，可能是被截断或触发过滤)" 
DEFAULT_ERROR_MOOD = ""



class InputEventInfo:
    """输入事件类"""
    def __init__(self):
        self.input_type = "keyboard"  # 假设是键盘输入
        self.typing_duration_ms = 0  # 假设没有打字时间
        self.delete_count = 0  # 假设没有删除操作

    def to_dict(self) -> dict:
        """将输入事件转换为字典格式"""
        return {
                "input_type": self.input_type,
                "typing_duration_ms": self.typing_duration_ms,
                "delete_count": self.delete_count
        }
        
    def __str__(self):
        return f"InputEventInfo(type={self.input_type}, duration={self.typing_duration_ms}ms, deletes={self.delete_count})"

class UserMessage:
    """用户消息类"""
    def __init__(self, role: str, content: str, timestamp: float | None = None):
        self.role: str= role
        self.content: str = content
        self.client_timestamp: float = timestamp if timestamp else time.time()
        self.input_event = InputEventInfo()

    def to_dict(self) -> dict:
        """将用户消息转换为字典格式"""
        return {
            "role": "user",
            "content": self.content,
            "client_timestamp": self.client_timestamp,
            "input_event": self.input_event.to_dict()
        }
        
    def to_str(self) -> str:
        return f"UserMessage(role={self.role}, content={self.content}, timestamp={self.client_timestamp}, input_event={self.input_event})"


from openai.types.chat import ChatCompletionMessage
import time
import logging

class ChatMessage:
    """聊天消息类，包含角色、内容、内心独白、时间戳等信息"""
    def __init__(self, role: str, content , inner_voice: str , timestamp: float | None = None):
        self.role: str = role
        self.content = content
        self.inner_voice: str = inner_voice
        self.timestamp: float = timestamp if timestamp else time.time()
    
    @classmethod
    def from_ChatCompletionMessage(cls, message: ChatCompletionMessage, timestamp: int):
        return cls(role=message.role, 
                   content=message.content, 
                   inner_voice="",
                   timestamp=float(timestamp))
    
    @classmethod
    def from_UserMessage(cls, user_message: UserMessage):
        return cls(role=user_message.role,
                   content=user_message.content,
                   inner_voice="",
                   timestamp=user_message.client_timestamp)
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "inner_voice":self.inner_voice,
            "timestamp": self.timestamp
        }
    
    @classmethod    
    def from_dict(cls, data: dict):
        """ 从字典加载数据 """
        return cls(
            role=data.get("role", ""),
            content=data.get("content", ""),
            inner_voice=data.get("inner_voice", ""),
            timestamp=data.get("timestamp", time.time())
        )
        
        
    def debug(self, logger: logging.Logger):
        logger.info(self.to_dict())


class ConversationSegment:
    """对话片段类，表示一段时间内的对话消息集合"""
    def __init__(self, start_time: float, end_time: float, messages: list[ChatMessage]):
        self.messages: list[ChatMessage] = messages
        self.start_time: float = start_time
        self.end_time: float = end_time
        
    def format_messages_to_line(self):
        """ 格式化消息为行文本 """
        lines = []
        for msg in self.messages:
            lines.append(f'  {msg.role}: {msg.content}: {msg.timestamp}： {datetime.fromtimestamp(msg.timestamp)}')
        return "[\n" + "\n".join(lines) + "\n]"
    
    def debug(self, logger: logging.Logger):
        logger.info("Conversaton Segement:")
        logger.info(f"During:{self.start_time} to {self.end_time}.Contains {len(self.messages)} messages")
        logger.info("Conversaton Segement:" + self.format_messages_to_line())
        
