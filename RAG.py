import os
from pymilvus import MilvusClient, DataType


class RAG:
    """
        记忆RAG
    """
    def __init__(self):
        self.milvus_client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
    
    
    