
from openai import OpenAI
from torch import embedding
from L1 import ChatMessage
from pymilvus import MilvusClient
import json

from datetime import datetime

class ConversationSegment:
    def __init__(self, start_time: float, end_time: float, messages: list[ChatMessage]):
        self.messages: list[ChatMessage] = messages
        self.start_time: float = start_time
        self.end_time: float = end_time
        
    def format_messages_to_line(self):
        lines = []
        for msg in self.messages:
            lines.append(f'  {msg.role}: {msg.content}: {msg.timestamp}： {datetime.fromtimestamp(msg.timestamp)}')
        return "[\n" + "\n".join(lines) + "\n]"
    
    def debug(self):
        print("Conversaton Segement:")
        print(f"During:{self.start_time} to {self.end_time}.Contains {len(self.messages)} messages")
        print(self.format_messages_to_line())
        print()


class MicroMemoryLLMOut:
    """LLM输出的最基础的micro memory的格式，没有timestamp和embedding"""
    def __init__(self, content: str, memory_type: str, poignancy: int, keywords: list[str]):
        self.content: str = content
        self.memory_type: str = memory_type
        self.poignancy: int = poignancy
        self.keywords: list[str] = keywords
        
    def to_dict(self):
        return {
            "content":self.content,
            "memory_type": self.memory_type,
            "poignancy": self.poignancy,
            "keywords":self.keywords
        }


class MicroMemory(MicroMemoryLLMOut):
    """Micro Memory 的格式"""
    def __init__(self, content: str, memory_type: str, poignancy: int, keywords: list[str], timestamp: float):
        super().__init__(content=content, memory_type=memory_type, poignancy=poignancy, keywords=keywords)
        self.timestamp = timestamp
        
    @classmethod
    def from_micro_memory_llm_out(cls, llm_out: MicroMemoryLLMOut, timestamp: float):
        return cls(
            content=llm_out.content,
            memory_type=llm_out.memory_type,
            poignancy=llm_out.poignancy,
            keywords=llm_out.keywords,
            timestamp=timestamp,
        )
        
    def to_dict(self):
        s = super().to_dict()
        s['timestamp'] = self.timestamp
        return s
        

class MicroMemoryStorage(MicroMemory):
    """Micro Memory 的milvus存储格式"""
    def __init__(self, content: str, memory_type: str, poignancy: int, keywords: list[str], timestamp: float, embedding: list[float]):
        super().__init__(content, memory_type, poignancy, keywords, timestamp)
        self.embedding = embedding

    @classmethod
    def from_memory(cls, memory: MicroMemory, embedding: list[float]):
        return cls(
            content=memory.content,
            memory_type=memory.memory_type,
            poignancy=memory.poignancy,
            keywords=memory.keywords,
            timestamp=memory.timestamp,
            embedding=embedding,
        )
        
    def to_dict(self):
        s = super().to_dict()
        s['embedding']=self.embedding
        return s
            

from Demo.Utils import MilvusAgent
from Demo.Prompt import ReflectorPromptTemplate_L1_to_L2
from openai.types.chat import ChatCompletionMessage, ChatCompletion


