# =========================================
# Macro Memory 相关的数据结构定义
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
    
    

# =========================================
# Micro Memory 相关的数据结构定义
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
