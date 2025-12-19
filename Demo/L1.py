
from datetime import datetime
import time
import json
from openai import OpenAI

from Demo.Prompt import SystemPromptTemplate
from Demo.L0 import UserMessage, L0_Output
from openai.types.chat import ChatCompletionMessage

class ChatMessage:
    def __init__(self, role: str, content , inner_voice: str = "", timestamp: float = time.time()):
        self.role: str = role
        self.content = content
        self.inner_voice: str = inner_voice
        self.timestamp: float = timestamp
    
    @classmethod
    def from_ChatCompletionMessage(cls, message: ChatCompletionMessage, timestamp: int):
        return cls(role=message.role, 
                   content=message.content, 
                   inner_voice="",
                   timestamp=float(timestamp))
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "inner_voice":self.inner_voice,
            "timestamp": self.timestamp
        }
        
    def debug(self):
        print(self.to_dict())


class SessionState:
    """会话状态（包含当前聊天的部分上下文）"""
    def __init__(self, user_name: str, role: str, max_messages_limit: int = 20, max_inner_limit = 3):
        self.user_name: str = user_name     # 用户的名字
        self.role: str = role               # AI的名字
        
        self.max_messages_limit: int = max_messages_limit    # 最大对话数(含inner voice + 不含inner voice)
        self.max_inner_limit: int = max_inner_limit     # 最大包含inner voice的对话数
        
        self.conversations: list[ChatMessage] = []
        self.last_interaction_time: float = time.time()
        
        # TODO 下面这两项是否需要到单独拿出来作为一个“当前状态”的信息类？需要更新
        self.short_term_goals: str = "Just chatting"
        self.current_mood: str = "Neutral"


    def add_messages(self, messages: list[ChatMessage]):
        if messages is not None and len(messages) == 0:
            return
        for msg in messages:
            self.conversations.append(msg)
        self.update_last_interaction_time()
        
    def update_goal(self, goal: str):
        if not goal:
            print("Error! New goal is invalid!")
        self.short_term_goals = goal
        
    def update_mood(self, mood: str):
        if not mood:
            print("Error! New mood is invalid!")
        self.current_mood = mood
        
    def update_last_interaction_time(self)->float:
        """更新最后交互时间（以最后一条消息为准）"""
        if len(self.conversations) == 0 :
            print("Error, SessionSate has empty conversations!")
            return 0.0
        self.last_interaction_time = self.conversations[-1].timestamp
        return self.last_interaction_time
    
    def prune_history(self):
        # 假设 history 结构是 [msg1, msg2, msg3, ...]
        # 我们保留最近 6 条消息 (3轮) 的完整内容
        # 对于更早的消息，只保留回复部分，去掉 Inner Thought
        # 对于非常老的消息，直接丢弃，保持总长度不超过 max_limits
        # TODO 待配套完善
        
        # 丢弃老消息
        if len(self.conversations) > self.max_messages_limit:
            history = self.conversations[-self.max_messages_limit:]
        
        # 清洗inner thought
        threshold_index = len(history) - 2 * self.max_inner_limit
        if threshold_index > 0:
            for i in range(threshold_index):
                if history[i].role == self.role:
                    # 清洗掉 Inner Thought，只留 Reply
                    history[i].inner_voice = ""
                    
        self.conversations.clear()
        self.conversations = history
    
    
    def debug(self):
        print("-------------------- SessionState Debug Info --------------------")
        print(f"Time: {datetime.fromtimestamp(time.time())}")
        print(f"  Last Interaction Time: {self.last_interaction_time}")
        print(f"  Short Term Goals: {self.short_term_goals}")
        print(f"  Current Mood: {self.current_mood}")
        print("  Conversation History:")
        for msg in self.conversations:
            if msg.inner_voice == "":
                print(f"    {msg.role} at {msg.timestamp}: {msg.content}")
            else:
                print(f"    {msg.role} at {msg.timestamp}: {msg.content} \n \t \t(inner_voice): {msg.inner_voice}")

        print("-------------------- End of Debug Info --------------------")


from Demo.Utils import MilvusAgent

