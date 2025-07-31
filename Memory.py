from gc import collect
import httpx
from sklearn.utils import resample
from sympy import limit, true
from Utils import create_embedding_model
from pymilvus import MilvusClient, DataType
from datetime import datetime
from ChatMessage import ChatMessage, MessageAttachment, AttachmentFile
from typing import Dict, List
from langchain_huggingface import HuggingFaceEmbeddings

class DailyMemory:
    def __init__(self, model: HuggingFaceEmbeddings):
        self.milvus_client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
        self.llm_client = httpx.AsyncClient(base_url="http://localhost:11434")
        self.daily_collection_name = "daily_memory"
        self.chat_message_collection_name = "chat_message"
        self.embedding_model = model

    def _ensure_collections_loaded(self):
        """确保集合已加载"""
        try:
            if self.milvus_client.has_collection(self.daily_collection_name):
                self.milvus_client.load_collection(collection_name=self.daily_collection_name)
            if self.milvus_client.has_collection(self.chat_message_collection_name):
                self.milvus_client.load_collection(collection_name=self.chat_message_collection_name)
        except Exception as e:
            print(f"Warning: Could not load collections: {e}")

    async def summary_daily_memory(self)-> str:
        """获取每日记忆的摘要"""
        print("Generating daily memory summary...")
        # 确保集合已加载
        self._ensure_collections_loaded()
        
        # 刷新聊天消息集合
        self.milvus_client.flush(collection_name=self.chat_message_collection_name)
        
        # 获取当前日期
        today = datetime.now().strftime("%Y_%m_%d")
        partition_name = today
        
        if not self.milvus_client.has_collection(self.chat_message_collection_name):
            raise ValueError(f"Collection {self.chat_message_collection_name} does not exist.")
        
        if not self.milvus_client.has_collection(self.daily_collection_name):
            raise ValueError(f"Collection {self.daily_collection_name} does not exist.")
        
        if not self.milvus_client.has_partition(self.chat_message_collection_name, partition_name):
            raise ValueError(f"Partition for today {partition_name} does not exist.")
        
        # 查询当天的所有消息
        filter_expr = f'timestamp like "{today}%"'  
        
        messages = self.milvus_client.query(
            collection_name=self.chat_message_collection_name,
            partition_names=[partition_name],
            filter=filter_expr,
            output_fields=["message_id", "timestamp", "role", "content"]
        )
        
        if messages:
            print(f"Debug: First message timestamp: {messages[0].get('timestamp')}")
        
        if not messages:
            print(f"No messages for today: {today}.")
            return f"No messages for today:{today}."
        
        summary_prompt = f"""请对以下用'###'包含的聊天记录生成客观的摘要。

            要求：
            1. 总结主要话题
            2. 提取关键信息  
            3. 控制在200字以内
            4. 只输出总结的内容
            5. 不要输出额外的信息

            聊天记录：
            ###
            {chr(10).join(message['content'] for message in messages)}
            ###
        """
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
        print("Daily memory summary generated successfully.")
        return content
        

    async def daily_memory_storage(self, daily_memory: str) -> bool:
        """存储每日记忆"""
        if not daily_memory:
            print("No daily memory to store.")
            return False
        daily_memory_vector = await self.embedding_model.aembed_documents([daily_memory])
        
        # 获取当前日期
        today = datetime.now().strftime("%Y_%m_%d")
        
        if not self.milvus_client.has_collection(self.daily_collection_name):
            raise ValueError(f"Collection {self.daily_collection_name} does not exist.")
        
        # 插入每日记忆到 Milvus
        data = [
            {
                "vector": daily_memory_vector[0],  
                "timestamp": today,
                "role": "system",
                "content": daily_memory
            }
        ]
        print(f"插入数据: {data[0].get('timestamp')}, {data[0].get('content')}")  
        res = self.milvus_client.insert(
            collection_name=self.daily_collection_name,
            data=data,
        )
        
        # 刷新集合以确保数据可查询
        self.milvus_client.flush(collection_name=self.daily_collection_name)
        
        print(f"Daily memory stored successfully: {res}")
        return True
    
        

