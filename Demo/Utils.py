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

import time
import numpy as np
from pymilvus import MilvusClient


class MilvusAgent:
    """milvus的接口类"""
    def __init__(self, collection_name: str = "l2_associative_memory"):
        self.milvus_client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
        self.collection_name = collection_name
        self.embedding_model = create_embedding_model()
        
    def retrieve(self, query_text: str, top_k: int = 5):
        """检索记忆"""
        vector = self.embedding_model.embed_documents([query_text])
        
        results = self.milvus_client.search(
            collection_name=self.collection_name,
            anns_field="embedding",
            data=[vector],
            limit=20,
            search_params={"metric_type": "L2"},
            output_fields=["content", "poignancy", "timestamp"]
        )
        result: list[dict] = results[0]
        # 重排
        result = self.rerank(result, top_k) 
        
        
    def rerank(self, results: list[dict], top_k: int = 5):
        """重排记忆"""
        candidates = []
        current_time = int(time.time())
        
        # 3. Python 内存重排序
        for hit in results:
            # A. 相似度 (Milvus 返回的是距离，需要转为相似度，L2距离越小越相似)
            # 简单处理：假设距离在 0-2 之间归一化，或者直接用 1/(1+distance)
            similarity = 1 / (1 + hit['distance'])
            
            # B. 情绪权重 (归一化到 0-1)
            poignancy_score = hit["entity"].get("poignancy") / 10.0
            
            # C. 时间新鲜度 (使用指数衰减)
            # 比如：每过 7 天，新鲜度减半
            days_diff = (current_time - hit["entity"].get("timestamp")) / (86400)
            recency_score = np.exp(-0.1 * days_diff) 
            
            # D. 综合打分 (权重可调)
            final_score = (similarity * 0.5) + (poignancy_score * 0.4) + (recency_score * 0.1)
            
            candidates.append({
                "content": hit["entity"].get("content"),
                "score": final_score,
                "debug_info": f"Sim:{similarity:.2f}, Poi:{poignancy_score:.2f}, Time:{recency_score:.2f}"
            })
        
        # 4. 按最终分数排序并切片
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_k]