class L1_Module:
    def __init__(self,openai_client: OpenAI):
        self.openai_client = openai_client
        self.milvus_agent = MilvusAgent(collection_name="l2_associative_memory")

    def run(self, session_state: SessionState, user_input: UserMessage, l0_context: L0_Output):
        # 1. 拼装 Prompt
        messages: list = self.construct_prompt(session_state, user_input, l0_context)
        
        print("-----------------------------DEBUG Final Prompt without system prompt-----------------------------")
        print(messages[1:])
        print("---------------------------------------------------------------------------------------------")
        
        # 对话前缀续写
        messages.append({"role": "assistant", "content": "{\n", "prefix": True})
        
        # 2. 调用 LLM 
        response = self.openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            # response_format={
            #     'type': 'json_object'
            # },
            stop=['{'],
            stream=False
        )
        raw_content = response.choices[0].message.content
        if raw_content:
            raw_content = '{' + raw_content
        print("----- LLM Raw Response -----")
        print(raw_content)
        print("----- End of LLM Raw Response -----")

        # 3. 解析
        inner_thought, public_reply = self.parse_llm_response(raw_content)
        
        # 4. 更新 L1 状态 (关键步骤！)
        # 我们不仅存“说的话”，还要存“想的话”，以便让 AI 记得自己的思路
        session_state.add_messages(
            [ChatMessage(role="妖梦", content=user_input.content)]
        )
        
        
        # 技巧：存入历史时，我们可以选择是否把 inner_voice 塞进去给 LLM 看
        # 为了连贯性，建议将 inner_voice 作为一个特殊的 context 存入，
        # 但在发给 LLM 时标记清楚这是"上一轮的想法"。
        session_state.add_messages(
            [ChatMessage(role="Elysia", content=public_reply, inner_voice=inner_thought)]
        )
        session_state.debug()
        
        print(f"This turn useage: Token:{response.usage}")
        return public_reply, inner_thought

    
    def parse_llm_response_aux(self, llm_raw_output) -> tuple[str, str]:
        """解析llm的输出"""
        data = json.loads(llm_raw_output)
        inner_voice = data.get("inner_voice", "...")
        reply_text = data.get("reply", "...")

        return inner_voice, reply_text

    def parse_llm_response(self, llm_raw_output)-> tuple[str, str]:
        # 1. 打印原始内容的 repr()，这样能看到空格、换行符等不可见字符
        print(f"DEBUG: Raw Output type: {type(llm_raw_output)}")
        print(f"DEBUG: Raw Output repr: {repr(llm_raw_output)}") 
        
        # 2. 清洗数据（防止模型输出 ```json ... ``` 包裹）
        cleaned_output = llm_raw_output.strip()
        if cleaned_output.startswith("```"):
            cleaned_output = cleaned_output.replace("```json", "").replace("```", "")
        
        try:
            data = json.loads(cleaned_output)
            return data["inner_voice"], data["reply"] # 假设你的JSON结构是这样
        except json.JSONDecodeError as e:
            print(f"!!! JSON 解析失败 !!!")
            print(f"错误信息: {e}")
            print(f"导致错误的内容: {llm_raw_output}")
            
            # 3. 兜底策略 (Fallback)
            # 如果解析失败，与其让程序崩溃，不如返回一个默认回复，保证对话继续
            return "(系统想法: 模型输出格式错误，可能是被截断或触发过滤)", "哎呀，我刚刚走神了，没听清你在说什么，能再说一遍吗？"

    def construct_prompt(self, session_state: SessionState, user_input: UserMessage, l0_data: L0_Output) -> list[dict]:
        """ 拼装 Prompt """
        l0_sensory_block_template = """
        <facts>
            Current_Time: {current_time}
            Time of day: {time_of_day}
            Day of Week: {day_of_week}
            Season: {season}
            User_Latency: {latency}
        </facts>

        <perception>
            Perception: {perception}
        </perception>
        """
        l0_sensory_block = l0_sensory_block_template.format(
            current_time=l0_data.envs.current_time,
            time_of_day=l0_data.envs.time_of_day,
            day_of_week=l0_data.envs.day_of_week,
            season=l0_data.envs.season,
            latency=l0_data.envs.user_latency,
            perception=l0_data.perception
        )
        
        # 检索记忆
        related_memories: list[dict] = self.milvus_agent.retrieve(query_text=user_input.content)
        
        print("--------------------DEBUG Related Memories--------------------")
        for r in related_memories:
            print(r)
        print("-------------------------------------------------------------------")
        
        l2_related_memories = []
        for memory in related_memories:
            l2_related_memories.append(f'  {memory['content']}')
        l2_related_memories = "[\n" + "\n".join(l2_related_memories) + "\n]"
        
        # 获取L3 人格设定
        from Demo.Prompt import l3_persona_example
        l3_persona: str = l3_persona_example
        
        system_prompt = SystemPromptTemplate.format(
            l3_persona_block=l3_persona,
            l0_sensory_block=l0_sensory_block,
            l2_memory_block=l2_related_memories,
            current_mood=session_state.current_mood,
            short_term_goal=session_state.short_term_goals
        )
        print("-------------------------------------------")
        print("Debug Info:")
        print(system_prompt)
        print("-------------------------------------------")
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # 注入历史记录 
        # TODO 目前是全部装进去了，并没有修剪，后面再考虑
        if session_state.conversations is not None and len(session_state.conversations) > 0:
            for msg in session_state.conversations: 
                if msg.role == "妖梦":
                    messages.append({"role": "user", "content": msg.content})
                elif msg.role == "Elysia":
                    messages.append({"role": "assistant", "content": msg.content + f'\n(内心想法):{msg.inner_voice}'})
                else:
                    raise ValueError(f"Role error: {msg.role}")
        
        messages.append({"role": "user", "content": user_input.content})
        
        return messages 


def test():
    from L0 import L0_Module
    from dotenv import load_dotenv
    import os
    load_dotenv()
    url = os.getenv("DEEPSEEK_API_BETA")
    client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=url)
    
    l0 = L0_Module(client)
    l1 = L1_Module(client)
    session_state = SessionState(user_name="妖梦", role="Elysia")
    
    while(True):
        user_input = UserMessage(input("User: "))
        
        l0_output = l0.run()
        
        print("------------------------L0 output------------------------")
        print(l0_output.debug())
        print("-------------------------------------------------------------------------")
        
        reply, inner_thought = l1.run(session_state, user_input, l0_output)
        
        print(f"Elysia (Inner Thought): {inner_thought}")
        print(f"Elysia (Reply): {reply}")
        print("-----")
       

if __name__ == "__main__":
    # simple_test()
    test()
    
    
    