"""
存放 Macro Reflector 相关的类和逻辑
包括 MacroMemory 的数据结构定义
"""

# =========================================
# 数据结构定义
# =========================================
class MacroMemoryLLMOut:
    """LLM输出的最基础的macro memory的格式，没有timestamp和embedding"""
    def __init__(self, diary_content: str, subject: str, poignancy: int, dominant_emotion: str, keywords: list):
        self.diary_content: str = diary_content              # 日记内容
        self.subject: str = subject                       # 日记描述的谁,比如"妖梦"
        self.poignancy: int = poignancy     # 情感强度
        self.dominant_emotion: str = dominant_emotion        # 情绪影响
        self.keywords: list = keywords        # 关键词
        
    def to_dict(self):
        return {
            "diary_content": self.diary_content,
            "subject": self.subject,
            "poignancy": self.poignancy,
            "dominant_emotion":self.dominant_emotion,
            "keywords":self.keywords
        }
    
    
class MacroMemory(MacroMemoryLLMOut):
    """Macro Memory 的格式"""
    def __init__(self, diary_content: str, subject: str, poignancy: int, dominant_emotion: str, keywords: list, timestamp: float):
        super().__init__(diary_content, subject, poignancy, dominant_emotion, keywords)
        self.timestamp = timestamp
        
         
    @classmethod
    def from_macro_memory_llm_out(cls, llm_out: MacroMemoryLLMOut, timestamp: float):
        return cls(
            diary_content = llm_out.diary_content,
            subject=llm_out.subject,
            poignancy=llm_out.poignancy,
            dominant_emotion=llm_out.dominant_emotion,
            keywords=llm_out.keywords,
            timestamp=timestamp
        )
        
    def to_dict(self):
        s = super().to_dict()
        s['timestamp'] = self.timestamp
        return s


class MacroMemoryStorage(MacroMemory):
    """Macro Memory 的milvus存储格式"""
    def __init__(self, diary_content: str, subject: str, poignancy: int, dominant_emotion: str, keywords: list, timestamp: float, embedding: list[float]):
        super().__init__(diary_content, subject, poignancy, dominant_emotion, keywords, timestamp=timestamp)
        self.embedding = embedding
    
    @classmethod
    def from_macro_memory(cls, memory: MacroMemory, embedding: list[float]):
        return cls(
            diary_content = memory.diary_content,
            subject=memory.subject,
            poignancy=memory.poignancy,
            dominant_emotion=memory.dominant_emotion,
            keywords=memory.keywords,
            timestamp=memory.timestamp,
            embedding=embedding
        )
    
    def to_dict(self):
        s = super().to_dict()
        s['embedding']=self.embedding
        return s
  
    
import time
import json   
from datetime import datetime
from Layers.L2.L2 import MemoryLayer
from openai import OpenAI
from Prompt import MacroReflector_SystemPrompt, MacroReflector_UserPrompt
from Workers.Reflector.MicroReflector import MicroMemory
from Utils import parse_json

from logging import Logger

