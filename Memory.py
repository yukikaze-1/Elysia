from gc import collect
import httpx
from numpy import partition
from pymilvus import MilvusClient, DataType
from datetime import datetime

class DailyMemory:
    def __init__(self):
        self.milvus_client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
        self.llm_client = httpx.AsyncClient(base_url="http://localhost:11434")
        
        self.milvus_client.load_collection(collection_name="daily_memory")
        
    async def summary_daily_memory(self):
        """获取每日记忆的摘要"""
        # 获取当前日期
        today = datetime.now().strftime("%Y_%m_%d")
        collection_name = "daily_memory"
        partition_name = f"daily_memory_{today}"
        
        if not self.milvus_client.has_collection(collection_name):
            raise ValueError(f"Collection {collection_name} does not exist.")
        if not self.milvus_client.has_partition(collection_name, partition_name):
            raise ValueError(f"Partition for today {partition_name} does not exist.")
        
        # 查询当天的所有消息
        filter_expr = f"timestamp >= '{datetime.now().strftime("%Y-%m-%d")} 00:00:00' and timestamp < '{datetime.now().strftime("%Y-%m-%d")} 23:59:59'"
        messages = self.milvus_client.query(
            collection_name=collection_name,
            partition_name=partition_name,
            filter=filter_expr,
            output_fields=["message_id", "timestamp", "role", "content"]
        )
        
        if not messages:
            return f"No messages for today:{today}."
        
        summary_prompt = f"""请对以下聊天记录生成客观的摘要。

            要求：
            1. 总结主要话题
            2. 提取关键信息  
            3. 控制在100字以内

            聊天记录：
            {chr(10).join(message['content'] for message in messages)}
            
        """
        print(f"summary_prompt: {summary_prompt}")
        # 构建请求数据
        data = {
            "model": "qwen2.5",
            "messages": [
                {
                    "role": "user",
                    "content": summary_prompt
                }
            ],
            "stream": False,
            "options": None  # Ollama 使用 options 字段
        }
        try:
            response = await self.llm_client.post(url="/api/chat", 
                                                json=data, 
                                                headers={"Content-Type": "application/json"},
                                                timeout=60.0)
            response.raise_for_status()
        except httpx.RequestError as e:
            raise ValueError(f"Request error: {e}")
        except httpx.HTTPStatusError as e:
            raise ValueError(f"HTTP error: {e}")
        
        response_data = response.json()
        content = response_data['message'].get("content", "")
        return content
        

    def daily_memory_storage(self):
        pass

class Memory:
    def __init__(self):
        self.milvus_client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
        self.daily_memory = DailyMemory()
        
        if not self.milvus_client.has_collection("daily_memory"):
            self.create_collection("daily_memory")
        if not self.milvus_client.has_partition("daily_memory", f"daily_memory_{datetime.now().strftime('%Y_%m_%d')}"):
            partition_name = f"daily_memory_{datetime.now().strftime('%Y_%m_%d')}"
            self.create_daily_memory_partition(partition_name)

    def create_daily_memory_partition(self, partition_name: str):
        """创建 DailyMemory 分区"""
        collection_name = "daily_memory"
        # 获取当前日期
        today = datetime.now().strftime("%Y_%m_%d")
        if not self.milvus_client.has_collection(collection_name):
            raise ValueError(f"Collection {collection_name}does not exist.")
        if self.milvus_client.has_partition("daily_memory", partition_name):
            print(f"Partition for today {today} already exists in collection daily_memory.")
            return 
        
        self.milvus_client.create_partition(collection_name=collection_name, partition_name=partition_name)
         
    def create_collection(self, collection_name: str):
        """创建 Milvus 集合"""
        schema = self.milvus_client.create_schema(
            collection_name=collection_name,
            auto_id=False,
            enable_dynamic_field=True
        )
        
        schema.add_field(field_name="message_id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR)
        schema.add_field(field_name="timestamp", datatype=DataType.VARCHAR, max_length=255)
        schema.add_field(field_name="role", datatype=DataType.VARCHAR, max_length=255)
        schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=65535)
        
        self.milvus_client.create_collection(collection_name=collection_name, schema=schema)
        
        # 创建索引（以 IVF_FLAT 为例）
        index_params = self.milvus_client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="IVF_FLAT",
            metric_type="COSINE",
            params={"nlist": 1024}
        )
        self.milvus_client.create_index(
            collection_name=collection_name,
            index_params=index_params
        )
        print(f"Index created for collection {collection_name}.")
        
        
async def test():
    memory = Memory()
    summary = await memory.daily_memory.summary_daily_memory()
    print(summary)
        
if __name__ == "__main__":
    import asyncio
    asyncio.run(test())
    collect()  # 强制垃圾回收，清理内存
    
    