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


def create_memory_collection(collection_name: str, milvus_client: MilvusClient):
    """  创建用于存储长期记忆的 Milvus Collection  """
    # 如果存在先删除 (测试用，生产环境请注释)
    if milvus_client.has_collection(collection_name):
        milvus_client.drop_collection(collection_name)
        
    from pymilvus import DataType
        
    schema = milvus_client.create_schema(
        collection_name=collection_name,
        auto_id=True,
        enable_dynamic_field=True
    )
    schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True)
    schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=1024)
    schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(field_name="memory_type", datatype=DataType.VARCHAR, max_length=20)
    schema.add_field(field_name="poignancy", datatype=DataType.INT8)
    schema.add_field(field_name="timestamp", datatype=DataType.INT64)
    schema.add_field(field_name="keywords", datatype=DataType.ARRAY, element_type=DataType.VARCHAR, max_length=128,max_capacity=50)
    
    milvus_client.create_collection(collection_name=collection_name, schema=schema)
    
    # 创建索引 (加快检索)
    index_params = milvus_client.prepare_index_params()
    index_params.add_index(
        field_name="embedding",
        index_type="IVF_FLAT",
        metric_type="L2",
        params={"nlist": 1024}
    )
    milvus_client.create_index(
        collection_name=collection_name, 
        index_params=index_params
    )
    milvus_client.load_collection(collection_name=collection_name) # 加载到内存
    print(f"Collection {collection_name} ready.")


class MilvusAgent:
    """milvus的接口类"""
    def __init__(self, collection_name: str = "l2_associative_memory"):
        self.milvus_client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
        self.collection_name = collection_name
        if not self.milvus_client.has_collection(self.collection_name):
            print(f"Warnning: No collection named {self.collection_name}!")
            create_memory_collection(self.collection_name, self.milvus_client)
        else:
            # 预加载
            self.milvus_client.load_collection(self.collection_name)
        self.embedding_model = create_embedding_model()
    
    def query(self, filter: str, output_fields: list[str]):
        """检索记忆(标量搜索)"""
        res = self.milvus_client.query(
            collection_name=self.collection_name,
            filter=filter,
            output_fields=output_fields,
            limit=10000
        )
        return res
        
    def retrieve(self, query_text: str, top_k: int = 5)->list[dict]:
        """检索记忆(向量搜索)"""
        vector = self.embedding_model.embed_documents([query_text])
        
        results = self.milvus_client.search(
            collection_name=self.collection_name,
            anns_field="embedding",
            data=vector,
            limit=20,
            search_params={"metric_type": "L2"},
            output_fields=["content", "poignancy", "timestamp"]
        )
        result: list[dict] = results[0]
        # 重排
        result = self.rerank(result, top_k)
        return result 
        
        
    def rerank(self, results: list[dict], top_k: int = 5)->list[dict]:
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
    
    
    def forget_trivial(self, threshold: int):
        """清理部分不重要的记忆"""
        # TODO 后续实现
        pass
    
    def dump_states(self):
        """查看现在存了多少记忆"""
        res = self.milvus_client.query(
            collection_name=self.collection_name,
            output_fields=["count(*)"],
            )
        print(f"Total memories: {res}")
        
        
  

    