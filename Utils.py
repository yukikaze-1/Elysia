import os
import torch
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