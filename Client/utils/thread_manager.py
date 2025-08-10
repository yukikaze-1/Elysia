"""
线程管理器 - 统一管理后台任务
"""
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Any, Optional, Dict
import time


class ThreadManager:
    """线程管理器"""
    
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.thread_pool = ThreadPoolExecutor(
            max_workers=max_workers, 
            thread_name_prefix="Elysia"
        )
        self.shutdown_event = threading.Event()
        self.active_tasks: Dict[str, Future] = {}
        self._task_counter = 0
        self._lock = threading.Lock()
    
    def submit_task(self, func: Callable, *args, task_name: Optional[str] = None, **kwargs) -> str:
        """提交任务到线程池"""
        with self._lock:
            self._task_counter += 1
            if task_name is None:
                task_name = f"task_{self._task_counter}"
        
        if self.shutdown_event.is_set():
            raise RuntimeError("线程管理器已关闭")
        
        future = self.thread_pool.submit(func, *args, **kwargs)
        
        with self._lock:
            self.active_tasks[task_name] = future
        
        # 添加完成回调来清理任务
        future.add_done_callback(lambda f: self._cleanup_task(task_name))
        
        return task_name
    
    def submit_async_task(self, coro_func: Callable, *args, task_name: Optional[str] = None, **kwargs) -> str:
        """提交异步任务"""
        import asyncio
        
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro_func(*args, **kwargs))
            finally:
                loop.close()
        
        return self.submit_task(run_async, task_name=task_name)
    
    def cancel_task(self, task_name: str) -> bool:
        """取消指定任务"""
        with self._lock:
            if task_name in self.active_tasks:
                future = self.active_tasks[task_name]
                cancelled = future.cancel()
                if cancelled:
                    del self.active_tasks[task_name]
                return cancelled
        return False
    
    def wait_for_task(self, task_name: str, timeout: Optional[float] = None) -> Any:
        """等待任务完成"""
        with self._lock:
            future = self.active_tasks.get(task_name)
        
        if future:
            try:
                return future.result(timeout=timeout)
            except Exception as e:
                print(f"任务 {task_name} 执行失败: {e}")
                raise
        else:
            raise ValueError(f"任务 {task_name} 不存在")
    
    def get_active_tasks(self) -> Dict[str, bool]:
        """获取活跃任务状态"""
        with self._lock:
            return {name: not future.done() for name, future in self.active_tasks.items()}
    
    def _cleanup_task(self, task_name: str):
        """清理完成的任务"""
        with self._lock:
            self.active_tasks.pop(task_name, None)
    
    def shutdown(self, wait: bool = True, timeout: Optional[float] = None):
        """关闭线程管理器"""
        self.shutdown_event.set()
        
        if wait:
            # 取消所有活跃任务
            with self._lock:
                for future in self.active_tasks.values():
                    future.cancel()
        
        self.thread_pool.shutdown(wait=wait)
    
    def is_shutdown(self) -> bool:
        """检查是否已关闭"""
        return self.shutdown_event.is_set()


class TaskResult:
    """任务结果封装"""
    
    def __init__(self, success: bool, result: Any = None, error: Optional[Exception] = None):
        self.success = success
        self.result = result
        self.error = error
        self.timestamp = time.time()
    
    def __str__(self):
        if self.success:
            return f"TaskResult(success=True, result={self.result})"
        else:
            return f"TaskResult(success=False, error={self.error})"
