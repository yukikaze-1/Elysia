
from openai import OpenAI
from Demo.MicroReflector import MicroReflector, MicroMemory
from Demo.MacroReflector import MacroReflector, MacroMemory
from Demo.Utils import MilvusAgent
from Demo.Session import ChatMessage

class MemoryReflector:
    """
    ORP System: MemoryReflector 模块，用于从对话中提取长期记忆节点
    会持续运行在后台
    """
    def __init__(self, openai_client: OpenAI, collection_name: str = "l2_associative_memory"):
        self.openai_client = openai_client
        self.collection_name= collection_name
        self.milvus_agent = MilvusAgent(self.collection_name)
        
        self.micro_reflector = MicroReflector(self.openai_client, self.collection_name)
        self.macro_reflector = MacroReflector(self.openai_client, self.collection_name)

    

def test_l1_to_l2(reflector: MemoryReflector, conversations: list[ChatMessage]):
    """测试l1到l2的反思"""
    memories: list[MicroMemory] = reflector.micro_reflector.run_micro_reflection(conversations)
    print("Extracted Memories:")
    for memory in memories:
        print(memory.to_dict())
    print("---------------------")
    return memories


def test():
    # 准备数据
    from dotenv import load_dotenv
    from pymilvus import MilvusClient
    
    import os
    load_dotenv()
    milvus_client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
    openai_client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com"))
    
    collection_name = "l2_associative_memory"
    
    # 清空数据库
    if milvus_client.has_collection(collection_name):
        print("Dropping collection for cleanup.")
        milvus_client.drop_collection(collection_name)
    
    # 创建collection    
    if not milvus_client.has_collection(collection_name):
        print("Creating Milvus collection for L2 memories...")
        from Demo.Utils import create_memory_collection
        create_memory_collection(collection_name, milvus_client)
    else:
        print("Milvus collection already exists.")
        milvus_client.load_collection(collection_name)
        
    reflector = MemoryReflector(openai_client)
        
    
    from test_dataset import (conversations_02, conversations_01, conversations_03)
    # 测试l1——to-l2
    conversations = conversations_03
    res = test_l1_to_l2(reflector, conversations)
        
    

def inject_milvus_test_data():
      return test()
        
    
    
if __name__ == "__main__":
    inject_milvus_test_data()
    
    