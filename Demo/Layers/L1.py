import json
import os

from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
from Prompt import (SystemPromptTemplate, 
                         l2_memory_block_template, 
                         l1_decide_to_act_template,
                         current_state_template)
from Layers.L0.Sensor import EnvironmentInformation
from Layers.L0.Amygdala import AmygdalaOutput 
from Workers.Reflector.MacroReflector import MacroMemory
from Workers.Reflector.MicroReflector import MicroMemory
from Core.Schema import ChatMessage, UserMessage, DEFAULT_ERROR_INNER_THOUGHT, DEFAULT_ERROR_PUBLIC_REPLY, DEFAULT_ERROR_MOOD
from Logger import setup_logger


class NormalResponse:
    """正常对话生成模块收到的llm回复格式"""
    def __init__(self, inner_thought: str, public_reply: str, mood: str):
        self.inner_thought = inner_thought
        self.public_reply = public_reply
        self.mood = mood
        
    def to_dict(self) -> dict:
        """将 NormalResponse 转换为字典格式"""
        return {
            "inner_thought": self.inner_thought,
            "public_reply": self.public_reply,
            "mood": self.mood
        }
        

class ActiveResponse:
    """主动开口模块收到的llm回复格式"""
    def __init__(self, should_speak: bool, inner_voice: str, mood: str, public_reply: str):
        self.should_speak = should_speak
        self.inner_voice = inner_voice
        self.public_reply = public_reply
        self.mood = mood
        
    def to_dict(self) -> dict:
        """将 ActiveResponse 转换为字典格式"""
        return {
            "should_speak": self.should_speak,
            "inner_voice": self.inner_voice,
            "public_reply": self.public_reply,
            "mood": self.mood
        }
        

