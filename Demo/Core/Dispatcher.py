import logging
import importlib  # 新增
import pkgutil    # 新增
from typing import Dict
from Core.EventBus import EventBus
from Core.Schema import Event, EventType
from Logger import setup_logger

from Core.Handlers.BaseHandler import BaseHandler
from Core.AgentContext import AgentContext
from Core.HandlerRegistry import HandlerRegistry
import Core.Handlers # 新增：导入包以便扫描

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
        
        # === 新增：动态加载所有 Handler 模块 ===
        # 必须先导入模块，装饰器 @HandlerRegistry.register 才会执行
        self.logger.info("Loading handler modules from Core.Handlers...")
        package = Core.Handlers
        prefix = package.__name__ + "."
        
        # 遍历 Core.Handlers 目录下的所有文件并导入
        if hasattr(package, "__path__"):
            for _, name, _ in pkgutil.iter_modules(package.__path__, prefix):
                try:
                    importlib.import_module(name)
                    self.logger.info(f"Auto-loaded handler module: {name}")
                except Exception as e:
                    self.logger.error(f"Failed to load handler module {name}: {e}", exc_info=True)
        # =========================================

        # 自动发现并实例化所有注册的 Handler
        self.logger.info("Registering event handlers...")
        for event_type, handler_cls in HandlerRegistry.get_handlers().items():
            self.handlers[event_type] = handler_cls(self.context)
            self.logger.info(f"Registered handler {handler_cls.__name__} for {event_type}")
        self.logger.info("All event handlers registered.")


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


