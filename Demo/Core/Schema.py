"""
定义数据模式
"""
from attr import dataclass
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

class EventContentType(str, Enum):
    """事件内容类型枚举"""
    USERMESSAGE = "UserMessage"
    TEXT = "Text"
    STRUCTURED_DATA = "StructuredData"
    TIME = "Time"

@dataclass
class Event:
    """系统内传递的标准事件对象"""
    type: EventType
    content_type: EventContentType  # 事件内容类型
    content: Any                  # 事件载荷: 文本字符串, 或结构化数据
    source: EventSource           # 来源: "L0", "L1", "REFLECTOR"
    timestamp: float = time.time()  # 事件发生时间戳
    id: str = str(uuid.uuid4())      # 唯一ID，便于追踪
    metadata: Dict[str, Any] | None = None     # 额外元数据

    def __str__(self):
        return f"[{datetime.fromtimestamp(self.timestamp).strftime('%H:%M:%S')}] {self.type} from {self.source}: {str(self.content)[:50]}..."
    

DEFAULT_ERROR_PUBLIC_REPLY = "抱歉，我刚刚有点走神了。能再说一遍吗？"    
DEFAULT_ERROR_INNER_THOUGHT = "(系统想法: 模型输出格式错误，可能是被截断或触发过滤)" 
DEFAULT_ERROR_MOOD = ""

