"""
应用状态管理
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import threading
import time


@dataclass
class AppState:
    """应用状态数据类"""
    # 请求计时相关
    request_start_time: Optional[float] = None
    first_response_received: bool = False
    first_audio_received: bool = False
    request_type: Optional[str] = None
    audio_playback_start_time: Optional[float] = None
    
    # 应用状态
    is_processing: bool = False
    current_message: str = ""
    
    # 统计信息
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    # 运行时数据
    runtime_data: Dict[str, Any] = field(default_factory=dict)


class StateManager:
    """线程安全的状态管理器"""
    
    def __init__(self):
        self.state = AppState()
        self._lock = threading.Lock()
        self._observers = []
    
    def get_state(self) -> AppState:
        """获取当前状态的副本"""
        with self._lock:
            # 返回状态的浅拷贝
            import copy
            return copy.copy(self.state)
    
    def update_state(self, **kwargs):
        """更新状态"""
        with self._lock:
            changed_fields = {}
            for key, value in kwargs.items():
                if hasattr(self.state, key):
                    old_value = getattr(self.state, key)
                    if old_value != value:
                        setattr(self.state, key, value)
                        changed_fields[key] = {'old': old_value, 'new': value}
        
        # 通知观察者
        if changed_fields:
            self._notify_observers(changed_fields)
    
    def start_request_timer(self, request_type: Optional[str] = None, custom_start_time: Optional[float] = None):
        """开始请求计时"""
        with self._lock:
            self.state.request_start_time = custom_start_time or (time.time() * 1000)
            self.state.first_response_received = False
            self.state.first_audio_received = False
            self.state.audio_playback_start_time = None
            self.state.request_type = request_type
            self.state.is_processing = True
            self.state.total_requests += 1
    
    def record_first_response(self) -> float:
        """记录第一个响应时间"""
        with self._lock:
            if not self.state.first_response_received and self.state.request_start_time:
                current_time = time.time() * 1000
                response_time = current_time - self.state.request_start_time
                self.state.first_response_received = True
                return response_time
        return 0
    
    def record_first_audio(self) -> float:
        """记录第一个音频响应时间"""
        with self._lock:
            if not self.state.first_audio_received and self.state.request_start_time:
                current_time = time.time() * 1000
                audio_time = current_time - self.state.request_start_time
                self.state.first_audio_received = True
                return audio_time
        return 0
    
    def record_audio_playback_start(self) -> float:
        """记录音频播放开始时间"""
        with self._lock:
            if self.state.request_start_time:
                self.state.audio_playback_start_time = time.time() * 1000
                return self.state.audio_playback_start_time - self.state.request_start_time
        return 0
    
    def finish_request(self, success: bool = True):
        """完成请求"""
        with self._lock:
            self.state.is_processing = False
            if success:
                self.state.successful_requests += 1
            else:
                self.state.failed_requests += 1
    
    def reset(self):
        """重置状态"""
        with self._lock:
            # 保留统计信息，重置其他状态
            total_requests = self.state.total_requests
            successful_requests = self.state.successful_requests
            failed_requests = self.state.failed_requests
            
            self.state = AppState()
            self.state.total_requests = total_requests
            self.state.successful_requests = successful_requests
            self.state.failed_requests = failed_requests
    
    def add_observer(self, callback):
        """添加状态变化观察者"""
        self._observers.append(callback)
    
    def remove_observer(self, callback):
        """移除状态变化观察者"""
        if callback in self._observers:
            self._observers.remove(callback)
    
    def _notify_observers(self, changed_fields):
        """通知观察者状态变化"""
        for observer in self._observers:
            try:
                observer(changed_fields)
            except Exception as e:
                print(f"状态观察者回调失败: {e}")
    
    def set_runtime_data(self, key: str, value: Any):
        """设置运行时数据"""
        with self._lock:
            self.state.runtime_data[key] = value
    
    def get_runtime_data(self, key: str, default=None):
        """获取运行时数据"""
        with self._lock:
            return self.state.runtime_data.get(key, default)
