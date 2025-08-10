"""
性能优化工具类
"""
import time
import threading
from functools import lru_cache, wraps
from typing import Dict, Any, Optional, Callable
import weakref
import gc
from dataclasses import dataclass, field


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    method_calls: Dict[str, int] = field(default_factory=dict)
    method_times: Dict[str, float] = field(default_factory=dict)
    cache_hits: int = 0
    cache_misses: int = 0
    memory_usage: Dict[str, float] = field(default_factory=dict)
    last_gc_time: float = 0


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self._lock = threading.Lock()
        self._start_time = time.time()
    
    def record_method_call(self, method_name: str, execution_time: float):
        """记录方法调用"""
        with self._lock:
            self.metrics.method_calls[method_name] = self.metrics.method_calls.get(method_name, 0) + 1
            self.metrics.method_times[method_name] = self.metrics.method_times.get(method_name, 0) + execution_time
    
    def record_cache_hit(self):
        """记录缓存命中"""
        with self._lock:
            self.metrics.cache_hits += 1
    
    def record_cache_miss(self):
        """记录缓存未命中"""
        with self._lock:
            self.metrics.cache_misses += 1
    
    def get_performance_report(self) -> dict:
        """获取性能报告"""
        with self._lock:
            total_time = time.time() - self._start_time
            return {
                'runtime': total_time,
                'method_calls': dict(self.metrics.method_calls),
                'average_times': {
                    method: total_time / calls 
                    for method, calls in self.metrics.method_calls.items()
                    if calls > 0
                },
                'cache_hit_rate': (
                    self.metrics.cache_hits / (self.metrics.cache_hits + self.metrics.cache_misses)
                    if (self.metrics.cache_hits + self.metrics.cache_misses) > 0 else 0
                ),
                'total_cache_operations': self.metrics.cache_hits + self.metrics.cache_misses
            }


def performance_monitor(monitor: PerformanceMonitor):
    """性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                monitor.record_method_call(func.__name__, execution_time)
        return wrapper
    return decorator


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, monitor: Optional[PerformanceMonitor] = None):
        self.monitor = monitor
        self._caches = {}  # 改为普通字典，避免弱引用问题
    
    def cached_method(self, maxsize: int = 128, ttl: Optional[float] = None):
        """带TTL的缓存装饰器"""
        def decorator(func):
            cache = {}
            cache_times = {}
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 创建缓存键
                key = str(args) + str(sorted(kwargs.items()))
                current_time = time.time()
                
                # 检查TTL
                if ttl and key in cache_times:
                    if current_time - cache_times[key] > ttl:
                        cache.pop(key, None)
                        cache_times.pop(key, None)
                
                # 检查缓存
                if key in cache:
                    if self.monitor:
                        self.monitor.record_cache_hit()
                    return cache[key]
                
                # 缓存未命中
                if self.monitor:
                    self.monitor.record_cache_miss()
                
                result = func(*args, **kwargs)
                
                # 管理缓存大小
                if len(cache) >= maxsize:
                    # 删除最旧的条目
                    oldest_key = min(cache_times.keys(), key=lambda k: cache_times[k])
                    cache.pop(oldest_key, None)
                    cache_times.pop(oldest_key, None)
                
                cache[key] = result
                cache_times[key] = current_time
                return result
            
            # 注册缓存以便管理
            self._caches[func.__name__] = cache
            return wrapper
        return decorator
    
    def clear_all_caches(self):
        """清空所有缓存"""
        for cache in self._caches.values():
            cache.clear()
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计"""
        return {name: len(cache) for name, cache in self._caches.items()}


class MemoryManager:
    """内存管理器"""
    
    def __init__(self, monitor: Optional[PerformanceMonitor] = None):
        self.monitor = monitor
        self._temp_objects = []  # 改为普通列表，避免弱引用问题
        self._last_gc = time.time()
        self._gc_threshold = 60  # 60秒进行一次GC
    
    def register_temp_object(self, obj):
        """注册临时对象"""
        self._temp_objects.append(obj)
    
    def force_gc(self):
        """强制垃圾回收"""
        gc.collect()
        current_time = time.time()
        self._last_gc = current_time
        
        if self.monitor:
            self.monitor.metrics.last_gc_time = current_time
    
    def auto_gc_check(self):
        """自动GC检查"""
        current_time = time.time()
        if current_time - self._last_gc > self._gc_threshold:
            self.force_gc()
    
    def get_memory_info(self) -> dict:
        """获取内存信息"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss': memory_info.rss / 1024 / 1024,  # MB
                'vms': memory_info.vms / 1024 / 1024,  # MB
                'temp_objects': len(self._temp_objects),
                'last_gc': self._last_gc
            }
        except (ImportError, Exception):
            # 回退方案：基本内存信息
            return {
                'rss': 0,  # 无法获取
                'vms': 0,  # 无法获取
                'temp_objects': len(self._temp_objects),
                'last_gc': self._last_gc,
                'note': 'Memory details unavailable (psutil not installed)'
            }


class AsyncOptimizer:
    """异步操作优化器"""
    
    def __init__(self):
        self._pending_operations = {}
        self._operation_lock = threading.Lock()
    
    def debounce(self, key: str, delay: float = 0.5):
        """防抖装饰器"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                with self._operation_lock:
                    # 取消之前的操作
                    if key in self._pending_operations:
                        timer = self._pending_operations[key]
                        timer.cancel()
                    
                    # 创建新的延迟操作
                    def delayed_execution():
                        with self._operation_lock:
                            self._pending_operations.pop(key, None)
                        func(*args, **kwargs)
                    
                    timer = threading.Timer(delay, delayed_execution)
                    self._pending_operations[key] = timer
                    timer.start()
            
            return wrapper
        return decorator
    
    def throttle(self, key: str, min_interval: float = 1.0):
        """节流装饰器"""
        last_call_times = {}
        
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                current_time = time.time()
                last_call = last_call_times.get(key, 0)
                
                if current_time - last_call >= min_interval:
                    last_call_times[key] = current_time
                    return func(*args, **kwargs)
                else:
                    print(f"节流: 跳过 {func.__name__} 调用")
            
            return wrapper
        return decorator


class PerformanceOptimizer:
    """性能优化器主类"""
    
    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.cache_manager = CacheManager(self.monitor)
        self.memory_manager = MemoryManager(self.monitor)
        self.async_optimizer = AsyncOptimizer()
    
    def get_comprehensive_report(self) -> dict:
        """获取综合性能报告"""
        return {
            'performance': self.monitor.get_performance_report(),
            'cache': self.cache_manager.get_cache_stats(),
            'memory': self.memory_manager.get_memory_info(),
            'timestamp': time.time()
        }
    
    def cleanup(self):
        """清理资源"""
        self.cache_manager.clear_all_caches()
        self.memory_manager.force_gc()
    
    def optimize_method(self, cache_size: int = 32, cache_ttl: float = 300):
        """方法优化装饰器组合"""
        def decorator(func):
            # 组合多个优化装饰器
            optimized_func = performance_monitor(self.monitor)(func)
            optimized_func = self.cache_manager.cached_method(cache_size, cache_ttl)(optimized_func)
            return optimized_func
        return decorator
