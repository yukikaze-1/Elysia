"""
存放 Macro Reflector 相关的类和逻辑
包括 MacroMemory 的数据结构定义
"""

# =========================================
# 数据结构定义
# =========================================
class MacroMemoryLLMOut:
    """LLM输出的最基础的macro memory的格式，没有timestamp和embedding"""
    def __init__(self, diary_content: str, poignancy: int, dominant_emotion: str):
        self.diary_content: str = diary_content              # 日记内容
        self.poignancy: int = poignancy     # 分数
        self.dominant_emotion: str = dominant_emotion        # 情绪影响
        self.keywords: list = []        # 关键词
        
    def to_dict(self):
        return {
            "diary_content": self.diary_content,
            "poignancy": self.poignancy,
            "dominant_emotion":self.dominant_emotion,
            "keywords":self.keywords
        }
    
    
class MacroMemory(MacroMemoryLLMOut):
    """Macro Memory 的格式"""
    def __init__(self, diary_content: str, poignancy: int, dominant_emotion: str, timestamp: float):
        super().__init__(diary_content, poignancy, dominant_emotion)
        self.timestamp = timestamp
        
         
    @classmethod
    def from_macro_memory_llm_out(cls, llm_out: MacroMemoryLLMOut, timestamp: float):
        return cls(
            diary_content = llm_out.diary_content,
            poignancy=llm_out.poignancy,
            dominant_emotion=llm_out.dominant_emotion,
            timestamp=timestamp
        )
        
    def to_dict(self):
        s = super().to_dict()
        s['timestamp'] = self.timestamp
        return s


class MacroMemoryStorage(MacroMemory):
    """Macro Memory 的milvus存储格式"""
    def __init__(self, diary_content: str, poignancy: int, dominant_emotion: str, timestamp: float, embedding: list[float]):
        super().__init__(diary_content, poignancy, dominant_emotion, timestamp=timestamp)
        self.embedding = embedding
    
    @classmethod
    def from_macro_memory(cls, memory: MacroMemory, embedding: list[float]):
        return cls(
            diary_content = memory.diary_content,
            poignancy=memory.poignancy,
            dominant_emotion=memory.dominant_emotion,
            timestamp=memory.timestamp,
            embedding=embedding
        )
    
    def to_dict(self):
        s = super().to_dict()
        s['embedding']=self.embedding
        return s
  
    
import json   
from datetime import datetime
from Demo.Layers.L2 import MemoryLayer
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage, ChatCompletion 
from Demo.Prompt import MacroReflector_SystemPrompt, MacroReflector_UserPrompt
from Demo.Layers.Session import ChatMessage
from Demo.Workers.Reflector.MicroReflector import MicroMemory

from logging import Logger

