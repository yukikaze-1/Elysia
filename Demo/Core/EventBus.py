"""
事件总线模块
"""

import queue
import logging
from typing import Callable, List, Dict
from Core.Schema import Event
from Logger import setup_logger

class EventBus:
    def __init__(self):
        self.logger: logging.Logger = setup_logger("EventBus")
        # 核心队列：使用 Python 内置的 PriorityQueue 或 Queue
        # Queue 是线程安全的，完美适配多线程环境 (L0 input thread vs Main loop)
        self._queue = queue.Queue()
        
        # 订阅者字典：用于无需主循环干预的即时回调 (Observer Pattern)
        # 格式: { "EVENT_TYPE": [callback_function1, callback_function2] }
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self.logger.info("EventBus initialized.")


    def subscribe(self, event_type: str, callback: Callable[[Event], None]):
        """
        允许组件订阅特定类型的事件（通常用于Logger、Monitor等副作用组件）
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        self.logger.info(f"New subscriber added for event: {event_type}")


    def publish(self, event: Event):
        """
        发布事件：
        1. 放入队列供主循环(Main Loop)处理
        2. 触发所有即时订阅者
        """
        # TODO 此处可能有耗时操作，待修改
        # 1. 触发直接订阅者 (同步执行，注意不要在这里做耗时操作)
        if event.type in self._subscribers:
            self.logger.debug(f"Triggering {len(self._subscribers[event.type])} subscribers for event: {event.type}")
            for callback in self._subscribers[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.error(f"Error in subscriber callback: {e}")

        # 2. 放入队列 (供异步调度器处理)
        self._queue.put(event)
        self.logger.debug(f"Event pushed to bus: {event}")


    def get(self, block: bool = True, timeout: float = 5.0) -> Event | None:
        """
        从总线获取下一个事件。
        Dispatcher (调度器) 会调用此方法。
        
        Args:
            block: 是否阻塞等待
            timeout: 等待超时时间
        """
        try:
            res = self._queue.get(block=block, timeout=timeout)
            self.logger.debug(f"Event retrieved from bus: {res}")
            return res
        except queue.Empty:
            self.logger.debug("EventBus get() timed out - no event available.")
            return None

    def empty(self) -> bool:
        """检查总线是否为空"""
        return self._queue.empty()

    def qsize(self) -> int:
        """当前积压的事件数量"""
        return self._queue.qsize()
    

# 单例模式 (可选，如果在整个应用中只用一个总线)
global_event_bus = EventBus()

    
    