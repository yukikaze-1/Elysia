

class MacroMemoryLLMOut:
    """LLM输出的最基础的macro memory的格式，没有timestamp和embedding"""
    def __init__(self, diary_content: str, relationship_score: int, dominant_emotion: str):
        self.diary_content = diary_content
        self.relationship_score =relationship_score
        self.dominant_emotion = dominant_emotion
        
    def to_dict(self):
        return {
            "diary_content": self.diary_content,
            "relationship_score": self.relationship_score,
            "dominant_emotion":self.dominant_emotion
        }
    
    
class MacroMemory(MacroMemoryLLMOut):
    """Macro Memory 的格式"""
    def __init__(self, diary_content: str, relationship_score: int, dominant_emotion: str, timestamp: float):
        super().__init__(diary_content, relationship_score, dominant_emotion)
        self.timestamp = timestamp
        
    @classmethod
    def from_macro_memory_llm_out(cls, llm_out: MacroMemoryLLMOut, timestamp: float):
        return cls(
            diary_content = llm_out.diary_content,
            relationship_score=llm_out.relationship_score,
            dominant_emotion=llm_out.dominant_emotion,
            timestamp=timestamp
        )
        
    def to_dict(self):
        s = super().to_dict()
        s['timestamp'] = self.timestamp
        return s


class MacroMemoryStorage(MacroMemory):
    """Macro Memory 的milvus存储格式"""
    def __init__(self, diary_content: str, relationship_score: int, dominant_emotion: str, timestamp: float, embedding: list[float]):
        super().__init__(diary_content, relationship_score, dominant_emotion, timestamp=timestamp)
        self.embedding = embedding
    
    @classmethod
    def from_macro_memory(cls, memory: MacroMemory, embedding: list[float]):
        return cls(
            diary_content = memory.diary_content,
            relationship_score=memory.relationship_score,
            dominant_emotion=memory.dominant_emotion,
            timestamp=memory.timestamp,
            embedding=embedding
        )
    
    def to_dict(self):
        s = super().to_dict()
        s['embedding']=self.embedding
        return s
  
    
import time
import json   
from Demo.Utils import MilvusAgent
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage, ChatCompletion 
from Demo.Prompt import ReflectorPromptTemplate_L2_to_L2_System_Prompt, ReflectorPromptTemplate_L2_to_L2_User_Prompt
from Demo.Session import ChatMessage

class MacroReflector:
    """负责从l2 的记忆中精炼记忆"""
    def __init__(self, openai_client: OpenAI, collection_name: str):
        self.openai_client = openai_client
        self.collection_name = collection_name
        self.milvus_agent = MilvusAgent(self.collection_name)
        self.system_prompt = ReflectorPromptTemplate_L2_to_L2_System_Prompt
        
    def gather_daily_memories(self)-> list:
        """汇集一天的记忆"""
        start_time = int(time.time()) - 86400 
    
        # Milvus 表达式查询 (Hybrid Search)
        # 查出今天发生的高权重记忆
        expr = f"timestamp > {start_time} && poignancy >= 5"
        results: list = self.milvus_agent.query(filter=expr, output_fields=["content", "type", "poignancy"])
        
        return [res['content'] for res in results]
    
        
    def run_macro_reflection(self):
        """对一天的记忆进行反思"""
        timestamp = int(time.time())
        memories = self.gather_daily_memories()
        system_prompt = self.system_prompt
        user_prompt=""
        
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
        
        print("--------------- Reflector L2 to L2 Raw Response ---------------")
        print(response)
        print()
        msg.debug()
        print("--------------- End of Reflector L2 to L2 Raw Response ---------------")
        
        memories: list[MacroMemoryLLMOut] = self.parse_macro_llm_output(response)
        
        # 添加时间戳
        res: list[MacroMemory] = []
        for mem in memories:
            res.append(MacroMemory.from_macro_memory_llm_out(mem, timestamp))
        
        return res
    
    def get_embedding(self, text: str) -> list[float]:
        """ Get embedding vector for a given text. """
        vector = self.milvus_agent.embedding_model.embed_documents([text])
        return vector[0] if vector and len(vector) > 0 else []
        
    def parse_macro_llm_output(self, raw_response: ChatCompletion)-> list[MacroMemoryLLMOut]:
        """处理llm的原生回复，提取出MicroMemory"""
        if not raw_response.choices[0].message.content:
            print("Error! LLM response contains empty content!")
            print("Raw LLM response:")
            print(raw_response)
            return []
        
        def parse_json(raw_content)->list[dict]:
            """Parse JSON content from raw string."""
            if not raw_content:
                return [{}]
            try:
                data = json.loads(raw_content)
                return data
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                return [{}]
        # 提取llm回复中的content部分，应该是一个list[dict]
        # [
        #   {
        #    "diary_content": "Today was a rollercoaster. He started off stressed...",
        #    "relationship_score": 75,
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
                    relationship_score=mem['relationship_score'],
                    dominant_emotion=mem['dominant_emotion']
                ))
        except Exception as e:
            raise Exception("Error! Failed to convert llm output to MacroMemoryLLMOut. In function: parse_llm_output.")
        return res 
    
    def save_reflection_results(self, memories: list[MacroMemory]):
        """ 将抽象出来的记忆存入 milvus. """
        # TODO 实现
        # if not memories or len(memories) == 0:
        #     print("No memories to store.")
        #     return
        
        # # 准备数据插入 Milvus
        # data = []
        
        # for mem in memories:
        #     if mem.poignancy < 3: continue # 过滤掉琐事

        #     # 生成向量
        #     vec = self.get_embedding(mem.content)
        #     info = {
        #         "content": mem.content,
        #         "embedding": vec,
        #         "memory_type": mem.memory_type,
        #         "poignancy": mem.poignancy,
        #         "keywords": mem.keywords,
        #         "timestamp": int(mem.timestamp)
        #     }
        #     data.append(info)

        # # 插入
        # res = self.milvus_agent.milvus_client.insert(collection_name="l2_associative_memory", data=data)
        # print(f"Stored {len(data)} new memories.\n {res}")
        # return res    