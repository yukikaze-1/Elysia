"""
事件总线 - 用于解耦组件间的通信
"""
from typing import Dict, List, Callable, Any
import threading


class EventBus:
    """线程安全的事件总线"""
    
    def __init__(self):
        self.listeners: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
    
    def on(self, event_type: str, callback: Callable):
        """注册事件监听器"""
        with self._lock:
            if event_type not in self.listeners:
                self.listeners[event_type] = []
            self.listeners[event_type].append(callback)
    
    def off(self, event_type: str, callback: Callable):
        """移除事件监听器"""
        with self._lock:
            if event_type in self.listeners:
                try:
                    self.listeners[event_type].remove(callback)
                except ValueError:
                    pass
    
    def emit(self, event_type: str, data: Any = None):
        """发送事件"""
        with self._lock:
            listeners = self.listeners.get(event_type, []).copy()
        
        for callback in listeners:
            try:
                if data is not None:
                    callback(data)
                else:
                    callback()
            except Exception as e:
                print(f"事件回调执行失败 {event_type}: {e}")
    
    def emit_async(self, event_type: str, data: Any = None):
        """异步发送事件（在UI线程中执行）"""
        # 这个方法会在ElysiaClient中被重写以使用UI的after方法
        self.emit(event_type, data)
    
    def clear(self):
        """清空所有监听器"""
        with self._lock:
            self.listeners.clear()