class MicroReflector:
    """负责从l1 的对话中提取记忆"""
    def __init__(self, openai_client: OpenAI, collection_name: str):
        self.openai_client = openai_client
        self.collection_name = collection_name
        self.milvus_agent = MilvusAgent(self.collection_name)
        self.system_prompt = ReflectorPromptTemplate_L1_to_L2
    
    def parse_micro_llm_output(self, raw_response: ChatCompletion)-> list[MicroMemoryLLMOut]:
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
        #    "content": "他今天早上通勤很不顺利，地铁临时晚点，这让他整个人都变得有些急躁。我能感受到他被打乱节奏后的那种烦躁。",
        #    "memory_type": "Experience",
        #    "poignancy": 4,
        #    "keywords": ["通勤", "地铁晚点", "急躁", "烦躁"],
        #   }
        # ]
        raw_content:str = raw_response.choices[0].message.content
        memories: list[dict] = parse_json(raw_content)
        if not memories:
            print("Error! Parse JSON failed.")
            print("Raw LLM content:")
            print(raw_content)
            return []
        res: list[MicroMemoryLLMOut] = []
        try:
            for mem in memories:
                res.append(MicroMemoryLLMOut(
                    content=mem['content'], 
                    memory_type=mem['memory_type'],
                    poignancy=mem['poignancy'],
                    keywords=mem['keywords'])
                )
        except Exception as e:
            raise Exception("Error! Failed to convert llm output to MicroMemoryLLMOut. In function: parse_llm_output.")
        return res
    
    def format_conversations_to_lines(self, conversations: ConversationSegment) -> str:
        """将历史对话转换为更高效的结构"""
        # 形如:[user: 今天一整天都感觉很累。
        # assistant: 听起来今天对你来说消耗挺大的。]
        lines = []
        for msg in conversations.messages:
            lines.append(f'  {msg.role}: {msg.content}')
        return "[\n" + "\n".join(lines) + "\n]"

    def trans_memory(self, memories: list[MicroMemoryLLMOut]):
        """处理reflector抽取出来的记忆，更换其表述"""
        # 例如将：用户近期持续睡眠质量不佳，表现为睡得很浅，并因此导致白天疲惫、注意力难以集中。
        # 转换为: 妖梦近期持续睡眠质量不佳，表现为睡得很浅，并因此导致白天疲惫、注意力难以集中。
        def normalize_content(text: str) -> str:
            replacements = {
                "用户": "妖梦"
            }
            for k, v in replacements.items():
                text = text.replace(k, v)
            return text
        for memory in memories:
            memory.content= normalize_content(memory.content)
            
        return memories
    
    def conversation_split(self, conversations: list[ChatMessage])->list[ConversationSegment]:
        """将对话按时间来进行切割"""
        if len(conversations) == 0:
            return []
             
        segments: list[ConversationSegment] = []
        gap_seconds = 1800.0
        
        # 目前采用简单粗暴的按时间间隔来分
        # TODO 后续考虑更新划分算法
        
        current: list[ChatMessage] = [conversations[0]]
        
        for prev, curr in zip(conversations, conversations[1:]):
            if curr.timestamp - prev.timestamp > gap_seconds:
                segments.append(ConversationSegment(current[0].timestamp, current[-1].timestamp, current.copy()))
                current.clear()
            current.append(curr)
            
        segments.append(ConversationSegment(current[0].timestamp, current[-1].timestamp, current.copy()))
        return segments
    
    def run_micro_reflection(self, conversations: list[ChatMessage])->list[MicroMemory]:
        """对一大段对话进行反思"""
        if len(conversations) == 0:
            print("Warnning: No ChatMessage in SessionState!")
            print("Do nothing.")
            return []
        
        print("--- [Reflector] Starting Micro-Reflection ---")
        
        segments: list[ConversationSegment] = self.conversation_split(conversations)
        memories: list[MicroMemory] = []
        
        # 对每一个对话块进行抽取
        for segment in segments:
            memory = self._run_micro_reflection_aux(segment)
            memories += memory
            
        # 存储
        self.save_reflection_results(memories)
            
        return memories
            
    def _run_micro_reflection_aux(self, conversations: ConversationSegment)->list[MicroMemory]:
        """对一小段对话进行反思"""
        # 该对话的时间戳
        timestamp = conversations.start_time
        # 转化历史对话
        transcript: str = self.format_conversations_to_lines(conversations)
        
        # 构建prompt
        system_prompt = self.system_prompt.format(
            user_name="妖梦",
            character_name="Elysia"
        )
        user_prompt = f"Here is the recent raw interaction log:\n\n{transcript}"
        
        print("----------Raw User Prompt ----------")
        print(user_prompt)
        print("----------------------------------------")
        # TODO 该chat是否需要使用前缀续写？(见L1的chat)
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
        
        print("--------------- Reflector L1 to L2 Raw Response ---------------")
        print(response)
        print()
        msg.debug()
        print("--------------- End of Reflector L1 to L2 Raw Response ---------------")
        
        # 处理llm输出的json，转换为list[dict]
        # 这里假设解析后的格式是我们规定的格式：MicroMemoryLLMOut
        memories: list[MicroMemoryLLMOut] = self.parse_micro_llm_output(response)
        
        # 处理记忆的角色替换
        memories = self.trans_memory(memories)
        # {'content': '我发现他今天醒来就感到异常疲惫，即使睡了七个多小时也无济于事。', 'memory_type': 'Experience', 'poignancy': 5, 'keywords': ['疲惫', '睡眠', '醒来']}, 
        # {'content': '我了解到他最近频繁做梦，这可能是导致他白天精神不振的原因。', 'memory_type': 'Experience', 'poignancy': 4, 'keywords': ['做梦', '精神不振', '频繁']},
        # {'content': '我注意到他正在忙于工作，项目进度很赶，时间压力不小。', 'memory_type': 'Fact', 'poignancy': 4, 'keywords': ['工作', '项目', '时间压力']}, 
        
        # 添加时间戳
        res: list[MicroMemory] = []
        for mem in memories:
            res.append(MicroMemory.from_micro_memory_llm_out(mem, timestamp))
        
        return res

    def get_embedding(self, text: str) -> list[float]:
        """ Get embedding vector for a given text. """
        vector = self.milvus_agent.embedding_model.embed_documents([text])
        return vector[0] if vector and len(vector) > 0 else []
    
    def save_reflection_results(self, memories: list[MicroMemory]):
        """ 将抽象出来的记忆存入 milvus. """
        if not memories or len(memories) == 0:
            print("No memories to store.")
            return
        
        # 准备数据插入 Milvus
        data = []
        
        for mem in memories:
            if mem.poignancy < 3: continue # 过滤掉琐事

            # 生成向量
            vec = self.get_embedding(mem.content)
            info = {
                "content": mem.content,
                "embedding": vec,
                "memory_type": mem.memory_type,
                "poignancy": mem.poignancy,
                "keywords": mem.keywords,
                "timestamp": int(mem.timestamp)
            }
            data.append(info)

        # 插入
        res = self.milvus_agent.milvus_client.insert(collection_name="l2_associative_memory", data=data)
        print(f"Stored {len(data)} new memories.\n {res}")
        return res
    
    

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
from Demo.Prompt import ReflectorPromptTemplate_L2_to_L2

