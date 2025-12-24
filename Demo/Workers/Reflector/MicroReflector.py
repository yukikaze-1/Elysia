"""
存放 Micro Reflector 相关的类和逻辑
包括 MicroMemory 的数据结构定义
"""

# =========================================
# 数据结构定义
# =========================================
class MicroMemoryLLMOut:
    """LLM输出的最基础的micro memory的格式，没有timestamp和embedding"""
    def __init__(self, content: str, subject: str,memory_type: str, poignancy: int, keywords: list[str]):
        self.content: str = content
        self.subject: str = subject
        self.memory_type: str = memory_type
        self.poignancy: int = poignancy
        self.keywords: list[str] = keywords
        
    def to_dict(self):
        return {
            "content":self.content,
            "subject":self.subject,
            "memory_type": self.memory_type,
            "poignancy": self.poignancy,
            "keywords":self.keywords
        }


class MicroMemory(MicroMemoryLLMOut):
    """Micro Memory 的格式"""
    def __init__(self, content: str, subject: str, memory_type: str, poignancy: int, keywords: list[str], timestamp: float):
        super().__init__(content=content, subject=subject, memory_type=memory_type, poignancy=poignancy, keywords=keywords)
        self.timestamp = timestamp
        
    @classmethod
    def from_micro_memory_llm_out(cls, llm_out: MicroMemoryLLMOut, timestamp: float):
        return cls(
            content=llm_out.content,
            subject=llm_out.subject,
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
    def __init__(self, content: str, subject: str, memory_type: str, poignancy: int, keywords: list[str], timestamp: float, embedding: list[float]):
        super().__init__(content, subject, memory_type, poignancy, keywords, timestamp)
        self.embedding = embedding

    @classmethod
    def from_memory(cls, memory: MicroMemory, embedding: list[float]):
        return cls(
            content=memory.content,
            subject=memory.subject,
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


from typing import TYPE_CHECKING

# 仅在类型检查时导入，运行时不会执行这行代码
if TYPE_CHECKING:
    from Demo.Layers.L2 import MemoryLayer
    
from Demo.Core.Schema import ChatMessage, ConversationSegment
from Demo.Prompt import MicroReflector_SystemPrompt, MicroReflector_UserPrompt
from openai.types.chat import ChatCompletionMessage, ChatCompletion
from Demo.Utils import parse_json
from openai import OpenAI
from datetime import datetime
from logging import Logger


class MicroReflector:
    """负责从l1 的对话中提取记忆"""
    def __init__(self, openai_client: OpenAI, milvus_agent: 'MemoryLayer', collection_name: str, logger: Logger):
        self.logger: Logger = logger
        self.openai_client: OpenAI = openai_client
        self.collection_name: str = collection_name
        self.milvus_agent: 'MemoryLayer' = milvus_agent
        self.system_prompt: str = MicroReflector_SystemPrompt
        self.user_prompt: str = MicroReflector_UserPrompt
    
    
    def run_micro_reflection(self, conversations: list[ChatMessage])->list[MicroMemory]:
        """对一大段对话进行反思，并抽取记忆、存入milvus"""
        if len(conversations) == 0:
            self.logger.warning("Warnning: No ChatMessage in SessionState!\n Do nothing.")
            return []
        
        self.logger.info("--- [Reflector] Starting Micro-Reflection ---")
        
        segments: list[ConversationSegment] = self.conversation_split(conversations)
        memories: list[MicroMemory] = []
        
        # 对每一个对话块进行抽取
        for segment in segments:
            memory = self._run_micro_reflection_aux(segment)
            memories += memory
            
        # 存储
        self.save_reflection_results(memories)
        
        return memories
    
    # ==================================================================================
    # 内部方法
    # ==================================================================================
            
    def _run_micro_reflection_aux(self, conversations: ConversationSegment)->list[MicroMemory]:
        """对一小段对话进行反思"""
        self.logger.info(f"[Reflector] Running Micro-Reflection on conversation segment from\
            {datetime.fromtimestamp(conversations.start_time)} to \
            {datetime.fromtimestamp(conversations.end_time)}, \
            containing {len(conversations.messages)} messages."
        )
        # 该对话的时间戳
        timestamp = conversations.start_time
        # 转化历史对话
        transcript: str = self.format_conversations_to_lines(conversations)
        
        # 构建prompt
        system_prompt = self.system_prompt.format(
            user_name="妖梦",
            character_name="Elysia"
        )
        user_prompt = self.user_prompt.format(
            transcript=transcript
        )
        
        self.logger.info("----------Micro Reflector(L1 to L2) Raw User Prompt ----------")
        self.logger.info(user_prompt)
        self.logger.info("----------------------------------------")
        
        # 调用LLM ，采用前缀续写方式
        messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": "[\n", "prefix": True} 
        ]
        response = self.openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )
        
        self.logger.info("--------------- Reflector L1 to L2 Raw Response ---------------")
        self.logger.info(response)
        self.logger.info("--------------- End of Reflector L1 to L2 Raw Response ---------------")
        
        # 处理llm输出的json，转换为list[dict]
        # 这里假设解析后的格式是我们规定的格式：MicroMemoryLLMOut
        # 因为是对话前缀续写，需要手动加上'{'组成完整的json格式
        raw_content = response.choices[0].message.content
        if raw_content:
                raw_content = '[' + raw_content
        memories: list[MicroMemoryLLMOut] = self.parse_micro_llm_output(raw_content)
        
        # 添加时间戳
        res: list[MicroMemory] = []
        for mem in memories:
            res.append(MicroMemory.from_micro_memory_llm_out(mem, timestamp))
        self.logger.info(f"[Reflector] Extracted {len(res)} Micro Memories from conversation segment.")
        return res


    def parse_micro_llm_output(self, llm_raw_output)-> list[MicroMemoryLLMOut]:
        """处理llm的原生回复，提取出MicroMemory"""
        
        self.logger.info("Parsing Micro LLM Output...")
        # 1. 打印原始内容的 repr()，这样能看到空格、换行符等不可见字符
        self.logger.info(f"DEBUG: Raw Output type: {type(llm_raw_output)}")
        self.logger.info(f"DEBUG: Raw Output repr: {repr(llm_raw_output)}") 
        
        # 2. 清洗数据（防止模型输出 ```json ... ``` 包裹）
        cleaned_output = llm_raw_output.strip()
        if cleaned_output.startswith("```"):
            cleaned_output = cleaned_output.replace("```json", "").replace("```", "")
            
        # 提取llm回复中的content部分，应该是一个list[dict]
        # [
        #   {
        #    "content": "他今天早上通勤很不顺利，地铁临时晚点，这让他整个人都变得有些急躁。我能感受到他被打乱节奏后的那种烦躁。",
        #    "subject": "妖梦",
        #    "memory_type": "Experience",
        #    "poignancy": 4,
        #    "keywords": ["通勤", "地铁晚点", "急躁", "烦躁"],
        #   }
        # ]
        # raw_content:str = raw_response.choices[0].message.content
        
        memories: list[dict] = parse_json(cleaned_output, self.logger)
        if not memories:
            self.logger.error("Error! Parse JSON failed.")
            self.logger.error("Raw LLM content:\n cleaned_output")
            return []
        
        # 将 dict 转换为 MicroMemoryLLMOut
        res: list[MicroMemoryLLMOut] = []
        try:
            for mem in memories:
                res.append(MicroMemoryLLMOut(
                    content=mem['content'], 
                    subject=mem['subject'],
                    memory_type=mem['memory_type'],
                    poignancy=mem['poignancy'],
                    keywords=mem['keywords'])
                )
        except Exception as e:
            self.logger.error("Error! Failed to convert llm output to MicroMemoryLLMOut. In function: parse_llm_output.")
            raise e
        self.logger.info(f"Parsed {len(res)} Micro Memories from LLM output.")
        return res
    
    
    def format_conversations_to_lines(self, conversations: ConversationSegment) -> str:
        """将历史对话转换为文本行格式"""
        lines = []
        for msg in conversations.messages:
            lines.append(f'  {msg.role}: {msg.content}')
        return "[\n" + "\n".join(lines) + "\n]"
    
    
    def conversation_split(self, conversations: list[ChatMessage], gap_seconds: float = 1800.0)->list[ConversationSegment]:
        """将对话按时间来进行切割"""
        if len(conversations) == 0:
            return []
        self.logger.info(f"Splitting {len(conversations)} messages into conversation segments. By gap_seconds={gap_seconds}") 
        self.logger.debug("Messages to split:")
        for msg in conversations:
            msg.debug(self.logger)    
        segments: list[ConversationSegment] = []
        
        # 目前采用简单粗暴的按时间间隔来分
        # TODO 后续考虑更新划分算法
        
        current: list[ChatMessage] = [conversations[0]]
        
        for prev, curr in zip(conversations, conversations[1:]):
            if curr.timestamp - prev.timestamp > gap_seconds:
                segments.append(ConversationSegment(current[0].timestamp, current[-1].timestamp, current.copy()))
                current.clear()
            current.append(curr)
            
        segments.append(ConversationSegment(current[0].timestamp, current[-1].timestamp, current.copy()))
        self.logger.info(f"Total {len(segments)} conversation segments created.")
        for s in segments:
            s.debug(self.logger)
        return segments


    def get_embedding(self, text: str) -> list[float]:
        """ Get embedding vector for a given text. """
        vector = self.milvus_agent.embedding_model.embed_documents([text])
        return vector[0] if vector and len(vector) > 0 else []
    
    
    def save_reflection_results(self, memories: list[MicroMemory]):
        """ 将抽象出来的记忆存入 milvus. """
        self.logger.info(f"[Reflector] Saving {len(memories)} Micro Memories to Milvus...")
        
        if not memories or len(memories) == 0:
            self.logger.warning("No memories to store.")
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
                "subject": mem.subject,
                "memory_type": mem.memory_type,
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
        self.logger.info(f"Stored {len(data)} new memories.\n {res}")
        return res
    
    