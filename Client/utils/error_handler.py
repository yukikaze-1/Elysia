"""
错误处理工具
"""
import functools
import traceback
from typing import Callable, Any, Optional
from .event_bus import EventBus


def handle_errors(
    show_in_ui: bool = True, 
    event_bus: Optional[EventBus] = None,
    fallback_value: Any = None,
    reraise: bool = False
):
    """
    统一错误处理装饰器
    
    Args:
        show_in_ui: 是否在UI中显示错误
        event_bus: 事件总线实例
        fallback_value: 异常时返回的默认值
        reraise: 是否重新抛出异常
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = f"{func.__name__} 失败: {str(e)}"
                
                # 打印详细错误信息
                print(f"❌ {error_msg}")
                print(f"详细错误: {traceback.format_exc()}")
                
                # 通过事件总线发送错误信息
                if show_in_ui and event_bus:
                    event_bus.emit_async('error', {
                        'title': '操作失败',
                        'message': error_msg,
                        'exception': e
                    })
                
                if reraise:
                    raise
                
                return fallback_value
        
        return wrapper
    return decorator


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus
        self.error_count = 0
        self.last_errors = []
        self.max_history = 10
    
    def handle_error(
        self, 
        error: Exception, 
        context: str = "", 
        show_in_ui: bool = True,
        user_message: Optional[str] = None
    ):
        """统一错误处理"""
        self.error_count += 1
        
        # 构造错误信息
        error_info = {
            'error': error,
            'context': context,
            'timestamp': __import__('time').time(),
            'traceback': traceback.format_exc()
        }
        
        # 保存到历史记录
        self.last_errors.append(error_info)
        if len(self.last_errors) > self.max_history:
            self.last_errors.pop(0)
        
        # 打印错误
        print(f"❌ 错误 #{self.error_count}: {context} - {str(error)}")
        print(f"详细信息: {traceback.format_exc()}")
        
        # 发送UI事件
        if show_in_ui and self.event_bus:
            display_message = user_message or f"{context}: {str(error)}"
            self.event_bus.emit_async('error', {
                'title': '操作失败',
                'message': display_message,
                'exception': error
            })
    
    def get_error_stats(self) -> dict:
        """获取错误统计"""
        return {
            'total_errors': self.error_count,
            'recent_errors': len(self.last_errors),
            'last_error_time': self.last_errors[-1]['timestamp'] if self.last_errors else None
        }
    
    def clear_history(self):
        """清空错误历史"""
        self.last_errors.clear()
        self.error_count = 0


# 创建全局错误处理器实例
_global_error_handler = None

def get_global_error_handler() -> ErrorHandler:
    """获取全局错误处理器"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler

def set_global_error_handler(handler: ErrorHandler):
    """设置全局错误处理器"""
    global _global_error_handler
    _global_error_handler = handler
