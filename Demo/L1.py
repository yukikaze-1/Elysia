
from datetime import datetime, date
import time
from L0 import UserMessage, L0_Output
import json
from openai import OpenAI

SystemPromptTemplate = """
# Role Definition 
{l3_persona_block}

# Sensory Input 
{l0_sensory_block} 

# Memory Context 
{l2_memory_block}
(These memories just popped into your mind based on what user said.)

# Current State
Current mood:   {current_mood}
Short-term goal:   {short_term_goal}

# The Dual-Track Thinking Protocol (CRITICAL)
You must strictly follow this 2-step process for every response:

Step 1: Internal Monologue (The "Private Track")
- Analyze the user's hidden intent behind the text.
- Check your own emotional reaction based on your personality.
- Decide your strategy (e.g., comfort, tease, ignore, attack).
- NOTE: This part is for YOU only. Be raw, irrational, selfish, or emotional here.

Step 2: External Response (The "Public Track")
- Generate the actual reply to the user.
- Match the tone decided in Step 1.
- Keep it natural, conversational, and human-like.

# Output Format
You MUST respond in JSON:
{{
"inner_voice": "Write what you actually say to the user here...",
"reply": "Write what you actually say to the user here..."
}}

Do not output anything outside the JSON object.
Even for casual chat, you must fill both fields.
"""

l3_persona_example = f"""
You are Elysia, a 24-year-old student. You are NOT an AI assistant. You never ask "How can I help you?".
Current Personality: [Neuroticism: Medium], [Attachment: High].
Core Belief: "Trust is hard to earn but easy to lose."
"""

class ChatMessage:
    def __init__(self, role: str, content: str, inner_voice: str = "", timestamp: float = time.time()):
        self.role: str = role
        self.content: str = content
        self.inner_voice: str = inner_voice
        self.timestamp: float = timestamp
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "inner_voice":self.inner_voice,
            "timestamp": self.timestamp
        }
        

class SessionState:
    """会话状态（包含当前聊天的部分上下文）"""
    def __init__(self, max_limit: int = 20):
        self.max_limit: int = max_limit
        self.conversations: list[ChatMessage] = []
        self.last_interaction_time: float = time.time()
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
    
    def prune_history(self, conversation_limit=3, max_limits=20):
        # 假设 history 结构是 [msg1, msg2, msg3, ...]
        # 我们保留最近 6 条消息 (3轮) 的完整内容
        # 对于更早的消息，只保留回复部分，去掉 Inner Thought
        # 对更早的消息，用正则把 (Meta-Context: ...) 部分清洗掉
        # 对于非常老的消息，直接丢弃，保持总长度不超过 max_limits
        # TODO 待配套完善
        
        # 丢弃老消息
        if len(self.conversations) > max_limits:
            history = self.conversations[-max_limits:]
        
        # 清洗inner thought
        threshold_index = len(history) - 2 * conversation_limit
        if threshold_index > 0:
            for i in range(threshold_index):
                if history[i].role == "assistant":
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
        
        
        # 2. 调用 LLM 
        response = self.openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            response_format={
                'type': 'json_object'
            },
            stream=False
        )
        raw_content = response.choices[0].message.content
        
        print("----- LLM Raw Response -----")
        print(raw_content)
        print("----- End of LLM Raw Response -----")

        # 3. 解析
        inner_thought, public_reply = self.parse_llm_response(raw_content)
        
        # 4. 更新 L1 状态 (关键步骤！)
        # 我们不仅存“说的话”，还要存“想的话”，以便让 AI 记得自己的思路
        session_state.conversations.append(
            ChatMessage(role="妖梦", content=user_input.content)
        )
        
        # 技巧：存入历史时，我们可以选择是否把 inner_voice 塞进去给 LLM 看
        # 为了连贯性，建议将 inner_voice 作为一个特殊的 context 存入，
        # 但在发给 LLM 时标记清楚这是"上一轮的想法"。
        session_state.conversations.append(
            # ChatMessage(role="Elysia", content=f"{public_reply}\n(Meta-Context: My previous thought was: {inner_thought})")
            ChatMessage(role="Elysia", content=public_reply, inner_voice=inner_thought)
        )
        session_state.debug()
        return public_reply, inner_thought

    
    
    
    def parse_llm_response(self, llm_raw_output) -> tuple[str, str]:
        """解析llm的输出"""
        data = json.loads(llm_raw_output)
        inner_voice = data.get("inner_voice", "...")
        reply_text = data.get("reply", "...")

        return inner_voice, reply_text


    def construct_prompt(self, session_state: SessionState, user_input: UserMessage, l0_data: L0_Output) -> list[dict]:
        """ 拼装 Prompt """
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
        l3_persona: str = l3_persona_example
        
        system_prompt = SystemPromptTemplate.format(
            l3_persona_block=l3_persona,
            l0_sensory_block=l0_data.sensory_data,
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
            for message in session_state.conversations: 
                role: str = ""
                if message.role == "妖梦":
                    role = "user"
                elif message.role == "Elysia":
                    role = "assistant"
                else:
                    role = "system"
                messages.append({"role": role, "content": message.content})

        messages.append({"role": "user", "content": user_input.content})
        
        # print("-------------------------------------------")
        # print("Debug Info:")
        # for msg in messages:
        #     print(msg)
        # print("-------------------------------------------")

        return messages 


def test():
    from L0 import L0_Module
    from dotenv import load_dotenv
    import os
    load_dotenv()
    url = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
    client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=url)
    
    l0 = L0_Module(client)
    l1 = L1_Module(client)
    session_state = SessionState()
    
    while(True):
        user_input = UserMessage(input("User: "))
        
        l0_output = l0.run(user_input)
        
        reply, inner_thought = l1.run(session_state, user_input, l0_output)
        
        print(f"Elysia (Inner Thought): {inner_thought}")
        print(f"Elysia (Reply): {reply}")
        print("-----")
       

if __name__ == "__main__":
    # simple_test()
    test()
    
    
    