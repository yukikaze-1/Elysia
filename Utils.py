import os
import torch
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