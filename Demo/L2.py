from pymilvus import MilvusClient
from Demo.Utils import create_embedding_model

milvus_client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")


# 2. 定义 Schema
def create_memory_collection(milvus_client: MilvusClient, collection_name: str ="l2_associative_memory"):
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
    schema.add_field(field_name="type", datatype=DataType.VARCHAR, max_length=20)
    schema.add_field(field_name="poignancy", datatype=DataType.INT8)
    schema.add_field(field_name="timestamp", datatype=DataType.INT64)
    
    milvus_client.create_collection(collection_name=collection_name, schema=schema)
    
    # 创建索引 (加快检索)
    index_params = milvus_client.prepare_index_params()
    index_params.add_index(
        field_name="embedding",
        index_type="IVF_FLAT",
        metric_type="COSINE",
        params={"nlist": 1024}
    )
    milvus_client.create_index(
        collection_name=collection_name, 
        index_params=index_params
    )
    milvus_client.load_collection(collection_name=collection_name) # 加载到内存
    print(f"Collection {collection_name} ready.")
    

class L2_Module:
    def __init__(self, milvus_client: MilvusClient, collection_name: str):
        self.milvus_client = milvus_client
        self.embedding_model = create_embedding_model()
        self.collection_name = collection_name
        
    
        

def test_prepare_datasets(milvus_client: MilvusClient, collection_name: str = "l2_associative_memory"):
    """生成测试数据并插入milvus"""
    
        
        
def test():
    # 准备数据
    from dotenv import load_dotenv
    import os
    load_dotenv()
    milvus_client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
    collection_name = "l2_associative_memory"
    
    l2 = L2_Module(milvus_client, collection_name)

if __name__ == "__main__":
    test()
    
    