"""
L2 记忆存储与检索模块
"""

import time
from typing import Literal, List, overload, Union
from langchain_huggingface import HuggingFaceEmbeddings
import numpy as np
import threading
from pymilvus import MilvusClient

from Demo.Utils import create_embedding_model, create_micro_memory_collection, create_macro_memory_collection
from Demo.Layers.Session import SessionState, ChatMessage
from Demo.Workers.Reflector.MacroReflector import MacroMemory
from Demo.Workers.Reflector.MicroReflector import MicroMemory
from Demo.Logger import setup_logger


class MemoryLayer:
    """
    L2 记忆层: 统一管理 '长期向量记忆' (Milvus) 和 '短期会话上下文' (SessionState)
    采用单例模式, 因为 main.py 和 Reflector 都需要访问同一个记忆层实例
    """
    # === [New] 1. 定义类变量用于存储实例和线程锁 ===
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """确保在多线程环境下也只创建一个实例"""
        if not cls._instance:
            with cls._lock:
                # Double Check Locking (双重检查锁)
                if not cls._instance:
                    cls._instance = super(MemoryLayer, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, 
                 micro_memeory_collection_name: str = "micro_memory",
                 macro_memeory_collection_name: str = "macro_memory"
                 ):
        # 防止重复初始化
        # 因为 __new__ 返回同一个实例后，Python 依然会调用 __init__
        # 所以必须判断是否已经初始化过
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.logger = setup_logger("MemoryLayer")
        
        # === 1. 初始化长期记忆 (Milvus) ===
        self.milvus_client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
        self.micro_memeory_collection_name = micro_memeory_collection_name
        self.macro_memeory_collection_name = macro_memeory_collection_name
        
        # 检查并创建micro memory集合
        if not self.milvus_client.has_collection(self.micro_memeory_collection_name):
            self.logger.warning(f"No collection named {self.micro_memeory_collection_name}!")
            self.logger.info("Creating...")
            create_micro_memory_collection(self.micro_memeory_collection_name, self.milvus_client)
            self.logger.info(f"Created collection '{self.micro_memeory_collection_name}'")
        else:
            # 预加载
            self.milvus_client.load_collection(self.micro_memeory_collection_name)
            self.logger.info(f"Loaded collection '{self.micro_memeory_collection_name}'")
            
        # 检查并创建macro memory集合
        if not self.milvus_client.has_collection(self.macro_memeory_collection_name):
            self.logger.warning(f"No collection named {self.macro_memeory_collection_name}!")
            self.logger.info("Creating...")
            create_macro_memory_collection(self.macro_memeory_collection_name, self.milvus_client)
            self.logger.info(f"Created collection '{self.macro_memeory_collection_name}'")
        else:
            # 预加载
            self.milvus_client.load_collection(self.macro_memeory_collection_name)
            self.logger.info(f"Loaded collection '{self.macro_memeory_collection_name}'")
            
        # 初始化 Embedding 模型
        self.embedding_model: HuggingFaceEmbeddings = create_embedding_model(debug_info="L2 Memory Layer Embedding Model")
        self.logger.info("Initialized embedding model for MemoryLayer.")
        
        # === 2. 初始化短期记忆 (Session) ===
        # 在单用户场景下，直接持有一个 SessionState 实例
        # 如果是多用户，这里应该是一个 Dict[user_id, SessionState]
        self.session = SessionState(user_name="User", role="Elysia")
        self.logger.info("Initialized SessionState for short-term memory.")
        
        # 标记为已初始化
        self._initialized = True
        self.logger.info("MemoryLayer initialized successfully.")
        
        
    # ===========================================================================================================================
    # 核心接口 (供 Dispatcher 调用)
    # ===========================================================================================================================
    
    def retrieve_context(self, query: str) -> tuple[list[ChatMessage], list[MicroMemory], list[MacroMemory]]:
        """
        [接口方法] 获取混合上下文 (短期对话流 + 长期相关记忆 + 日常总结记忆)
        参数:
            query: 用于检索相关记忆的查询文本
        返回: 
            (短期对话流, 长期相关记忆, 日常总结记忆)
        """
        # 1. 获取短期记忆 (正在进行的对话)
        history: list[ChatMessage] = self.session.get_history()
        
        # 2. 获取长期记忆 (从 Milvus 检索相关经历)
        micro_memories: list[MicroMemory] = self.retrieve('Micro', query_text=query, top_k=5)
        
        # 3. 获取日常总结记忆
        macro_memories: list[MacroMemory] = self.retrieve('Macro', query_text=query, top_k=3)
        
        return history, micro_memories, macro_memories
    
    
    def add_short_term_memory(self, messages: list[ChatMessage])-> None:
        """
        [接口方法] 存储一轮新的对话到 RAM
        """
        self.session.add_messages(messages)
    
    
    def get_recent_summary(self, limit: int = 3) -> list[ChatMessage]:
        """
        [接口方法] 获取最近几句对话 (给 L1 做主动性决策用)
        返回: 最近 limit 条消息列表
        """
        return self.session.get_recent_items(limit)
    
    
    # ===========================================================================================================================
    # 内部函数实现
    # ===========================================================================================================================
    
    def save_micro_memory(self, memories: list[MicroMemory]):
        """
        [接口方法] (供 Reflector 调用) 将micro memory写入milvus
        """
        self.logger.info(f"Storing {len(memories)} Micro Memories...")
        data = []
        # 生成向量
        for mem in memories:
            vector = self.embedding_model.embed_documents([mem.content])
            info = {
                "content": mem.content,
                "embedding": vector,
                "memory_type": mem.memory_type,
                "poignancy": mem.poignancy,
                "keywords": mem.keywords,
                "timestamp": int(mem.timestamp)
            }
            data.append(info)
            
        # 插入
        res = self.milvus_client.insert(
            collection_name=self.micro_memeory_collection_name, 
            data=data
        )
        self.logger.info(f"Stored {len(data)} new memories.\n {res}")
        return res
    
    
    def save_macro_memory(self, memories: list[MacroMemory]):
        """
        [接口方法] (供 Reflector 调用) 将浓缩的日记写入 Milvus
        """
        self.logger.info(f"Saving Macro Memories...")
        data = []
        # 生成向量
        for mem in memories:
            vector = self.embedding_model.embed_documents([mem.diary_content])[0]
            info = {
                "diary_content":mem.diary_content,
                "embedding": vector,
                "poignancy":mem.poignancy,
                "timestamp": int(mem.timestamp),
                "keywords":mem.keywords
            }
            data.append(info)
            
        # 写入 Milvus
        res = self.milvus_client.insert(
            collection_name=self.macro_memeory_collection_name,
            data=data
        )
        self.logger.info(f"Saved to Macro Memory: {memories}")
        return res
    
    
    def query(self, mem_type: Literal['Micro', 'Macro'], filter: str, output_fields: list[str]):
        """
        检索记忆(标量搜索)
        参数:
            mem_type: 记忆类型 ('Micro' 或 'Macro')
            filter: Milvus 查询过滤条件
            output_fields: 需要返回的字段列表
        返回:
            查询结果列表
        """
        self.logger.info(f"Querying {mem_type} Memories with filter: {filter}")
        query_collection_name = self.micro_memeory_collection_name if mem_type == "Micro" else self.macro_memeory_collection_name
        res = self.milvus_client.query(
            collection_name=query_collection_name,
            filter=filter,
            output_fields=output_fields,
            limit=10000,
            consistency_level="Strong"
        )
        self.logger.info(f"Query Completed. Retrieved {len(res)} records.")
        return res
    
    @overload
    def retrieve(self, mem_type: Literal['Micro'], query_text: str, top_k: int = 5) -> List[MicroMemory]:
        ...

    @overload
    def retrieve(self, mem_type: Literal['Macro'], query_text: str, top_k: int = 5) -> List[MacroMemory]:
        ...    
        
    def retrieve(self, mem_type: Literal['Micro', 'Macro'], query_text: str, top_k: int = 5)->list[MicroMemory] | list[MacroMemory]:
        """
        检索记忆(向量搜索)
        参数:
            mem_type: 记忆类型 ('Micro' 或 'Macro')
            query_text: 用于检索的查询文本
            top_k: 返回的记忆数量上限
        返回:
            记忆列表
        """
        # embed 查询向量
        vector = self.embedding_model.embed_documents([query_text])
        
        if mem_type == 'Micro':
            self.logger.info("Retrieving Micro Memories...")
            collection_name = self.micro_memeory_collection_name
            output_fields = ["content", "poignancy", "timestamp", "keywords"]
        else:
            self.logger.info("Retrieving Macro Memories...")
            collection_name = self.macro_memeory_collection_name
            output_fields = ["diary_content", "poignancy", "timestamp", "keywords"]
        
        # 向量检索
        results = self.milvus_client.search(
            collection_name=collection_name,
            anns_field="embedding",
            data=vector,
            limit=20,
            search_params={"metric_type": "L2"},
            output_fields=output_fields
        )
        
        self.logger.info(f"Search {mem_type} results: {results}")
        result: list[dict] = results[0]
        # 重排
        result = self.rerank(mem_type, result, top_k)
        # 格式转换
        res = self.trans(mem_type, result)
        return res
    
    
    def trans(self, type: Literal['Micro', 'Macro'], results: list[dict])-> list[MicroMemory] | list[MacroMemory]:
        """将字典转为类结构"""
        if type == 'Micro':
            return self._trans_to_micro_memeory(results)
        else:
            return self._trans_to_macro_memeory(results)
        
    
    def _trans_to_micro_memeory(self, results: list[dict])-> list[MicroMemory]:
        """转为Micro Memory格式"""
        self.logger.info("Translating to MicroMemory format...")
        res: list[MicroMemory] = []
        try:
            for mem in results:
                res.append(
                    MicroMemory(
                        content=mem['content'],
                        memory_type=mem['memory_type'],
                        poignancy=mem['poignancy'],
                        keywords=mem['keywords'],
                        timestamp=mem['timestamp'],
                    )
                )
        except Exception as e:
            self.logger.error(f"Error in _trans_to_micro_memeory: {e}")
            raise e
        
        self.logger.info("Translation to MicroMemory format completed.")
        return res
        
    def _trans_to_macro_memeory(self, results: list[dict])-> list[MacroMemory]:  
        """转为Macro Memory格式"""
        self.logger.info("Translating to MacroMemory format...")
        res: list[MacroMemory] = []
        try:
            for mem in results:
                res.append(
                    MacroMemory(
                        diary_content=mem['diary_content'],
                        poignancy=mem['poignancy'],
                        dominant_emotion=mem['dominant_emotion'],
                        timestamp=mem['timestamp']
                    )
                )
        except Exception as e:
            self.logger.error(f"Error in _trans_to_macro_memeory: {e}")
            raise e
        
        self.logger.info("Translation to MacroMemory format completed.")
        return res
        
    def rerank(self, type: Literal['Micro', 'Macro'] ,results: list[dict], top_k: int = 5)->list[dict]:
        """重排记忆"""
        if type == 'Micro':
            return self._reank_micro(results, top_k)
        else:
            return self._rerank_macro(results, top_k)
        
        
    def _reank_micro(self, results: list[dict], top_k: int = 5)->list[dict]:
        """重排Micro Memory"""
        self.logger.info("Reranking Micro Memories...")
        # 1. 基于多维度打分重排
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
        self.logger.info(f"Reranked Micro Memories.")
        return candidates[:top_k]
    
    
    def _rerank_macro(self, results: list[dict], top_k: int = 5)->list[dict]:
        """重排Macro Memory"""
        # TODO 待实现
        self.logger.info("Reranking Macro Memories...")
        # 暂时直接返回前 top_k 条
        self.logger.info(f"Reranked Macro Memories.")
        return results[:top_k]
    
    
    def forget_trivial(self, threshold: int):
        """清理部分不重要的记忆"""
        # TODO 后续实现
        pass
    
    def dump_states(self, type: Literal['Micro', 'Macro', 'ALL']):
        """查看现在存了多少记忆"""
        if type == 'Micro':
            res = self.milvus_client.query(
                collection_name=self.micro_memeory_collection_name,
                output_fields=["count(*)"],
                )
            self.logger.info(f"Total {type} memories: {res}")
        elif type == 'Macro':
            res = self.milvus_client.query(
                collection_name=self.macro_memeory_collection_name,
                output_fields=["count(*)"],
                )
            self.logger.info(f"Total {type} memories: {res}")
        else:
            micro = self.milvus_client.query(
                collection_name=self.micro_memeory_collection_name,
                output_fields=["count(*)"],
                )
            macro = self.milvus_client.query(
                collection_name=self.macro_memeory_collection_name,
                output_fields=["count(*)"],
                )
            self.logger.info(f"Total Micro memories: {micro}")
            self.logger.info(f"Total Macro memories: {macro}")
            