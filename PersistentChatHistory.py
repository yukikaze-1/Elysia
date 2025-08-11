from typing import List, Optional
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from pymilvus import MilvusClient
from datetime import datetime
import asyncio
import threading
import concurrent.futures
from Utils import MessageIDGenerator, SyncMessageIDGenerator, create_embedding_model

class GlobalChatMessageHistory(BaseChatMessageHistory):
    """全局单例聊天历史"""
    
    _instance = None
    _initialized = False
    GLOBAL_SESSION_ID = "global_chat_session"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.session_id = self.GLOBAL_SESSION_ID
        self.collection_name = "chat_sessions"
        
        # 内存中的聊天历史
        self.memory_history = ChatMessageHistory()
        
        # Milvus相关
        self.milvus_client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
        self.embedding_model = create_embedding_model()
        
        # 使用持久化的ID生成器
        self.id_generator = SyncMessageIDGenerator()
        
        self.auto_sync = True
        self.pending_messages = []
        
        # 创建线程池用于异步任务
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="chat_history")
        
        # 初始化
        self._ensure_collection()
        # 同步加载历史记录
        self._load_history_from_db_sync()
        
        self._initialized = True
        print(f"初始化全局聊天历史，会话ID: {self.session_id}")
    
    def _load_history_from_db_sync(self):
        """同步从数据库加载历史记录到内存"""
        try:
            filter_expr = f'session_id == "{self.session_id}"'
            results = self.milvus_client.query(
                collection_name=self.collection_name,
                filter=filter_expr,
                output_fields=["message_type", "content", "sequence_number"],
                limit=1000
            )
            
            # 按序列号排序
            results.sort(key=lambda x: x.get("sequence_number", 0))
            
            # 加载到内存
            for result in results:
                message_type = result.get("message_type")
                content = result.get("content", "")
                
                if message_type == "human":
                    self.memory_history.add_message(HumanMessage(content=content))
                elif message_type == "ai":
                    self.memory_history.add_message(AIMessage(content=content))
                    
            print(f"从数据库加载了 {len(results)} 条历史消息到内存")
            
        except Exception as e:
            print(f"加载历史记录失败: {e}")
    
    def _ensure_collection(self):
        """确保集合存在"""
        if not self.milvus_client.has_collection(self.collection_name):
            self._create_collection()
        self.milvus_client.load_collection(self.collection_name)
    
    def _create_collection(self):
        """创建聊天会话集合"""
        from pymilvus import DataType
        
        schema = self.milvus_client.create_schema(
            collection_name=self.collection_name,
            auto_id=False,
            enable_dynamic_field=True
        )
        
        schema.add_field(field_name="message_id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="session_id", datatype=DataType.VARCHAR, max_length=255)
        schema.add_field(field_name="message_type", datatype=DataType.VARCHAR, max_length=50)
        schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=65535)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=1024)
        schema.add_field(field_name="timestamp", datatype=DataType.VARCHAR, max_length=255)
        schema.add_field(field_name="sequence_number", datatype=DataType.INT64)
        
        self.milvus_client.create_collection(collection_name=self.collection_name, schema=schema)
        
        # 创建索引
        index_params = self.milvus_client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="IVF_FLAT",
            metric_type="COSINE",
            params={"nlist": 1024}
        )
        self.milvus_client.create_index(
            collection_name=self.collection_name,
            index_params=index_params
        )
    
    @property
    def messages(self) -> List[BaseMessage]:
        """返回内存中的消息"""
        return self.memory_history.messages
    
    def add_message(self, message: BaseMessage) -> None:
        """添加消息"""
        # 总是添加到内存
        self.memory_history.add_message(message)
        
        if self.auto_sync:
            # 使用线程池执行同步存储
            self.executor.submit(self._store_message_to_db_sync, message)
        else:
            # 添加到待同步队列
            self.pending_messages.append(message)
    
    def _store_message_to_db_sync(self, message: BaseMessage):
        """同步存储消息到数据库"""
        try:
            # 获取序列号
            sequence_number = self._get_next_sequence_number()
            
            # 修复 BaseMessage 属性访问
            content_text = str(message.content)
            
            # 生成向量嵌入（同步）
            try:
                vector = self.embedding_model.embed_documents([content_text])
            except Exception as embed_error:
                print(f"生成嵌入失败: {embed_error}")
                # 使用零向量作为备选
                vector = [[0.0] * 1024]
            
            # 确定消息类型
            message_type = "human" if isinstance(message, HumanMessage) else "ai"
            
            # 准备数据
            data = {
                "message_id": self.id_generator.get_next_id(),  # 使用持久化ID生成器
                "session_id": self.session_id,
                "message_type": message_type,
                "content": content_text,
                "vector": vector[0] if isinstance(vector, list) and len(vector) > 0 else vector,
                "timestamp": datetime.now().strftime("%Y_%m_%d %H:%M:%S"),
                "sequence_number": sequence_number
            }
            
            # 插入到 Milvus
            self.milvus_client.insert(
                collection_name=self.collection_name,
                data=[data]
            )
            
            # 刷新
            self.milvus_client.flush(collection_name=self.collection_name)
            
            print(f"消息已存储到数据库: {content_text[:50]}...")
            
        except Exception as e:
            print(f"存储消息到数据库失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_next_sequence_number(self) -> int:
        """获取下一个序列号"""
        try:
            # 查询当前会话中所有消息的序列号
            filter_expr = f'session_id == "{self.session_id}"'
            results = self.milvus_client.query(
                collection_name=self.collection_name,
                filter=filter_expr,
                output_fields=["sequence_number"],
                limit=1000
            )
            
            if results:
                # 找到最大序列号，然后+1
                max_sequence = max(result.get("sequence_number", 0) for result in results)
                return max_sequence + 1
            else:
                # 如果没有消息，从1开始
                return 1
                
        except Exception as e:
            print(f"获取序列号失败: {e}")
            # 备选方案：使用内存中的消息数量+1
            return len(self.memory_history.messages) + 1
    
    def clear(self) -> None:
        """清空内存和数据库中的消息"""
        print(f"开始清除聊天历史记录...")
        
        # 记录清除前的消息数量
        memory_count = len(self.memory_history.messages)
        print(f"内存中有 {memory_count} 条消息")
        
        # 清空内存
        self.memory_history.clear()
        print("✅ 内存中的聊天历史已清空")
        
        # 清空数据库
        try:
            filter_expr = f'session_id == "{self.session_id}"'
            
            # 查询要删除的记录数量
            results = self.milvus_client.query(
                collection_name=self.collection_name,
                filter=filter_expr,
                output_fields=["message_id"],
                limit=10000  # 设置一个足够大的限制
            )
            db_count = len(results)
            print(f"Milvus中有 {db_count} 条记录")
            
            if db_count > 0:
                # 删除记录
                self.milvus_client.delete(
                    collection_name=self.collection_name,
                    filter=filter_expr
                )
                
                # 刷新以确保删除操作完成
                self.milvus_client.flush(collection_name=self.collection_name)
                print(f"✅ Milvus中的 {db_count} 条记录已删除")
            else:
                print("✅ Milvus中没有需要删除的记录")
                
            print("聊天历史记录清除完成")
            
        except Exception as e:
            print(f"✗ 清空数据库消息失败: {e}")
            raise e
    
    def reload_from_db(self) -> int:
        """重新从数据库加载历史记录"""
        print("开始重新加载聊天历史...")
        
        # 清空当前内存中的历史
        old_count = len(self.memory_history.messages)
        self.memory_history.clear()
        
        # 重新加载
        self._load_history_from_db_sync()
        new_count = len(self.memory_history.messages)
        
        print(f"重新加载完成: {old_count} -> {new_count} 条消息")
        return new_count