class MacroReflector:
    """负责从l2 的记忆中精炼记忆"""
    def __init__(self, openai_client: OpenAI, 
                 milvus_agent: MemoryLayer, 
                 collection_name: str, 
                 logger: Logger):
        self.logger: Logger = logger
        self.openai_client: OpenAI = openai_client
        self.collection_name: str = collection_name
        self.milvus_agent: MemoryLayer = milvus_agent
        self.system_prompt: str = MacroReflector_SystemPrompt
        self.user_prompt: str = MacroReflector_UserPrompt
        
        # TODO 这个一天的记忆有待商榷
        self.gather_memory_time_interval_seconds: float = 86400.0  # 汇集记忆的时间间隔，单位秒，默认一天
        
        self.last_macro_reflection_time: float = 0.0  # 上一次macro reflection的时间
        self.last_macro_reflection_log: list[MacroMemory] = []  # 上一次macro reflection的结果日志(Dashboard用) 
        
    
    def get_status(self) -> dict:
        """获取 MacroReflector 状态"""
        # TODO 加一个计数器，计算处理了多少条记忆，生成了多少条记忆，然后保存在文件中,启动时从文件加载
        status = {
            "collection_name": self.collection_name,
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "last_macro_reflection_time": datetime.fromtimestamp(self.last_macro_reflection_time).strftime("%Y-%m-%d %H:%M:%S") if self.last_macro_reflection_time > 0 else "Never",
            "last_macro_reflection_log_count": len(self.last_macro_reflection_log),
            "last_macro_reflection_log": [mem.to_dict() for mem in self.last_macro_reflection_log]
        }
        return status
        
        
    def gather_daily_memories(self, time_interval: float | None = None)-> list[MicroMemory]:
        """汇集一天的记忆"""
        if time_interval is None:
            time_interval = self.gather_memory_time_interval_seconds
        start_time = int(time.time()) - time_interval
    
        # Milvus 表达式查询 (Hybrid Search)
        # 查出今天发生的高权重记忆
        expr = f"timestamp > {start_time} AND poignancy >= 3"
        results: list = self.milvus_agent.query(
            mem_type='Micro', filter=expr, 
            output_fields=["content", "subject", "memory_type", "poignancy", "timestamp", "keywords"]
        )
        
        self.logger.info("--------------- Gather Daily Memories ---------------")
        self.logger.info(f"Query Expression: {expr}")
        self.logger.info(f"Found {len(results)} memories from Milvus.")
        self.logger.info("-----------------------------------------------------")
        
        # 将查询到的结果转为标准的MicroMemory格式返回
        micro_memories: list[MicroMemory] = []
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


    def run_macro_reflection(self):
        """对一天的记忆进行反思"""
        # TODO 时间点待调整
        timestamp = int(time.time())
        
        micro_memories: list[MicroMemory] = self.gather_daily_memories()
        if not micro_memories or len(micro_memories) == 0:
            self.logger.info("No micro memories found for macro reflection. Exiting.")
            return []
        
        # 准备prompt
        system_prompt = self.system_prompt
        user_prompt = self.user_prompt.format(
            character_name="Elysia",
            memories_list=self.format_micro_memories_to_lines(micro_memories)
        )
        
        self.logger.info("--------------- Reflector L2 to L2 User Prompt ---------------")
        self.logger.info("User Prompt:")
        self.logger.info(user_prompt)
        self.logger.info("---------------------------------------------------------")
        
        # 调用llm进行宏观反思
        # 采用前缀续写
        messgaes = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": "{\n", "prefix": True} # 让模型续写
        ]
        response = self.openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=messgaes,
            stream=False
        )
        
        self.logger.info("--------------- Reflector L2 to L2 Raw Response ---------------")
        self.logger.info(response)
        self.logger.info("--------------- End of Reflector L2 to L2 Raw Response ---------------")

        # 解析llm输出
        raw_content = response.choices[0].message.content
        if raw_content:
                raw_content = '{' + raw_content
        macro_memories_llm_out: list[MacroMemoryLLMOut] = self.parse_macro_llm_output(raw_content)
        
        # 添加时间戳
        macro_memories: list[MacroMemory] = []
        for mem in macro_memories_llm_out:
            macro_memories.append(MacroMemory.from_macro_memory_llm_out(mem, timestamp))
            
        # 记录日志
        self.last_macro_reflection_log = macro_memories
        self.last_macro_reflection_time = time.time()
            
        # 将结果存入数据库milvus
        self.save_reflection_results(macro_memories)
        return macro_memories
    
    
    def format_micro_memories_to_lines(self, memories: list[MicroMemory])-> str:
        """将micro memories格式化为文本行"""
        lines = []
        for mem in memories:
            lines.append(f"- [{datetime.fromtimestamp(mem.timestamp).strftime("%Y-%m-%d %H:%M:%S")}] (Poignancy: {mem.poignancy}) {mem.content}\n")
        return "[\n" + "\n".join(lines) + "\n]"
    
    
    def get_embedding(self, text: str) -> list[float]:
        """ Get embedding vector for a given text. """
        vector = self.milvus_agent.embedding_model.embed_documents([text])
        return vector[0] if vector and len(vector) > 0 else []
        
        
    def parse_macro_llm_output(self, llm_raw_output)-> list[MacroMemoryLLMOut]:
        """处理llm的原生回复，提取出MacroMemoryLLMOut列表"""
        # 提取llm回复中的content部分，应该是一个dict
        #   {
        #    "diary_content": "今天过得很开心，他今天带我出去玩了一整天...",
        #    "poignancy": 75,
        #    "dominant_emotion": "复杂, 喜悦",
        #    "keywords": ["外出", "笑声", "陪伴"]
        #   }
        
        self.logger.info("Parsing Macro LLM Output...")
        
        # 1. 打印原始内容的 repr()，这样能看到空格、换行符等不可见字符
        self.logger.info(f"DEBUG: Raw Output type: {type(llm_raw_output)}")
        self.logger.info(f"DEBUG: Raw Output repr: {repr(llm_raw_output)}") 
        
        # 2. 清洗数据（防止模型输出 ```json ... ``` 包裹）
        cleaned_output = llm_raw_output.strip()
        if cleaned_output.startswith("```"):
            cleaned_output = cleaned_output.replace("```json", "").replace("```", "")
            
        memories: list[dict] = parse_json(cleaned_output, self.logger)
        if not memories or len(memories) == 0:
            print("Error! Parse JSON failed.")
            print("Raw LLM content:")
            print(cleaned_output)
            return []
        
        # 修复：如果解析出来是字典（单个记忆），则包装成列表
        if isinstance(memories, dict):
            memories = [memories]
            self.logger.info(f"Parsed single memory dict, wrapped into list.")
            
        res: list[MacroMemoryLLMOut] = []
        
        try:
            for mem in memories:
                res.append(MacroMemoryLLMOut(
                    diary_content=mem['diary_content'],
                    subject="妖梦",  # TODO 这里先写死，后续可以改成参数传入
                    poignancy=mem['poignancy'],
                    dominant_emotion=mem['dominant_emotion'],
                    keywords=mem['keywords']
                ))
        except Exception as e:
            self.logger.error("Error! Failed to convert llm output to MacroMemoryLLMOut. In function: parse_llm_output.")
            raise e
        self.logger.info(f"Parsed {len(res)} Macro Memories from LLM output.")
        
        return res 
    
    
    def save_reflection_results(self, memories: list[MacroMemory]):
        """ 将抽象出来的Macro记忆存入 milvus. """
        if not memories or len(memories) == 0:
            self.logger.info("No memories to store.")
            return
        self.logger.info(f"Storing {len(memories)} Macro Memories to Milvus...")
        # 准备数据插入 Milvus
        data = []
        
        for mem in memories:
            # 生成向量
            vec = self.get_embedding(mem.diary_content)
            info = {
                "diary_content": mem.diary_content,
                "embedding": vec,
                "subject": mem.subject,
                "dominant_emotion": mem.dominant_emotion,
                "poignancy": mem.poignancy,
                "keywords": mem.keywords,
                "timestamp": int(mem.timestamp)
            }
            data.append(info)

        # 插入
        res = self.milvus_agent.milvus_client.insert(
            collection_name=self.collection_name, 
            data=data
        )
        self.logger.info(f"Stored {len(data)} new memories.\n")
        self.logger.debug(f"Insert result details: {res}")
        return res    
    
    