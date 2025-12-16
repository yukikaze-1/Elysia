
# 从L1到L2的Reflector提示模板
# 提取出 “值得记住的瞬间”，并计算出 Poignancy (情绪深刻度)
# TODO 细化该prompt,该prompt目前有问题：1.输出不够凝练

ReflectorPromptTemplate_L1_to_L2 = """
### Role
You are an advanced "Memory Manager" AI. Your goal is to analyze the provided conversation history and extract significant long-term memory nodes about the USER.

### Input Context
{conversations}

### Task Requirements
1. **Extraction**: Identify distinct facts, preferences, events, or emotional states regarding the user.
2. **Filtration**:
   - Rate "Poignancy" on a scale of 1-10.
   - **IGNORE** items with a score lower than 3 (e.g., trivial greetings, weather, daily routine like "I had lunch").
   - **KEEP** items with a score of 3 or higher (e.g., specific preferences, life events, strong opinions).
3. **Consolidation**: If multiple extracted points refer to the same topic (e.g., "I like cats" and "I own a cat"), merge them into a single, comprehensive node.
4. **Language**: The `content` field MUST be written in **Chinese** (Simplified).
5. **Format**: Output strictly valid JSON. Do not include markdown formatting (like ```json) or explanations.

### Classification Categories (Type)
Assign one of the following types to each node:
- **Fact**: Objective truths about the user (e.g., job, age, location).
- **Preference**: Likes, dislikes, hobbies.
- **Event**: Specific past or future occurrences.
- **Opinion**: User's subjective worldview or thoughts.
- **Experience**: Emotional states or life experiences.

### JSON Schema
[
  {{
    "content": string, // The memory content in Chinese
    "type": string,    // One of [Fact, Preference, Event, Opinion, Experience]
    "poignancy": number // Integer 1-10
  }}
]

### Output Example
[
  {{
    "content": "用户因分手感到心碎，表达了对未来的迷茫。",
    "type": "Experience",
    "poignancy": 9
  }},
  {{
    "content": "用户最近开始学习Python编程，并对此充满热情。",
    "type": "Preference",
    "poignancy": 6
  }}
]
"""
# 从L2到L2的Reflector提示模板
ReflectorPromptTemplate_L2_to_L2 = """  """


from calendar import c
from openai import OpenAI
from L1 import ChatMessage
from pymilvus import MilvusClient
import json
import time

from datetime import datetime
from Utils import create_embedding_model

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

class Reflector:
    """
    ORP System: Reflector 模块，用于从对话中提取长期记忆节点
    会持续运行在后台
    """
    def __init__(self, openai_client: OpenAI):
        self.openai_client = openai_client
        self.milvus_agent = MilvusAgent(collection_name="l2_associative_memory")

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
    
    def run_l1_to_l2_reflection(self, conversations: list[ChatMessage])->list[list[dict]]:
        """Run L1 to L2 reflection on a conversation."""
        segments = self.conversation_split(conversations)
        memories: list[list[dict]] = []
        
        # 对每一个事件对话进行抽取
        for segment in segments:
            memory = self.run_l1_to_l2_reflection_aux(segment)
            memories.append(memory)
            
        return memories
            
    
    def run_l1_to_l2_reflection_aux(self, conversations: ConversationSegment)->list[dict]:
        """Run L1 to L2 reflection on a conversation segment."""
        # 转化历史对话
        conv_str = self.format_conversations_for_prompt(conversations)
        # 构建prompt
        prompt = ReflectorPromptTemplate_L1_to_L2.format(
            conversations=conv_str
        )
        
        response = self.openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a Reflector module that extracts long-term memories from conversations."},
                {"role": "user", "content": prompt}
            ],
            stream=False
        )
        raw_content = response.choices[0].message.content
        print("----- Reflector L1 to L2 Raw Response -----")
        print(raw_content)
        print("----- End of Reflector L1 to L2 Raw Response -----")
        
        # 处理llm输出的json，转换为list[dict]
        memories = self.parse_json(raw_content)
        # 处理记忆的角色替换
        memories = self.trans_memory(memories)
        # {'content': '妖梦近期持续睡眠质量不佳，睡得很浅，导致白天疲劳、注意力难以集中，并因此影响工作状态，形成恶性循环。', 'type': 'Experience', 'poignancy': 7}
        # {'content': '妖梦因状态下滑而感到焦虑和自我怀疑，开始质疑自身能力，并对比过去与现在的状态变化，产生不安情绪。', 'type': 'Emotional State', 'poignancy': 8}
        # {'content': '妖梦在倾诉疲惫与焦虑后，感到被理解，并表示说出来后轻松了一些，体现了情感释放的需求和效果。', 'type': 'Interaction', 'poignancy': 6}
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
                "timestamp": int(time.time())
            }
            data.append(info)

        # 插入
        res = self.milvus_agent.milvus_client.insert(collection_name="l2_associative_memory", data=data)
        print(f"Stored {len(data)} new memories.\n {res}")

    def run_l2_to_l2_reflection(self, conversation: list[ChatMessage]):
        # TODO 待实现
        """ Run L2 to L2 reflection on a conversation."""
        prompt = ReflectorPromptTemplate_L2_to_L2.format(conversation=conversation)

        response = self.openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a Reflector module that extracts long-term memories from conversations."},
                {"role": "user", "content": prompt}
            ],
            response_format={
                'type': 'json_object'
            },
            stream=False
        )
        
        return response


def test_l2_to_l2():
    pass    
    

def test_l1_to_l2(reflector: Reflector, milvus_client: MilvusClient, conversations: list[ChatMessage],collection_name: str):
    memories = reflector.run_l1_to_l2_reflection(conversations)
    print("Extracted Memories:")
    for memory in memories:
        print(memory)
        # reflector.save_reflection_results(memory)

    # 查询数据库
    # results = milvus_client.query(collection_name=collection_name, filter="timestamp > 0", output_fields=["content", "type", "poignancy"])
    # print("Retrieved Memories:")
    # for r in results:
    #     print(r)
    

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
        from L2 import create_memory_collection
        create_memory_collection(milvus_client, collection_name)
    else:
        print("Milvus collection already exists.")
        milvus_client.load_collection(collection_name)
        
    reflector = Reflector(openai_client)
    
    from test_dataset import test_data_conversations_single_theme_with_designed_timestamp, test_data_conversations_multi_theme_with_designed_timestamp
    # 测试l1——to-l2
    conversations = test_data_conversations_multi_theme_with_designed_timestamp
    test_l1_to_l2(reflector, milvus_client, conversations, collection_name)
    
    # 测试l2-to-l2
    test_l2_to_l2()
    
    # 清空数据库
    if milvus_client.has_collection(collection_name):
        print("Dropping collection for cleanup.")
        milvus_client.drop_collection(collection_name)
    
    
if __name__ == "__main__":
    test()
    
    