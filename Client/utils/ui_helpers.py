"""
UI 工具类 - 减少UI操作的重复代码
"""
from typing import Callable, Any, Optional
from functools import wraps
import time


class UIHelper:
    """UI操作辅助类"""
    
    def __init__(self, ui_instance):
        self.ui = ui_instance
        self._last_status_update = 0
        self._status_debounce_delay = 0.1  # 100ms防抖
    
    def schedule_ui_update(self, func: Callable, *args, delay: int = 0, **kwargs):
        """统一的UI更新调度方法"""
        def update():
            try:
                func(*args, **kwargs)
            except Exception as e:
                print(f"UI更新失败: {e}")
        
        self.ui.root.after(delay, update)
    
    def batch_ui_updates(self, updates: list, delay: int = 0):
        """批量UI更新"""
        def batch_update():
            for update_func, args, kwargs in updates:
                try:
                    update_func(*args, **kwargs)
                except Exception as e:
                    print(f"批量UI更新失败: {e}")
        
        self.ui.root.after(delay, batch_update)
    
    def debounced_status_update(self, status: str):
        """防抖的状态更新"""
        current_time = time.time()
        if current_time - self._last_status_update < self._status_debounce_delay:
            return
        
        self._last_status_update = current_time
        self.schedule_ui_update(self.ui.set_status, status)
    
    def safe_append_chat(self, message: str, sender: str = "系统"):
        """安全的聊天消息添加"""
        self.schedule_ui_update(self.ui.append_to_chat, message, sender)
    
    def safe_enable_buttons(self):
        """安全的按钮启用"""
        self.schedule_ui_update(self.ui.enable_buttons)
    
    def safe_disable_buttons(self):
        """安全的按钮禁用"""
        self.schedule_ui_update(self.ui.disable_buttons)
    
    def show_error_safe(self, title: str, message: str):
        """安全的错误显示"""
        self.schedule_ui_update(self.ui.show_error, title, message)
    
    def show_warning_safe(self, title: str, message: str):
        """安全的警告显示"""
        self.schedule_ui_update(self.ui.show_warning, title, message)


def ui_thread_safe(ui_helper: UIHelper):
    """装饰器：确保方法在UI线程中执行"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            def execute():
                return func(*args, **kwargs)
            ui_helper.schedule_ui_update(execute)
        return wrapper
    return decorator


class CallbackManager:
    """回调管理器 - 统一管理各种回调设置"""
    
    def __init__(self):
        self.callbacks = {}
    
    def register_callback_set(self, name: str, callback_dict: dict):
        """注册一组回调"""
        self.callbacks[name] = callback_dict
    
    def get_callback_set(self, name: str) -> dict:
        """获取回调组"""
        return self.callbacks.get(name, {})
    
    def create_message_callbacks(self, client_instance):
        """创建消息处理回调字典"""
        return {
            "text_update": self._wrap_async_callback(client_instance._on_text_update),
            "text_complete": self._wrap_async_callback(client_instance._on_text_complete),
            "audio_start": self._wrap_async_callback(client_instance._on_audio_start),
            "audio_status": self._wrap_async_callback(client_instance._on_audio_status),
            "audio_chunk": self._wrap_async_callback(client_instance._on_audio_chunk),
            "audio_end": self._wrap_async_callback(client_instance._on_audio_end),
            "token_usage": self._wrap_async_callback(client_instance._on_token_usage),
            "error": self._wrap_async_callback(client_instance._on_error),
            "done": self._wrap_async_callback(client_instance._on_done),
        }
    
    def _wrap_async_callback(self, callback_func):
        """包装异步回调函数"""
        async def wrapped(*args, **kwargs):
            try:
                return await callback_func(*args, **kwargs)
            except Exception as e:
                print(f"回调执行失败: {e}")
        return wrapped


class RequestHelper:
    """请求处理辅助类"""
    
    def __init__(self, client_instance):
        self.client = client_instance
        self.ui_helper = UIHelper(client_instance.ui)
    
    def validate_message(self, message: str) -> bool:
        """验证消息有效性"""
        if not message or not message.strip():
            self.ui_helper.show_warning_safe("警告", "请先输入消息")
            return False
        return True
    
    def prepare_request(self, message: str, request_type: str) -> bool:
        """准备请求的通用逻辑"""
        if not self.validate_message(message):
            return False
        
        # 重置状态
        self.client.streaming_manager.reset_streaming_response()
        self.client.state_manager.start_request_timer(request_type)
        
        # UI更新
        self.ui_helper.debounced_status_update(f"正在发送{request_type}请求...")
        self.ui_helper.safe_disable_buttons()
        
        return True
    
    def finish_request(self, success: bool = True):
        """完成请求的通用逻辑"""
        self.client.state_manager.finish_request(success)
        self.ui_helper.safe_enable_buttons()
        
        if success:
            self.ui_helper.debounced_status_update("就绪")
        else:
            self.ui_helper.debounced_status_update("请求失败")
    
    def execute_request_with_cleanup(self, handler_func, *args, **kwargs):
        """执行请求并确保清理"""
        def task_wrapper():
            try:
                result = handler_func(*args, **kwargs)
                self.finish_request(True)
                return result
            except Exception as e:
                self.client.error_handler.handle_error(e, "请求执行", True)
                self.finish_request(False)
                raise
        
        return task_wrapper
