import os
import torch
from langchain_huggingface import HuggingFaceEmbeddings


def create_embedding_model(debug_info: str, model: str = "BAAI/bge-large-en-v1.5") -> HuggingFaceEmbeddings:
    """
    创建 HuggingFace 嵌入模型
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[DEBUG] Using device: {device} | Info: {debug_info}")
    
    # 将模型名称转换为本地路径格式
    local_model_name = model
    local_model_path = f"/home/yomu/Elysia/model_cache/{local_model_name}"
    
    # 检查本地模型是否存在
    if os.path.exists(local_model_path):
        print(f"[Debug] Using local model: {local_model_path}")
        return HuggingFaceEmbeddings(
            model_name=local_model_path,  # 使用本地路径
            model_kwargs={'device': device, 'trust_remote_code': True},
            encode_kwargs={'normalize_embeddings': True}
        )
    else:
        print(f"[Debug] Local model not found at {local_model_path}, downloading...")
        return HuggingFaceEmbeddings(
            model_name=model,
            model_kwargs={'device': device, 'trust_remote_code': True},
            encode_kwargs={'normalize_embeddings': True},
            cache_folder="/home/yomu/Elysia/model_cache"
        )

from pymilvus import MilvusClient

from datetime import timedelta

def timedelta_to_text(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())

    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)

from logging import Logger
import json

def parse_json(raw_content, logger: Logger)-> list[dict]:
    """Parse JSON content from raw string."""
    if not raw_content:
        return [{}]
    try:
        data = json.loads(raw_content)
        return data
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return [{}]