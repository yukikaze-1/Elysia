import os
import torch
import threading
from typing import Optional
import asyncio
import aiofiles
from langchain_huggingface import HuggingFaceEmbeddings

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
        
import time        
class TimeTracker:
    """时间追踪器，用于详细记录各个阶段的耗时"""
    
    def __init__(self):
        self.timestamps = {}
        self.durations = {}
    
    def start(self, phase_name: str):
        """开始记录某个阶段的时间"""
        self.timestamps[f"{phase_name}_start"] = time.time()
    
    def end(self, phase_name: str):
        """结束记录某个阶段的时间"""
        end_time = time.time()
        self.timestamps[f"{phase_name}_end"] = end_time
        start_time = self.timestamps.get(f"{phase_name}_start")
        if start_time:
            self.durations[phase_name] = end_time - start_time
    
    def get_duration(self, phase_name: str) -> float:
        """获取某个阶段的耗时（秒）"""
        return self.durations.get(phase_name, 0.0)
    
    def print_summary(self, total_files: int = 1, total_size: int = 0):
        """打印时间统计摘要"""
        print("\n   ⏱️  详细时间统计:")
        print("   " + "-" * 40)
        
        for phase, duration in self.durations.items():
            print(f"   {phase:20s}: {duration:8.3f}秒")
        
        total_duration = self.durations.get('total_request', 0.0)
        if total_duration > 0:
            print("   " + "-" * 40)
            print(f"   {'总耗时':20s}: {total_duration:8.3f}秒")
            
            if total_files > 0:
                avg_per_file = total_duration / total_files
                print(f"   {'平均每文件':20s}: {avg_per_file:8.3f}秒")
            
            if total_size > 0:
                mb_size = total_size / (1024 * 1024)
                speed = mb_size / total_duration if total_duration > 0 else 0
                print(f"   {'处理速度':20s}: {speed:8.3f}MB/s")