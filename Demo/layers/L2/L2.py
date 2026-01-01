"""
L2 记忆存储与检索模块
"""

import time
from typing import Literal, List, overload
from langchain_huggingface import HuggingFaceEmbeddings
import numpy as np
import threading
from pymilvus import MilvusClient
from dotenv import load_dotenv
import os

from Utils import create_embedding_model
from core.Schema import ChatMessage
from config.Config import L2Config
from Logger import setup_logger
from workers.reflector.MemorySchema import MicroMemory, MacroMemory



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
    
    def __init__(self, config: L2Config):
        # 防止重复初始化
        # 因为 __new__ 返回同一个实例后，Python 依然会调用 __init__
        # 所以必须判断是否已经初始化过
        if hasattr(self, "_initialized") and self._initialized:
            return
        
        self.config: L2Config = config
        self.logger = setup_logger(self.config.MemoryLayer.logger_name)
        
        load_dotenv()
        # === 1. 初始化长期记忆 (Milvus) === 
        # self.milvus_client = MilvusClient(uri=os.getenv("MILVUS_URI", ""), token=os.getenv("MILVUS_TOKEN", ""))
        self.milvus_client = MilvusClient(uri=self.config.MemoryLayer.MILVUS_URI, 
                                          token=self.config.MemoryLayer.MILVUS_TOKEN)
        self.micro_memeory_collection_name = self.config.MemoryLayer.micro_memory_collection
        self.macro_memeory_collection_name = self.config.MemoryLayer.macro_memory_collection
        
        # 检查并创建集合
        self._check_milvus_collections()
            
        # 初始化 Embedding 模型
        self.embedding_model: HuggingFaceEmbeddings = create_embedding_model(debug_info="L2 Memory Layer Embedding Model")
        self.logger.info("Initialized embedding model for MemoryLayer.")
        
        # 标记为已初始化
        self._initialized = True
        self.logger.info("MemoryLayer initialized successfully.")
        
        
    # ===========================================================================================================================
    # 核心接口 (供 Dispatcher 调用)
    # ===========================================================================================================================
    
    def retrieve_context(self, query: str) -> tuple[list[MicroMemory], list[MacroMemory]]:
        """
        [接口方法] 获取混合上下文 (长期相关记忆 + 日常总结记忆)
        参数:
            query: 用于检索相关记忆的查询文本
        返回: 
            (长期相关记忆, 日常总结记忆)
        """
        
        # 1. 获取长期记忆 (从 Milvus 检索相关经历)
        micro_memories: list[MicroMemory] = self.retrieve('Micro', query_text=query, top_k=5)
        
        # 2. 获取日常总结记忆
        macro_memories: list[MacroMemory] = self.retrieve('Macro', query_text=query, top_k=3)
        
        return micro_memories, macro_memories
    
    
    
    def close(self):
        """
        [接口方法] 关闭记忆层，释放资源
        """
        # 因为要将sessionstate的信息保存到磁盘
        # self.session._save_session()
        
    
    def get_status(self) -> dict:
        """
        [接口方法] 获取记忆层状态信息(Dashboard 用)
        返回: 状态字典
        """
        status = {
            "micro_memory_collection": self.micro_memeory_collection_name,
            "macro_memory_collection": self.macro_memeory_collection_name,
        }
        return status
    
    def get_recent_micro_memories(self, start_time: int, min_poignancy: int) -> list[MicroMemory]:
        """ [接口方法] (供 Reflector 调用) 获取最近的高重要性 Micro Memories """
        micro_memories: list[MicroMemory] = []
        expr = f"timestamp > {start_time} AND poignancy >= {min_poignancy}"
        results: list = self.milvus_client.query(
            collection_name=self.micro_memeory_collection_name,
            mem_type='Micro', 
            filter=expr, 
            output_fields=["content", "subject", "memory_type", "poignancy", "timestamp", "keywords"]
        )
        # 将查询到的结果转为标准的MicroMemory格式返回
        for res in results:
            micro_memories.append(MicroMemory(
                content=res['content'],
                subject=res['subject'],
                memory_type=res['memory_type'],
                poignancy=res['poignancy'],
                keywords=res['keywords'],
                timestamp=res['timestamp']
            ))
        return micro_memories
    
    # ===========================================================================================================================
    # 内部函数实现
    # ===========================================================================================================================
    
    def _check_milvus_collections(self):
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
            
    
    def save_micro_memory(self, memories: list[MicroMemory]):
        """
        [接口方法] (供 Reflector 调用) 将micro memory写入milvus
        """
        self.logger.info(f"Storing {len(memories)} Micro Memories...")
        data = []
        
        for mem in memories:
            # 生成向量
            vector = self.embedding_model.embed_documents([mem.content])
            # 组织数据
            info = {
                "content": mem.content,
                "embedding": vector[0],
                "subject": mem.subject,
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
                "subject":mem.subject,
                "dominant_emotion":mem.dominant_emotion,
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
            output_fields = ["content", "subject", "memory_type", "poignancy", "timestamp", "keywords"]
        else:
            self.logger.info("Retrieving Macro Memories...")
            collection_name = self.macro_memeory_collection_name
            output_fields = ["diary_content", "subject", "dominant_emotion", "poignancy", "timestamp", "keywords"]
        
        # 向量检索
        results: list[list[dict]] = self.milvus_client.search(
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
        
    
    def _trans_to_micro_memeory(self, results: list[dict]) -> list[MicroMemory]:
        """转为Micro Memory格式 (兼容扁平结构)"""
        self.logger.info("Translating to MicroMemory format...")
        res: list[MicroMemory] = []
        
        try:
            for mem in results:
                # [核心逻辑]
                # 经过 Rerank 后，数据已经是扁平的了，不需要 mem['entity']
                # 但为了健壮性，我们做一个判断：
                # 如果 mem 里有 'entity' 键，说明没经过 Rerank（或者是原始结果），就取 entity
                # 否则，mem 本身就是数据源
                source = mem.get('entity', mem)

                res.append(
                    MicroMemory(
                        content=source.get('content'),
                        memory_type=source.get('memory_type'),
                        subject=source.get('subject'),
                        poignancy=source.get('poignancy'),
                        keywords=source.get('keywords'),
                        timestamp=source.get('timestamp')
                    )
                )
        except Exception as e:
            self.logger.error(f"Error in _trans_to_micro_memeory: {e}")
            self.logger.error(f"Problematic data: {mem}") 
            raise e
        
        self.logger.info("Translation to MicroMemory format completed.")
        return res
        
        
    def _trans_to_macro_memeory(self, results: list[dict]) -> list[MacroMemory]:
        """转为Macro Memory格式 (兼容性修复版)"""
        self.logger.info("Translating to MacroMemory format...")

        res: list[MacroMemory] = []
        try:
            for mem in results:
                # 2. 智能获取数据源：
                # 如果是 Milvus 原始结果，数据在 'entity' 里；
                # 如果是 Rerank 后的结果，数据可能已经被展平在 mem 本身里
                source = mem.get('entity', mem)
                
                res.append(
                    MacroMemory(
                        # 使用 .get() 避免字段缺失导致崩溃
                        diary_content=source.get('diary_content'),
                        subject=source.get('subject'),
                        poignancy=source.get('poignancy'),
                        dominant_emotion=source.get('dominant_emotion'),
                        timestamp=source.get('timestamp'),
                        keywords=source.get('keywords') 
                    )
                )
        except Exception as e:
            self.logger.error(f"Error in _trans_to_macro_memeory: {e}")
            self.logger.error(f"Problematic data: {mem}")
            raise e
        
        self.logger.info("Translation to MacroMemory format completed.")
        return res
    
        
    def rerank(self, type: Literal['Micro', 'Macro'] ,results: list[dict], top_k: int = 5)->list[dict]:
        """重排记忆"""
        if type == 'Micro':
            return self._reank_micro(results, top_k)
        else:
            return self._rerank_macro(results, top_k)
        
        
    def _reank_micro(self, results: list[dict], top_k: int = 5) -> list[dict]:
        """重排Micro Memory (修复版：保留原始字段)"""
        self.logger.info("Reranking Micro Memories...")
        
        candidates = []
        current_time = int(time.time())
        
        for hit in results:
            # 安全获取 entity，防止部分数据异常
            raw_entity = hit.get("entity", {})
            
            # --- 评分逻辑不变 ---
            similarity = 1 / (1 + hit.get('distance', 0)) # distance usually outside entity
            
            # 使用 .get(key, default) 防止 NoneType 报错
            poignancy = raw_entity.get("poignancy", 0) or 0
            poignancy_score = poignancy / 10.0
            
            timestamp = raw_entity.get("timestamp", current_time) or current_time
            days_diff = (current_time - timestamp) / (86400)
            recency_score = np.exp(-0.1 * days_diff) 
            
            final_score = (similarity * 0.5) + (poignancy_score * 0.4) + (recency_score * 0.1)
            
            # --- [关键修改] 构建新的数据项 ---
            # 1. 复制原始 entity 数据 (content, subject, memory_type, keywords 等全都在这里)
            item = raw_entity.copy()
            
            # 2. 注入评分信息 (可选，用于调试)
            item['score'] = final_score
            item['debug_info'] = f"Sim:{similarity:.2f}, Poi:{poignancy_score:.2f}, Time:{recency_score:.2f}"
            
            # 3. 将 id 或 distance 也放进去（如果下游需要）
            item['vector_id'] = hit.get('id')
            
            candidates.append(item)
        
        # 按最终分数排序
        candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        self.logger.info(f"Reranked Micro Memories.")
        return candidates[:top_k]
    
    
    def _rerank_macro(self, results: list[dict], top_k: int = 5) -> list[dict]:
        """重排Macro Memory (实现版)"""
        self.logger.info("Reranking Macro Memories...")
        
        candidates = []
        current_time = int(time.time())
        
        for hit in results:
            # 安全获取原始数据
            raw_entity = hit.get("entity", {})
            
            # --- A. 相似度计算 ---
            # 同样假设 metric_type 是 L2，距离越小越相似
            # 加上 1e-6 防止除以 0（虽然 L2 通常 >= 0）
            distance = hit.get('distance', 100.0)
            similarity = 1 / (1 + distance)
            
            # --- B. 情绪/重要性权重 ---
            # Macro 记忆通常有较高的 Poignancy，这是检索长期记忆的关键
            poignancy = raw_entity.get("poignancy", 0) or 0
            poignancy_score = poignancy / 10.0
            
            # --- C. 时间衰减 (比 Micro 更加平缓) ---
            # Micro 关注当下，Macro 关注长期。
            # 这里设置 decay_rate 为 0.05 (Micro 是 0.1)，意味着“旧”得更慢
            timestamp = raw_entity.get("timestamp", current_time) or current_time
            days_diff = (current_time - timestamp) / 86400
            # 保护性判断，防止未来时间导致负数
            days_diff = max(0, days_diff)
            recency_score = np.exp(-0.05 * days_diff)
            
            # --- D. 综合打分 ---
            # 策略：相关性优先，其次是重要性，时间因素影响较小
            # 调整建议：Sim: 0.5, Poi: 0.35, Time: 0.15
            final_score = (similarity * 0.5) + (poignancy_score * 0.35) + (recency_score * 0.15)
            
            # --- [关键] 构建结果，必须保留原始字段 ---
            # 复制原始 entity 的所有字段 (diary_content, dominant_emotion 等)
            item = raw_entity.copy()
            
            # 注入分数和调试信息
            item['score'] = final_score
            item['debug_info'] = (f"Score:{final_score:.3f} | "
                                  f"Sim:{similarity:.2f}, Poi:{poignancy_score:.2f}, Time:{recency_score:.2f}")
            
            # 保留 vector id 以备不时之需
            item['vector_id'] = hit.get('id')
            
            candidates.append(item)
            
        # 按分数降序排列
        candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        self.logger.info(f"Reranked Macro Memories. Top score: {candidates[0]['score'] if candidates else 0:.3f}")
        return candidates[:top_k]
    
    
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
 
# ============================================================================================================================
# 辅助函数
# ============================================================================================================================           

def create_micro_memory_collection(collection_name: str, milvus_client: MilvusClient):
    """  创建用于Micro Memory 的 Milvus Collection  """
    #  TODO 如果存在先删除 (测试用，生产环境请注释)
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
    schema.add_field(field_name="subject", datatype=DataType.VARCHAR, max_length=255)
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
    # TODO 如果存在先删除 (测试用，生产环境请注释)
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
    schema.add_field(field_name="subject", datatype=DataType.VARCHAR, max_length=255)
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
  