class BrainLayer:
    """
    L1 大脑层: 纯粹的认知核心。
    不再持有 MemoryLayer 实例，不再主动检索数据库。
    只负责接收上下文(Context)，进行推理(Inference)，并返回结果(Result)。
    """
    def __init__(self):
        load_dotenv()
        self.logger = setup_logger("L1_BrainLayer")
        self.client: OpenAI = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=os.getenv("DEEPSEEK_API_BETA"))
        
        # 参数配置 (可以提取到 config 文件中)
        self.model_name = "deepseek-chat" 
        self.temperature = 1.3  # 较高的温度让 AI 更有人味
        
        # 最后一次思考日志
        self.last_thinking_log : NormalResponse | ActiveResponse | None = None
        
        self.logger.info("BrainLayer initialized successfully.")
    
    # ===========================================================================================================================
    # 接口方法
    # ===========================================================================================================================
    
    def get_status(self) -> dict:
        """获取当前大脑层状态的摘要信息"""
        status = {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "last_thinking_log": self.last_thinking_log.to_dict() if self.last_thinking_log else None
        }
        return status    

    def generate_reply(self, 
                       user_input: UserMessage, 
                       personality: str, 
                       mood: str,
                       micro_memories: list[MicroMemory],
                       macro_memories: list[MacroMemory],
                       history: list[ChatMessage], 
                       l0_output: AmygdalaOutput
                       ) -> NormalResponse:
        """
        [接口方法] 核心对话生成
        采用双重思考 (Dual-Think) 模式，同时生成“内心想法”(Inner Thought) 和“公开回复”(Public Reply)
            1. 内心想法：AI 对用户输入的即时反应，包含情感色彩和潜在动机
            2. 公开回复：AI 面向用户的正式回答，通常更理性和礼貌
        通过这种方式，AI 能够展现更丰富的个性和情感层次，使对话更加生动自然。
        参数:
            user_input: 用户的输入消息
            personality: L3 人格设定文本块
            mood: 当前情绪描述
            micro_memories: 近期微观记忆列表
            macro_memories: 宏观记忆列表
            history: 历史对话消息列表
            l0_output: L0 模块输出的感知信息
        返回值:
            NormalResponse: 包含内心想法、公开回复和情绪的对象
        """
        self.logger.info("Generating reply for user input.")
        # TODO 测试用，实际调用时请传入真实的参数
        # 目前先用传入的 mood 参数，后续考虑扩展，不只是情绪，而是更全面的状态描述
        current_state:str = mood  
        
        # 将记忆格式化为文本格式
        memories: str =  self._construct_memories(micro_memories, macro_memories)
        
        try:
            # 1. 构建系统级 Prompt (System Prompt)
            # 将人格设定和记忆注入到 System 区域，确保模型遵循人设
            system_prompt = self._construct_system_prompt(
                l3_personality=personality,
                l0_output=l0_output, 
                memories=memories,
                current_state=current_state
            )
            self.logger.info("System prompt constructed.")
            
            # 拼装消息列表
            messages: list = self._construct_messages(system_prompt, history, user_input)
            
            # 2. 调用 LLM
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                stream=False
            )
            
            # 3. 处理返回结果
            # 因为是对话前缀续写，需要手动加上'{'组成完整的json格式
            raw_content = response.choices[0].message.content
            if raw_content:
                raw_content = '{' + raw_content
            self.logger.info("----- LLM Raw Response -----")
            self.logger.info(raw_content)
            self.logger.info("----- End of LLM Raw Response -----")

            # 4. 解析
            res: NormalResponse = self.parse_llm_dual_think_response(raw_content)
            
            # 5. 将最后一次思考日志保存到属性中
            self.last_thinking_log = res
            
            self.logger.info(f"This turn useage: Token:{response.usage}")
            return res

        except Exception as e:
            self.logger.error(f"[L1 Error] Generate reply failed: {e}", exc_info=True)
            return NormalResponse(inner_thought="(系统想法: 模型输出格式错误，可能是被截断或触发过滤)", 
                                  public_reply="哎呀，我刚刚走神了，没听清你在说什么，能再说一遍吗？", 
                                  mood="") # 发生错误时的兜底回复，保持沉默或简单的拟声词
    
    
    def decide_to_act(self, 
                      silence_duration: timedelta, 
                      last_speaker: str,
                      cur_mood: str,
                      cur_envs: EnvironmentInformation, 
                      recent_conversations: list[ChatMessage]
                      )-> ActiveResponse:
        """
        决定是否主动开口
        参数:
            silence_duration: 自上次交互以来的静默时间(包含用户和AI双方)
            last_speaker: 上次发言者 ("Elysia" 或 "妖梦")
            cur_mood: 当前心情描述
            cur_envs: 当前环境信息
            recent_conversations: 最近的对话列表
        返回值:
            ActiveResponse: 包含是否开口及相关信息的对象
        """
        
        self.logger.info("Deciding whether to initiate conversation.")
        current_mood =  cur_mood
        
        # 1. 格式化最近对话
        lines = []
        for msg in recent_conversations:
            lines.append(f'  {msg.role}: {msg.content} | {msg.timestamp} | {datetime.fromtimestamp(msg.timestamp)}')
        recent_convs =  "[\n" + "\n".join(lines) + "\n]"
        self.logger.info(f"Recent conversations formatted: {recent_convs}")
        
        # 2. 构造system prompt
        system_prompt = l1_decide_to_act_template.format(
            user_name="妖梦",
            last_speaker=last_speaker,
            silence_duration=silence_duration.__str__(),
            current_mood=current_mood,
            current_time_envs=cur_envs.time_envs.to_l1_decide_to_act_dict(),
            recent_conversations=recent_convs,
        )
        self.logger.info("System prompt for decide_to_act constructed.")
        
        # 对话前缀续写
        messages: list = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "assistant", "content": "{\n", "prefix": True})
        self.logger.info("Messages for decide_to_act constructed.")
        
        # 3. 调用llm
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )
        self.logger.info("LLM response received for decide_to_act.")
        # 4. 处理回复
        # 因为是对话前缀续写，需要手动加上'{'组成完整的json格式
        raw_content = response.choices[0].message.content
        if raw_content:
                raw_content = '{' + raw_content
        self.logger.info("----- LLM Raw Response -----")
        self.logger.info(raw_content)
        self.logger.info("----- End of LLM Raw Response -----")
        
        # 5. 解析
        res: ActiveResponse = self.parse_llm_decide_to_act_response(raw_content)
        
        # 6. 将最后一次思考日志保存到属性中
        self.last_thinking_log = res
        self.logger.info("------------------------------------------------------------------------------------------------")
        return res
    
    # ===========================================================================================================================
    # 内部函数实现
    # ===========================================================================================================================
    
    def _construct_memories(self, 
                            micro_memories: list[MicroMemory], 
                            macro_memories: list[MacroMemory]
                            )-> str:
        """将各种格式的记忆文本格式化"""
        
        self.logger.info("Formatting memories into text lines.")
        
        def format_micro_memories_to_lines(memories: list[MicroMemory])-> str:
            """将micro memories格式化为文本行"""
            lines = []
            for mem in memories:
                lines.append(f"- {datetime.fromtimestamp(mem.timestamp).isoformat()} (Poignancy: {mem.poignancy}) {mem.content}")
            return "[\n" + "\n".join(lines) + "\n]"
        
        def format_macro_memories_to_lines(memories: list[MacroMemory])-> str:
            """将macro memories格式化为文本行"""
            lines = []
            for mem in memories:
                lines.append(f"- {datetime.fromtimestamp(mem.timestamp).isoformat()} (Poignancy: {mem.poignancy}) (Dominant Emotion: {mem.dominant_emotion})  {mem.diary_content}")
            return "[\n" + "\n".join(lines) + "\n]"
                
        
        res: str = l2_memory_block_template.format(
            micro_memory=format_micro_memories_to_lines(micro_memories),
            macro_memory=format_macro_memories_to_lines(macro_memories)
        )
        self.logger.info("Memories formatted into text lines.")
        return res
    
    
    def _construct_messages(self, system_prompt: str, history: list[ChatMessage], user_input: UserMessage):
        
        # 拼装消息列表
        messages: list = [{"role": "system", "content": system_prompt}]
        
        # 注入历史记录 
        if history is not None and len(history) > 0:
            for msg in history: 
                if msg.role == "妖梦":
                    messages.append({"role": "user", "content": msg.content})
                elif msg.role == "Elysia":
                    messages.append({"role": "assistant", "content": msg.content + f'\n(内心想法):{msg.inner_voice}'})
                else:
                    raise ValueError(f"Role error: {msg.role}")
        # 注入当前用户输入
        messages.append({"role": "user", "content": user_input.content})
        
        # 对话前缀续写
        messages.append({"role": "assistant", "content": "{\n", "prefix": True})
        
        return messages
            

    def _construct_system_prompt(self, 
                                l3_personality: str,
                                l0_output: AmygdalaOutput,
                                memories: str,
                                current_state: str
                                ) -> str:
        # 拼装current_state
        # TODO 待扩展
        current_state = current_state_template.format(
            mood=current_state
        )
        
        # 拼装 System Prompt
        system_prompt = SystemPromptTemplate.format(
            l3_personality_block=l3_personality,
            l0_sensory_block=l0_output.perception,
            l2_memory_block=memories,
            current_state=current_state
        )
        self.logger.info("-------------------------------------------")
        self.logger.info("Debug Info:")
        self.logger.info(system_prompt)
        self.logger.info("-------------------------------------------")
        
        return system_prompt
    
    
    def parse_llm_decide_to_act_response(self, llm_raw_output)-> ActiveResponse:
        """ 解析 LLM 决定是否主动开口的回复 """
         # 1. 打印原始内容的 repr()，这样能看到空格、换行符等不可见字符
        self.logger.info(f"DEBUG: Raw Output type: {type(llm_raw_output)}")
        self.logger.info(f"DEBUG: Raw Output repr: {repr(llm_raw_output)}") 
        
        # 2. 清洗数据（防止模型输出 ```json ... ``` 包裹）
        cleaned_output = llm_raw_output.strip()
        if cleaned_output.startswith("```"):
            cleaned_output = cleaned_output.replace("```json", "").replace("```", "")
            
        try:
            data = json.loads(cleaned_output)
            
            res = ActiveResponse(
                should_speak=data['should_speak'],
                inner_voice=data['inner_voice'],
                public_reply=data['public_reply'],
                mood=data['mood']
            )
            self.logger.info("LLM output parsed into ActiveResponse.")
            return res
        except Exception as e:
            self.logger.error("Error to convert llm raw content to ActiveResponse.", exc_info=True)
            raise e
            
        
    def parse_llm_dual_think_response(self, llm_raw_output)-> NormalResponse:
        """ 解析 LLM 双重思考回复 """
        # 1. 打印原始内容的 repr()，这样能看到空格、换行符等不可见字符
        self.logger.info(f"DEBUG: Raw Output type: {type(llm_raw_output)}")
        self.logger.info(f"DEBUG: Raw Output repr: {repr(llm_raw_output)}") 
        
        # 2. 清洗数据（防止模型输出 ```json ... ``` 包裹）
        cleaned_output = llm_raw_output.strip()
        if cleaned_output.startswith("```"):
            cleaned_output = cleaned_output.replace("```json", "").replace("```", "")
            
        try:
            data = json.loads(cleaned_output)
            self.logger.info("LLM output parsed into dual think response.")
            return NormalResponse(
                inner_thought=data["inner_voice"],
                public_reply=data["public_reply"],
                mood=data["mood"]
            )
        except json.JSONDecodeError as e:
            self.logger.error("!!! JSON 解析失败 !!!", exc_info=True)
            self.logger.error(f"错误信息: {e}")
            self.logger.error(f"导致错误的内容: {llm_raw_output}")
            
            # 3. 兜底策略 (Fallback)
            # 如果解析失败，与其让程序崩溃，不如返回一个默认回复，保证对话继续
            return NormalResponse(DEFAULT_ERROR_INNER_THOUGHT, DEFAULT_ERROR_PUBLIC_REPLY, DEFAULT_ERROR_MOOD)
    
