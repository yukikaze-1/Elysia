"""
存放 Micro Reflector 相关的类和逻辑
"""

from layers.L2.L2 import MemoryLayer    
from core.Schema import ChatMessage, ConversationSegment
from openai.types.chat import ChatCompletionMessage, ChatCompletion
from Utils import parse_json
from openai import OpenAI
from datetime import datetime
from logging import Logger
import time
from config.Config import MicroReflectorConfig
from workers.Reflector.MemorySchema import MicroMemory, MicroMemoryLLMOut, MicroMemoryStorage
from core.PromptManager import PromptManager


class MicroReflector:
    """负责从l1 的对话中提取记忆"""
    def __init__(self, openai_client: OpenAI, 
                 milvus_agent: MemoryLayer, 
                 logger: Logger,
                 config: MicroReflectorConfig,
                 prompt_manager: PromptManager):
        self.config: MicroReflectorConfig = config
        self.logger: Logger = logger
        self.openai_client: OpenAI = openai_client
        self.collection_name: str = self.config.milvus_collection
        self.milvus_agent: MemoryLayer = milvus_agent
        self.prompt_manager: PromptManager = prompt_manager
        
        # TODO 这个参数简单粗暴，后续考虑升级
        self.conversation_split_gap_seconds: float = self.config.conversation_split_gap_seconds  # 对话切割的时间间隔，单位秒，默认30分钟
        
        # TODO 这些参数要存入json
        self.last_micro_reflection_time: float = 0.0  # 上一次micro reflection的时间
        self.last_micro_reflection_log: list[MicroMemory] = []  # 上一次micro reflection的结果日志(Dashboard用)
        
    
    # ==================================================================================
    # 状态导入导出
    # ==================================================================================
    
    def get_status(self) -> dict:
        """获取当前 MicroReflector 状态的摘要信息"""
        # TODO 加一个计数器，计算处理了多少条记忆，生成了多少条记忆，然后保存在文件中,启动时从文件加载
        status = {
            "collection_name": self.collection_name,
            "last_micro_reflection_time": datetime.fromtimestamp(self.last_micro_reflection_time).strftime("%Y-%m-%d %H:%M:%S") if self.last_micro_reflection_time > 0 else "Never",
            "last_micro_reflection_log_count": len(self.last_micro_reflection_log),
            "last_micro_reflection_log": [mem.to_dict() for mem in self.last_micro_reflection_log]
        }
        return status
    
    
    def dump_state(self) -> dict:
        """导出当前状态为字典"""
        state = {
            "last_micro_reflection_time": self.last_micro_reflection_time,
            "last_micro_reflection_log": [mem.to_dict() for mem in self.last_micro_reflection_log]
        }
        return state
    
    
    def load_state(self, state: dict):
        """从字典加载状态"""
        self.last_micro_reflection_time = state.get("last_micro_reflection_time", 0.0)
        log_list = state.get("last_micro_reflection_log", [])
        self.last_micro_reflection_log = []
        for mem_dict in log_list:
            self.last_micro_reflection_log.append(
                MicroMemory(
                    content=mem_dict['content'],
                    subject=mem_dict['subject'],
                    memory_type=mem_dict['memory_type'],
                    poignancy=mem_dict['poignancy'],
                    keywords=mem_dict['keywords'],
                    timestamp=mem_dict['timestamp']
                )
            )

    # ==================================================================================
    # 核心方法
    # ==================================================================================
    
    def run_micro_reflection(self, conversations: list[ChatMessage])->list[MicroMemory]:
        """对一大段对话进行反思，并抽取记忆、存入milvus"""
        if len(conversations) == 0:
            self.logger.warning("Warnning: No ChatMessage in SessionState!\n Do nothing.")
            return []
        
        self.logger.info("--- [Reflector] Starting Micro-Reflection ---")
        
        # 1. 进行对话切割
        segments: list[ConversationSegment] = self.conversation_split(conversations)
        memories: list[MicroMemory] = []
        
        # 2. 对每一个对话块进行抽取
        for segment in segments:
            memory = self._run_micro_reflection_aux(segment)
            memories += memory
            
        # 4. 记录日志
        self.last_micro_reflection_log = memories
        self.last_micro_reflection_time = time.time()
        
        # 5. 存储
        self.save_reflection_results(memories)
        
        return memories
    
    # ==================================================================================
    # 内部方法
    # ==================================================================================
            
    def _run_micro_reflection_aux(self, segment: ConversationSegment) -> list[MicroMemory]:
        """主流程：协调各步骤"""
        # 1. 准备输入
        messages = self._build_llm_messages(segment)
        
        # 2. 调用 LLM (只负责拿回字符串)
        raw_response_content: str = self._call_llm(messages)
        
        # 3. 解析与转换
        res: list[MicroMemory] = self._parse_and_transform(raw_response_content, segment.start_time)
        
        return res


    def _build_llm_messages(self, segment: ConversationSegment) -> list[dict]:
        """职责：构建 Prompt"""
        recent_conversations: list[ChatMessage] = segment.messages
        
        system_prompt = self.prompt_manager.render_macro(
            "MicroReflector.j2",
            "MicroReflectorSystemPrompt",
            character_name="Elysia",
            user_name="妖梦"
        )
        
        user_prompt = self.prompt_manager.render_macro(
            "MicroReflector.j2",
            "MicroReflectorUserPrompt",
            recent_conversations=recent_conversations
        )
        # 组装消息列表,采用前缀续写方式
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": "[\n", "prefix": True}
        ]


    def _call_llm(self, messages: list) -> str:
        """职责：纯粹的 LLM I/O"""
        response = self.openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )
        content = response.choices[0].message.content
        # 处理前缀续写的补全逻辑属于 LLM 交互的一部分
        res = '[' + content if content else ""
        return res


    def _parse_and_transform(self, raw_json: str, timestamp: float) -> list[MicroMemory]:
        """职责：数据清洗与对象转换"""
        # 解析 LLM 输出
        llm_outs = self.parse_micro_llm_output(raw_json)
        
        # 转换为 MicroMemory 对象
        res = [
            MicroMemory.from_micro_memory_llm_out(mem, timestamp) 
            for mem in llm_outs
        ]
        return res

    def parse_micro_llm_output(self, llm_raw_output)-> list[MicroMemoryLLMOut]:
        """处理llm的原生回复，提取出MicroMemory"""
        
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
        
        self.logger.info("Parsing Micro LLM Output...")
        
        # 1. 打印原始内容的 repr()，这样能看到空格、换行符等不可见字符
        self.logger.info(f"DEBUG: Raw Output type: {type(llm_raw_output)}")
        self.logger.info(f"DEBUG: Raw Output repr: {repr(llm_raw_output)}") 
        
        # 2. 清洗数据（防止模型输出 ```json ... ``` 包裹）
        cleaned_output = llm_raw_output.strip()
        if cleaned_output.startswith("```"):
            cleaned_output = cleaned_output.replace("```json", "").replace("```", "")
            
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
    
    
    def conversation_split(self, conversations: list[ChatMessage], gap_seconds: float | None = None)->list[ConversationSegment]:
        """将对话按时间来进行切割"""
        if len(conversations) == 0:
            return []
        
        if gap_seconds is None:
            gap_seconds = self.conversation_split_gap_seconds
            
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
        if not memories or len(memories) == 0:
            self.logger.warning("No memories to store.")
            return
        self.logger.info(f"[Reflector] Saving {len(memories)} Micro Memories to Milvus...")
        
        # 直接调用 MemoryLayer 的存储接口
        self.milvus_agent.save_micro_memory(memories)
        self.logger.info(f"[Reflector] Successfully stored {len(memories)} Micro Memories to Milvus.")

