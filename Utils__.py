import os
import time        
import torch
from typing import Optional, Dict, Tuple, List
import asyncio
import aiofiles
from langchain_huggingface import HuggingFaceEmbeddings
from contextlib import contextmanager

def create_embedding_model(model: str = "BAAI/bge-large-en-v1.5") -> HuggingFaceEmbeddings:
    """
    创建 HuggingFace 嵌入模型
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # 将模型名称转换为本地路径格式
    local_model_name = model
    local_model_path = f"/home/yomu/Elysia/model_cache/{local_model_name}"
    
    # 检查本地模型是否存在
    if os.path.exists(local_model_path):
        print(f"Using local model: {local_model_path}")
        return HuggingFaceEmbeddings(
            model_name=local_model_path,  # 使用本地路径
            model_kwargs={'device': device, 'trust_remote_code': True},
            encode_kwargs={'normalize_embeddings': True}
        )
    else:
        print(f"Local model not found at {local_model_path}, downloading...")
        return HuggingFaceEmbeddings(
            model_name=model,
            model_kwargs={'device': device, 'trust_remote_code': True},
            encode_kwargs={'normalize_embeddings': True},
            cache_folder="/home/yomu/Elysia/model_cache"
        )
        

class MessageIDGenerator:
    """
    异步消息ID生成器
    使用文件存储当前ID，支持并发访问
    """
    def __init__(self, storage_file: str = "/home/yomu/Elysia/message_id_counter.txt"):
        self.storage_file = storage_file
        self._current_id: Optional[int] = None
        self._lock = asyncio.Lock()
    
    async def _load_current_id(self) -> int:
        """从文件加载当前ID"""
        try:
            if os.path.exists(self.storage_file):
                async with aiofiles.open(self.storage_file, 'r') as f:
                    content = await f.read()
                    return int(content.strip())
            else:
                # 文件不存在，从1开始
                return 0
        except (ValueError, IOError):
            # 文件损坏或读取失败，从1开始
            return 0
    
    async def _save_current_id(self, message_id: int):
        """保存当前ID到文件"""
        try:
            async with aiofiles.open(self.storage_file, 'w') as f:
                await f.write(str(message_id))
        except IOError as e:
            print(f"Warning: Failed to save message ID to file: {e}")
    
    async def get_next_id(self) -> int:
        """获取下一个消息ID"""
        async with self._lock:
            if self._current_id is None:
                self._current_id = await self._load_current_id()
            
            self._current_id += 1
            await self._save_current_id(self._current_id)
            return self._current_id
    
    async def get_current_id(self) -> int:
        """获取当前ID（不递增）"""
        async with self._lock:
            if self._current_id is None:
                self._current_id = await self._load_current_id()
            return self._current_id


class SyncMessageIDGenerator:
    """
    同步消息ID生成器
    使用文件存储当前ID，支持并发访问
    """
    def __init__(self, storage_file: str = "/home/yomu/Elysia/message_id_counter.txt"):
        self.storage_file = storage_file
        self._current_id: Optional[int] = None
        import threading
        self._lock = threading.Lock()
    
    def _load_current_id(self) -> int:
        """从文件加载当前ID"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    content = f.read().strip()
                    return int(content)
            else:
                # 文件不存在，从0开始
                return 0
        except (ValueError, IOError):
            # 文件损坏或读取失败，从0开始
            return 0
    
    def _save_current_id(self, message_id: int):
        """保存当前ID到文件"""
        try:
            with open(self.storage_file, 'w') as f:
                f.write(str(message_id))
        except IOError as e:
            print(f"Warning: Failed to save message ID to file: {e}")
    
    def get_next_id(self) -> int:
        """获取下一个消息ID"""
        with self._lock:
            if self._current_id is None:
                self._current_id = self._load_current_id()
            
            self._current_id += 1
            self._save_current_id(self._current_id)
            return self._current_id
    
    def get_current_id(self) -> int:
        """获取当前ID（不递增）"""
        with self._lock:
            if self._current_id is None:
                self._current_id = self._load_current_id()
            return self._current_id
        
        
class TimeTracker:
    """时间追踪器 - 用于监控各个阶段的耗时"""
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.stage_times: Dict[str, float] = {}
        self.stage_start: Optional[float] = None
        
    def start_request(self):
        """开始一个请求的计时"""
        self.start_time = time.time()
        self.stage_times.clear()
        
    def start_stage(self, stage_name: str):
        """开始一个阶段的计时"""
        self.stage_start = time.time()
        
    def end_stage(self, stage_name: str):
        """结束一个阶段的计时"""
        if self.stage_start is not None:
            duration = time.time() - self.stage_start
            self.stage_times[stage_name] = duration
            self.stage_start = None
            return duration
        return 0
    
    @contextmanager
    def time_stage(self, stage_name: str):
        """上下文管理器方式计时"""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.stage_times[stage_name] = duration
    
    def get_total_time(self) -> float:
        """获取总耗时"""
        if self.start_time is None:
            return 0
        return time.time() - self.start_time
    
    def get_timing_summary(self) -> Dict[str, float]:
        """获取计时摘要"""
        summary = self.stage_times.copy()
        summary['total_time'] = self.get_total_time()
        return summary