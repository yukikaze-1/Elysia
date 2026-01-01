"""
存放 Macro Reflector 相关的类和逻辑
"""
  
    
import time
import json   
from datetime import datetime
from layers.L2.L2 import MemoryLayer
from openai import OpenAI
from workers.reflector.MicroReflector import MicroMemory
from Utils import parse_json
from config.Config import MacroReflectorConfig
from workers.reflector.MemorySchema import MacroMemoryLLMOut, MacroMemory, MacroMemoryStorage
from core.PromptManager import PromptManager
from logging import Logger

class MacroReflector:
    """负责从l2 的记忆中精炼记忆"""
    def __init__(self, openai_client: OpenAI, 
                 milvus_agent: MemoryLayer, 
                 logger: Logger,
                 config: MacroReflectorConfig,
                 prompt_manager: PromptManager):
        self.config: MacroReflectorConfig = config
        self.logger: Logger = logger
        self.openai_client: OpenAI = openai_client
        self.collection_name: str = config.milvus_collection
        self.milvus_agent: MemoryLayer = milvus_agent
        self.prompt_manager: PromptManager = prompt_manager
        
        # TODO 这个一天的记忆有待商榷
        self.gather_memory_time_interval_seconds: int = self.config.gather_memory_time_interval_seconds  # 汇集记忆的时间间隔，单位秒，默认一天
        
        self.last_macro_reflection_time: float = 0.0  # 上一次macro reflection的时间
        self.last_macro_reflection_log: list[MacroMemory] = []  # 上一次macro reflection的结果日志(Dashboard用) 
    
    # ==================================================================================
    # 状态导入导出
    # ==================================================================================   
    
    def get_status(self) -> dict:
        """获取 MacroReflector 状态"""
        # TODO 加一个计数器，计算处理了多少条记忆，生成了多少条记忆，然后保存在文件中,启动时从文件加载
        status = {
            "collection_name": self.collection_name,
            "last_macro_reflection_time": datetime.fromtimestamp(self.last_macro_reflection_time).strftime("%Y-%m-%d %H:%M:%S") if self.last_macro_reflection_time > 0 else "Never",
            "last_macro_reflection_log_count": len(self.last_macro_reflection_log),
            "last_macro_reflection_log": [mem.to_dict() for mem in self.last_macro_reflection_log]
        }
        return status
    
    
    def dump_state(self) -> dict:
        """导出当前状态为字典"""
        state = {
            "last_macro_reflection_time": self.last_macro_reflection_time,
            "last_macro_reflection_log": [mem.to_dict() for mem in self.last_macro_reflection_log]
        }
        return state
    
    
    def load_state(self, state: dict):
        """从字典加载状态"""
        if 'last_macro_reflection_time' in state:
            self.last_macro_reflection_time = state['last_macro_reflection_time']
        if 'last_macro_reflection_log' in state:
            self.last_macro_reflection_log = []
            for mem_dict in state['last_macro_reflection_log']:
                self.last_macro_reflection_log.append(MacroMemory(
                    diary_content=mem_dict['diary_content'],
                    subject=mem_dict['subject'],
                    poignancy=mem_dict['poignancy'],
                    dominant_emotion=mem_dict['dominant_emotion'],
                    keywords=mem_dict['keywords'],
                    timestamp=mem_dict['timestamp']
                ))

    # ==================================================================================
    # 核心方法
    # ==================================================================================    

    def run_macro_reflection(self) -> list[MacroMemory]:
        """主流程：协调各步骤"""
        self.logger.info("Starting Macro Reflection...")
        
        # 1. 获取数据
        micro_memories = self._gather_daily_memories()
        if not micro_memories:
            self.logger.info("No memories found. Skipping.")
            return []

        # 2. 思考 (LLM 交互的核心逻辑封装在这里)
        macro_memories: list[MacroMemory] = self._generate_macro_memories(micro_memories)
        
        # 3. 更新状态
        self._update_state(macro_memories)
        
        # 4. 存储结果
        self.save_reflection_results(macro_memories)
        
        return macro_memories
    
    # ==================================================================================
    # 内部方法实现
    # ==================================================================================

    def _generate_macro_memories(self, micro_memories: list[MicroMemory]) -> list[MacroMemory]:
        """职责：负责与 LLM 交互并解析结果"""
        # 1. 准备 Prompt
        messages: list = self._build_llm_messages(micro_memories)
        
        # 2. 调用 LLM
        raw_json: str = self._call_llm(messages)
        
        # 3. 解析并转换为对象
        timestamp = int(time.time())
        llm_outs = self.parse_macro_llm_output(raw_json)
        
        return [
            MacroMemory.from_macro_memory_llm_out(mem, timestamp)
            for mem in llm_outs
        ]

    def _build_llm_messages(self, memories: list[MicroMemory]) -> list[dict]:
        """职责：构建 Prompt"""
        # 构建 System Prompt
        system_prompt: str = self.prompt_manager.render_macro(
            "MacroReflector.j2",
            "MacroReflectorSystemPrompt",
            character_name="Elysia",
        )
        # 构建 User Prompt
        user_prompt: str = self.prompt_manager.render_macro(
            "MacroReflector.j2",
            "MacroReflectorUserPrompt",
            character_name="Elysia",
            current_date=datetime.now().strftime("%Y-%m-%d"),
            last_diary_entry=None,  # TODO 这里可以传入上一次的日记内容
            memories_list=memories
        )
        # 构建消息列表
        messsages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": "{\n", "prefix": True}
        ]
        return messsages


    def _call_llm(self, messages: list) -> str:
        """职责：纯粹的 LLM I/O"""
        response = self.openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        content = response.choices[0].message.content
        return '{' + content if content else ""


    def _update_state(self, memories: list[MacroMemory]):
        """职责：更新内部状态"""
        self.last_macro_reflection_log = memories
        self.last_macro_reflection_time = time.time()
    
    
    def _gather_daily_memories(self, time_interval: float | None = None)-> list[MicroMemory]:
        """汇集一天的记忆"""
        if time_interval is None:
            time_interval = self.gather_memory_time_interval_seconds
            
        start_time:int = int(time.time()) - int(time_interval)
    
        # 查出今天发生的高权重记忆
        results: list[MicroMemory] = self.milvus_agent.get_recent_micro_memories(
            start_time=start_time,
            min_poignancy=3  # 只取重要性 >=3 的记忆
        )
        
        self.logger.info("--------------- Gather Daily Memories ---------------")
        self.logger.info(f"Found {len(results)} memories from Milvus.")
        self.logger.info("-----------------------------------------------------")
        
        return results
    
    
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
        # 直接调用 MemoryLayer 的存储接口
        self.milvus_agent.save_macro_memory(memories)
        self.logger.info("Macro Memories stored successfully.")
        return


