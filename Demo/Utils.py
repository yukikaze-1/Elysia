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

def create_micro_memory_collection(collection_name: str, milvus_client: MilvusClient):
    """  创建用于Micro Memory 的 Milvus Collection  """
    #  如果存在先删除 (测试用，生产环境请注释)
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
    print("Created Micro Memory collection.")
    print(f"Collection {collection_name} ready.")


def create_macro_memory_collection(collection_name: str, milvus_client: MilvusClient):
    """  创建用于Macro Memory 的 Milvus Collection  """
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
    schema.add_field(field_name="diary_content", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(field_name="dominant_emotion", datatype=DataType.VARCHAR, max_length=65535)
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
    print("Created Micro Memory collection.")
    print(f"Collection {collection_name} ready.")        
  

    