class MacroReflector:
    """负责从l2 的记忆中精炼记忆"""
    def __init__(self, openai_client: OpenAI, milvus_agent: MemoryLayer, collection_name: str, logger: Logger):
        self.logger: Logger = logger
        self.openai_client: OpenAI = openai_client
        self.collection_name: str = collection_name
        self.milvus_agent: MemoryLayer = milvus_agent
        self.system_prompt: str = MacroReflector_SystemPrompt
        self.user_prompt: str = MacroReflector_UserPrompt
        
        
    def gather_daily_memories(self)-> list[MicroMemory]:
        """汇集一天的记忆"""
        # TODO 这个一天的记忆有待商榷
        # start_time = int(time.time()) - 86400 
        start_time: int = 1766011204  # 2025-12-18 6:40:4 ---- 2025-12-19 7:40:1
    
        # Milvus 表达式查询 (Hybrid Search)
        # 查出今天发生的高权重记忆
        expr = f"timestamp > {start_time} AND poignancy >= 3"
        results: list = self.milvus_agent.query(mem_type='Macro', filter=expr, 
                                                output_fields=["content", "memory_type", "poignancy", "timestamp", "keywords"])
        
        self.logger.info("--------------- Gather Daily Memories ---------------")
        self.logger.info(f"Query Expression: {expr}")
        self.logger.info(f"Found {len(results)} memories from Milvus.")
        for hit in results:
            self.logger.info(hit)
        self.logger.info("-----------------------------------------------------")
        
        # 将查询到的结果转为标准的MicroMemory格式返回
        micro_memories: list[MicroMemory] = []
        for res in results:
            micro_memories.append(MicroMemory(
                content=res['content'],
                memory_type=res['memory_type'],
                poignancy=res['poignancy'],
                keywords=res['keywords'],
                timestamp=res['timestamp']
            ))
        return micro_memories


    def run_macro_reflection(self):
        """对一天的记忆进行反思"""
        # timestamp = int(time.time())
        # TODO 测试用，待修改
        
        timestamp = 1766101201  # 2025-12-19 7:40:1
        
        micro_memories: list[MicroMemory] = self.gather_daily_memories()
        system_prompt = self.system_prompt
        user_prompt = self.user_prompt.format(
            character_name="Elysia",
            memories_list=self.format_micro_memories_to_lines(micro_memories)
        )
        
        self.logger.info("--------------- Reflector L2 to L2 User Prompt ---------------")
        self.logger.info("User Prompt:")
        self.logger.info(user_prompt)
        self.logger.info("---------------------------------------------------------")
        
        response = self.openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            stream=False
        )
        raw_message: ChatCompletionMessage = response.choices[0].message
        msg = ChatMessage.from_ChatCompletionMessage(raw_message, response.created)
        
        self.logger.info("--------------- Reflector L2 to L2 Raw Response ---------------")
        self.logger.info(response)
        self.logger.info("")
        msg.debug(self.logger)
        self.logger.info("--------------- End of Reflector L2 to L2 Raw Response ---------------")
        
        macro_memories_llm_out: list[MacroMemoryLLMOut] = self.parse_macro_llm_output(response)
        
        # 添加时间戳
        macro_memories: list[MacroMemory] = []
        for mem in macro_memories_llm_out:
            macro_memories.append(MacroMemory.from_macro_memory_llm_out(mem, timestamp))
            
        # 将结果存入数据库milvus
        self.save_reflection_results(macro_memories)
        
        return macro_memories
    
    
    def format_micro_memories_to_lines(self, memories: list[MicroMemory])-> str:
        """将micro memories格式化为文本行"""
        lines = []
        for mem in memories:
            lines.append(f"- [{datetime.fromtimestamp(mem.timestamp).isoformat()}] (Poignancy: {mem.poignancy}) {mem.content}\n")
        return "[\n" + "\n".join(lines) + "\n]"
    
    
    def get_embedding(self, text: str) -> list[float]:
        """ Get embedding vector for a given text. """
        vector = self.milvus_agent.embedding_model.embed_documents([text])
        return vector[0] if vector and len(vector) > 0 else []
        
        
    def parse_macro_llm_output(self, raw_response: ChatCompletion)-> list[MacroMemoryLLMOut]:
        """处理llm的原生回复，提取出MicroMemory"""
        self.logger.info("Parsing Macro LLM Output...")
        if not raw_response.choices[0].message.content:
            self.logger.error("Error! LLM response contains empty content!")
            self.logger.error("Raw LLM response:")
            self.logger.error(raw_response)
            return []
        
        def parse_json(raw_content)->list[dict]:
            """Parse JSON content from raw string."""
            if not raw_content:
                return [{}]
            try:
                data = json.loads(raw_content)
                # 如果解析出来的是字典，把它包装成列表
                if isinstance(data, dict):
                    return [data]
                return data
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                return [{}]
            
        # 提取llm回复中的content部分，应该是一个list[dict]
        # [
        #   {
        #    "diary_content": "Today was a rollercoaster. He started off stressed...",
        #    "poignancy": 75,
        #    "dominant_emotion": "Bittersweet"
        #   }
        # ]
        raw_content:str = raw_response.choices[0].message.content
        memories: list[dict] = parse_json(raw_content)
        if not memories:
            print("Error! Parse JSON failed.")
            print("Raw LLM content:")
            print(raw_content)
            return []
        res: list[MacroMemoryLLMOut] = []
        try:
            for mem in memories:
                res.append(MacroMemoryLLMOut(
                    diary_content=mem['diary_content'],
                    poignancy=mem['poignancy'],
                    dominant_emotion=mem['dominant_emotion']
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
                "content": mem.diary_content,
                "embedding": vec,
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