class MacroReflector:
    """负责从l2 的记忆中精炼记忆"""
    def __init__(self, openai_client: OpenAI, collection_name: str):
        self.openai_client = openai_client
        self.collection_name = collection_name
        self.milvus_agent = MilvusAgent(self.collection_name)
        self.system_prompt = ReflectorPromptTemplate_L2_to_L2 
        
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

class Reflector:
    """
    ORP System: Reflector 模块，用于从对话中提取长期记忆节点
    会持续运行在后台
    """
    def __init__(self, openai_client: OpenAI, collection_name: str = "l2_associative_memory"):
        self.openai_client = openai_client
        self.collection_name= collection_name
        self.milvus_agent = MilvusAgent(self.collection_name)
        
        self.micro_reflector = MicroReflector(self.openai_client, self.collection_name)
        self.macro_reflector = MacroReflector(self.openai_client, self.collection_name)

    
    

def test_l1_to_l2(reflector: Reflector, conversations: list[ChatMessage]):
    memories: list[MicroMemory] = reflector.micro_reflector.run_micro_reflection(conversations)
    print("Extracted Memories:")
    for memory in memories:
        print(memory.to_dict())
    print("---------------------")
    return memories


def test():
    # 准备数据
    from dotenv import load_dotenv
    import os
    load_dotenv()
    milvus_client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
    openai_client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com"))
    
    collection_name = "l2_associative_memory"
    # 清空数据库
    if milvus_client.has_collection(collection_name):
        print("Dropping collection for cleanup.")
        milvus_client.drop_collection(collection_name)
        
    if not milvus_client.has_collection(collection_name):
        print("Creating Milvus collection for L2 memories...")
        from Demo.Utils import create_memory_collection
        create_memory_collection(collection_name, milvus_client)
    else:
        print("Milvus collection already exists.")
        milvus_client.load_collection(collection_name)
        
    reflector = Reflector(openai_client)
        
    
    from test_dataset import (conversations_01)
    # 测试l1——to-l2
    conversations = conversations_01
    res = test_l1_to_l2(reflector, conversations)
        
    
    # 清空数据库
    # if milvus_client.has_collection(collection_name):
    #     print("Dropping collection for cleanup.")
    #     milvus_client.drop_collection(collection_name)
    

def inject_milvus_test_data():
      return test()
        
    
    
if __name__ == "__main__":
    inject_milvus_test_data()
    
    