class Memory:
    def __init__(self):
        self.milvus_client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
        self.chat_message_collection_name = "chat_message"
        self.daily_memory_collection_name = "daily_memory"
        self.embedding_model = create_embedding_model()
        self.drop()
        self.check()
        # 在集合创建完成后再初始化 DailyMemory
        self.daily_memory = DailyMemory(model=self.embedding_model)
        
    def check(self)->None:
        """检查 Milvus 集合和分区是否存在"""
        # 检查存储chatmessage的集合
        if not self.milvus_client.has_collection(self.chat_message_collection_name):
            print(f"Collection {self.chat_message_collection_name} does not exist, creating...")
            self.create_chat_message_collection(self.chat_message_collection_name)
        print(f"Collection {self.chat_message_collection_name} exists.")
        
        # 检查存储chatmessage的分区是否存在    
        today = datetime.now().strftime("%Y_%m_%d")
        if not self.milvus_client.has_partition(self.chat_message_collection_name, today):
            print(f"Partition for today {today} does not exist in collection {self.chat_message_collection_name}, creating...")
            self.create_chat_message_partition()
        print(f"Partition for today {today} exists in collection {self.chat_message_collection_name}.")    

        # 检查存储每日记忆的集合
        if not self.milvus_client.has_collection(self.daily_memory_collection_name):
            print(f"Collection {self.daily_memory_collection_name} does not exist, creating...")
            self.create_daily_memory_collection(self.daily_memory_collection_name)
        print(f"Collection {self.daily_memory_collection_name} exists.")   

    def drop(self):
        """删除 Milvus 集合和分区"""
        if self.milvus_client.has_collection(self.chat_message_collection_name):
            self.milvus_client.drop_collection(collection_name=self.chat_message_collection_name)
            print(f"Collection {self.chat_message_collection_name} dropped.")
        
        if self.milvus_client.has_collection(self.daily_memory_collection_name):
            self.milvus_client.drop_collection(collection_name=self.daily_memory_collection_name)
            print(f"Collection {self.daily_memory_collection_name} dropped.")
            
    def create_chat_message_partition(self):
        """创建 ChatMessage 的日期分区"""
        # 获取当前日期
        today = datetime.now().strftime("%Y_%m_%d")
        partition_name = today

        if not self.milvus_client.has_collection(self.chat_message_collection_name):
            raise ValueError(f"Collection {self.chat_message_collection_name} does not exist.")

        if self.milvus_client.has_partition(self.chat_message_collection_name, partition_name):
            print(f"Partition for today {today} already exists in collection {self.chat_message_collection_name}.")
            return

        self.milvus_client.create_partition(collection_name=self.chat_message_collection_name, partition_name=partition_name)

    def create_daily_memory_collection(self, collection_name: str="daily_memory"):
        """创建 存储每日记忆的 Milvus 集合"""
        schema = self.milvus_client.create_schema(
            collection_name=collection_name,
            auto_id=False,
            enable_dynamic_field=True
        )
        
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=1024)  # 假设向量维度为768
        schema.add_field(field_name="timestamp", datatype=DataType.VARCHAR, max_length=255, is_primary=True)
        schema.add_field(field_name="role", datatype=DataType.VARCHAR, max_length=255)
        schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=65535)
        
        self.milvus_client.create_collection(collection_name=collection_name, schema=schema)
        print(f"Collection {collection_name} created successfully.")
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
        print(f"Index created for collection: {collection_name}.")
             
    def create_chat_message_collection(self, collection_name: str="chat_message"):       
        """创建 Milvus 集合用于存储聊天消息"""
        schema = self.milvus_client.create_schema(
            collection_name=collection_name,
            auto_id=False,
            enable_dynamic_field=True
        )
        
        schema.add_field(field_name="message_id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=1024)  # 假设向量维度为768
        schema.add_field(field_name="timestamp", datatype=DataType.VARCHAR, max_length=255)
        schema.add_field(field_name="role", datatype=DataType.VARCHAR, max_length=255)
        schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=65535)
        
        self.milvus_client.create_collection(collection_name=collection_name, schema=schema)
        print(f"Collection {collection_name} created successfully.")
        
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
        print(f"Index created for collection: {collection_name}.") 
        
    async def insert_chat_message(self, messages: List[ChatMessage]):
        """"插入聊天消息到 Milvus"""
        vectors_content: List[List[float]]  = await self.embedding_model.aembed_documents(
            [message.content for message in messages]
        )
        today = datetime.now().strftime("%Y_%m_%d")
        res = self.milvus_client.insert(
                collection_name=self.chat_message_collection_name,
                data=[{
                        "role": message.role,
                        "content": message.content,
                        "vector": vector_content,
                        "timestamp": message.timestamp,
                        "message_id": message.message_id
                    }for message, vector_content in zip(messages, vectors_content)
                ],
                partition_name=today,
            )
        self.milvus_client.flush(collection_name=self.chat_message_collection_name)
        print(f"Inserted {len(messages)} messages into collection {self.chat_message_collection_name}).")
        return res

    async def search_memory(self, query: str, threshold: float = 0.3)-> List[List[Dict]]:
        """在 Milvus 中搜索记忆"""
        query_vector = await self.embedding_model.aembed_documents([query])
        if not query_vector:
            raise ValueError("Query vector is empty.")
        
        # 确保集合已加载
        if not self.milvus_client.has_collection(self.chat_message_collection_name):
            raise ValueError(f"Collection {self.chat_message_collection_name} does not exist.")
        
        self.milvus_client.load_collection(collection_name=self.chat_message_collection_name)
        
        results = self.milvus_client.search(
            collection_name=self.chat_message_collection_name,
            data=query_vector,
            anns_field="vector",
            limit=5,
            output_fields=["timestamp", "role", "content"]
        )
        
        return results
    
    async def test(self):
        # 插入测试数据
        from test_dataset import messages, Test
        
        # # 测试自己的数据
        # if not messages:
        #     print("No messages to insert.")
        #     return
        # print(messages[0].timestamp)
        # res = await self.insert_chat_message(messages)
        # print(f"Insert response: {res}")
        
        # res = await self.daily_memory.daily_memory_storage()
        # print(f"Daily memory storage result: {res}")
        
        # # 刷新集合以确保数据可查询
        # self.milvus_client.flush(collection_name=self.daily_memory_collection_name)
        # print("Daily memory collection flushed.")
        
        # 测试 conversations
        test = Test()
        print("Generating test conversations...")
        test_conversations = await test.generate_test_conversations()
        
        # 显示前几条消息
        for msg in test_conversations:
            print(f"[{msg.timestamp}] {msg.role}: {msg.content}")
        
        if not test_conversations:
            print("No test conversations to insert.")
            return
        res = await self.insert_chat_message(test_conversations)
        print(f"Test conversations inserted: {res}")
        
        memory_summary = await self.daily_memory.summary_daily_memory()
        print(f"Daily memory summary: {memory_summary}")
        res = await self.daily_memory.daily_memory_storage(memory_summary)
        print(f"Daily memory storage result: {res}")
        
        # 刷新集合以确保数据可查询
        self.milvus_client.flush(collection_name=self.daily_memory_collection_name)
        print("Daily memory collection flushed.")
        
        
        # 测试查询每日总结后的记忆(daily_memory)
        today = datetime.now().strftime("%Y_%m_%d")
        filter_expr = f'timestamp == "{today}"'
        res = self.milvus_client.query(
            collection_name=self.daily_memory_collection_name,
            filter=filter_expr,
            output_fields=["timestamp", "role", "content"]  
        )
        print(f"Daily memory query response: {res}")

        # 测试查询记忆(chat_message)
        query = "机器学习"
        print(f"Searching memory for query: {query}")
        res = await self.search_memory(query)
        # res_content = [item[0].get("content") for item in res]
        print(f"Search results for query '{query}': {res}")
        
if __name__ == "__main__":
    import asyncio
    memory = Memory()
    asyncio.run(memory.test())
    collect()  # 强制垃圾回收，清理内存

