import logging
from typing import Literal, Dict, Optional
from Core.EventBus import EventBus
from Core.Schema import Event, EventType
from Logger import setup_logger

from Core.Handlers.BaseHandler import BaseHandler
from Core.Handlers.UserInputHandler import UserInputHandler
from Core.Handlers.SystemTickHandler import SystemTickHandler

from Core.AgentContext import AgentContext

class Dispatcher:
    """
    调度器：负责协调 L0, L1, L2, L3 各层的工作流程
    采用策略模式分发事件。
    """
    def __init__(self, context: AgentContext):
        self.logger: logging.Logger = setup_logger("Dispatcher")
        # 保存上下文引用
        self.context = context
        
        # 核心组件引用
        self.bus: EventBus = context.event_bus
        
        self.running = False
        
        # === [策略模式] 事件处理器注册表 ===
        self.handlers: Dict[EventType, BaseHandler] = {}
        self._register_handlers()


    def _register_handlers(self):
        """初始化并注册所有具体的策略 (Handlers)"""
        
        # 1. 注册用户输入策略
        self.handlers[EventType.USER_INPUT] = UserInputHandler(self.context)
        
        # 2. 注册系统心跳策略
        self.handlers[EventType.SYSTEM_TICK] = SystemTickHandler(self.context)
        
        # 未来可以在这里轻松添加新的事件处理策略，例如：
        # self.handlers[EventType.REFLECTION_DONE] = ReflectionHandler(...)


    def start(self):
        """启动调度主循环 (阻塞式)"""
        self.running = True
        self.logger.info("Dispatcher Loop Started.")
        
        while self.running:
            # 1. 从总线获取事件
            event = self.bus.get(block=True, timeout=1.0)
            
            if not event:
                continue

            # 2. [策略模式] 路由分发
            # 直接根据类型查找对应的 Handler
            handler = self.handlers.get(event.type)

            if handler:
                try:
                    handler.handle(event)
                except Exception as e:
                    self.logger.error(f"Error processing event {event.id} with {type(handler).__name__}: {e}", exc_info=True)
            else:
                # 处理未注册 Handler 的事件 (Fallback)
                self._handle_unregistered_event(event)

        self.logger.info("Dispatcher Loop Stopped.")
        
    def _handle_unregistered_event(self, event: Event):
        """处理没有对应 Handler 的事件"""
        # 暂时保留之前的 TODO 逻辑
        if event.type in [EventType.MACRO_REFLECTION_DONE, EventType.MICRO_REFLECTION_DONE, EventType.REFLECTION_DONE]:
             self.logger.info(f"Reflection event received: {event.type} (Handler not implemented yet).")
        else:
            self.logger.warning(f"Unknown or unhandled event type: {event.type}")

    def stop(self):
        self.running = False
        self.logger.info("Dispatcher stopping...")


