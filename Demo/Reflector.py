
from calendar import c
from openai import OpenAI
from L1 import ChatMessage
from pymilvus import MilvusClient
import json
import time

from datetime import datetime

class ConversationSegment:
    def __init__(self, start_time: float, end_time: float, messages: list[ChatMessage]):
        self.messages: list[ChatMessage] = messages
        self.start_time: float = start_time
        self.end_time: float = end_time
        
    def format_messages(self):
        lines = []
        for msg in self.messages:
            lines.append(f'  {msg.role}: {msg.content}: {msg.timestamp}： {datetime.fromtimestamp(msg.timestamp)}')
        return "[\n" + "\n".join(lines) + "\n]"
    
    def debug(self):
        print("Conversaton Segement:")
        print(f"During:{self.start_time} to {self.end_time}.Contains {len(self.messages)} messages")
        print(self.format_messages())
        print()


from Demo.Utils import MilvusAgent
from Demo.Prompt import ReflectorPromptTemplate_L1_to_L2

class Reflector:
    """
    ORP System: Reflector 模块，用于从对话中提取长期记忆节点
    会持续运行在后台
    """
    def __init__(self, openai_client: OpenAI):
        self.openai_client = openai_client
        self.collection_name="l2_associative_memory"
        self.milvus_agent = MilvusAgent(self.collection_name)

    def parse_json(self, raw_content)->list[dict]:
        """Parse JSON content from raw string."""
        if not raw_content:
            return [{}]
        try:
            data = json.loads(raw_content)
            return data
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return [{}]
        
    def format_conversations_for_prompt(self, conversations: ConversationSegment) -> str:
        """将历史对话转换为更高效的结构"""
        # 形如:[user: 今天一整天都感觉很累。
        # assistant: 听起来今天对你来说消耗挺大的。]
        lines = []
        for msg in conversations.messages:
            lines.append(f'  {msg.role}: {msg.content}')
        return "[\n" + "\n".join(lines) + "\n]"

    def trans_memory(self, memories: list[dict]):
        """处理reflector抽取出来的记忆，更换其表述"""
        # 例如将：户近期持续睡眠质量不佳，表现为睡得很浅，并因此导致白天疲惫、注意力难以集中。
        # 转换为: 妖梦近期持续睡眠质量不佳，表现为睡得很浅，并因此导致白天疲惫、注意力难以集中。
        def normalize_content(text: str) -> str:
            replacements = {
                "用户": "妖梦"
            }
            for k, v in replacements.items():
                text = text.replace(k, v)
            return text
        res = []
        for memory in memories:
            content = memory['content']
            memory['content'] = normalize_content(content)
            res.append(memory)
            
        return res
    
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
    
    def run_micro_reflection(self, conversations: list[ChatMessage])->list[list[dict]]:
        """Run L1 to L2 reflection on  conversations."""
        if len(conversations) == 0:
            print("Warnning: No ChatMessage in SessionState!")
            print("Do nothing.")
            return []
        
        print("--- [Reflector] Starting Micro-Reflection ---")
        
        segments = self.conversation_split(conversations)
        memories: list[list[dict]] = []
        
        # 对每一个事件对话进行抽取
        for segment in segments:
            memory = self._run_micro_reflection_aux(segment)
            memories.append(memory)
            
        # 存储
        for memory in memories:
            self.save_reflection_results(memory)
            
        return memories
            
    
    def _run_micro_reflection_aux(self, conversations: ConversationSegment)->list[dict]:
        """Run L1 to L2 reflection on a conversation segment."""
        # 该对话的时间戳
        timestamp = conversations.start_time
        # 转化历史对话
        transcript: str = self.format_conversations_for_prompt(conversations)
        
        # 构建prompt
        system_prompt = ReflectorPromptTemplate_L1_to_L2
        user_prompt = f"Here is the recent raw interaction log:\n\n{transcript}"
        
        print("----------Raw User Prompt ----------")
        print(user_prompt)
        print("----------------------------------------")
        
        response = self.openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            stream=False
        )
        raw_content = response.choices[0].message.content
        print("--------------- Reflector L1 to L2 Raw Response ---------------")
        print(raw_content)
        print("--------------- End of Reflector L1 to L2 Raw Response ---------------")
        
        # 处理llm输出的json，转换为list[dict]
        memories = self.parse_json(raw_content)
        
        # 处理记忆的角色替换
        memories = self.trans_memory(memories)
        # {'content': '我发现他今天醒来就感到异常疲惫，即使睡了七个多小时也无济于事。', 'type': 'Experience', 'poignancy': 5, 'keywords': ['疲惫', '睡眠', '醒来']}, 
        # {'content': '我了解到他最近频繁做梦，这可能是导致他白天精神不振的原因。', 'type': 'Experience', 'poignancy': 4, 'keywords': ['做梦', '精神不振', '频繁']},
        # {'content': '我注意到他正在忙于工作，项目进度很赶，时间压力不小。', 'type': 'Fact', 'poignancy': 4, 'keywords': ['工作', '项目', '时间压力']}, 
        
        # 添加时间戳
        for mem in memories:
            mem['timestamp'] = timestamp
        
        return memories

    def get_embedding(self, text: str) -> list[float]:
        """ Get embedding vector for a given text. """
        vector = self.milvus_agent.embedding_model.embed_documents([text])
        return vector[0] if vector and len(vector) > 0 else []
    
    def save_reflection_results(self, memories: list[dict]):
        """ 将抽象出来的记忆存入 milvus. """
        if not memories or len(memories) == 0:
            print("No memories to store.")
            return
        
        # 准备数据插入 Milvus
        data = []
        
        for mem in memories:
            if mem['poignancy'] < 3: continue # 过滤掉琐事

            # 生成向量
            vec = self.get_embedding(mem['content'])
            info = {
                "content": mem['content'],
                "embedding": vec,
                "type": mem['type'],
                "poignancy": mem['poignancy'],
                "keywords": mem['keywords'],
                "timestamp": int(time.time())
            }
            data.append(info)

        # 插入
        res = self.milvus_agent.milvus_client.insert(collection_name="l2_associative_memory", data=data)
        print(f"Stored {len(data)} new memories.\n {res}")
        return res

    def run_macro_reflection(self, conversation: list[ChatMessage]):
        # TODO 待实现
        pass
    

def test_l1_to_l2(reflector: Reflector, conversations: list[ChatMessage]):
    memories = reflector.run_micro_reflection(conversations)
    print("Extracted Memories:")
    for memory in memories:
        print(memory)
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
        
    
    from test_dataset import (test_data_conversations_single_theme_with_designed_timestamp, 
                              test_data_conversations_multi_theme_with_designed_timestamp,
                              conversations_01)
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
    
    