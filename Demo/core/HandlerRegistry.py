"""
注册和管理事件处理器的模块
"""
from typing import Type, Dict
from core.Handlers.BaseHandler import BaseHandler
from core.Schema import EventType

class HandlerRegistry:
    _registry: Dict[EventType, Type[BaseHandler]] = {}

    @classmethod
    def register(cls, event_type: EventType):
        """装饰器：将 Handler 类注册到特定事件"""
        def wrapper(handler_cls):
            cls._registry[event_type] = handler_cls
            return handler_cls
        return wrapper

    @classmethod
    def get_handlers(cls):
        return cls._registry