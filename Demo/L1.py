
from datetime import datetime, date
import time
from L0 import UserMessage, L0_Output
import json
from openai import OpenAI

SystemPromptTemplate = """
# Role Definition 
{l3_persona_block}

# L0 Sensory Input 
{l0_sensory_block} 

# L2 Memory Context 
{l2_memory_block}

# Current State
{current_state}

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
"inner_voice": "(Write what you actually say to the user here...)",
"reply": "(Write what you actually say to the user here...)"
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
    def __init__(self, role: str, content: str, timestamp: float = time.time()):
        self.role: str = role
        self.content: str = content
        self.timestamp: float = timestamp
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp
        }
    
    def embed_in_prompt(self):
        return {
            "role": self.role,
            "content": self.content,
        }    
        

class SessionState:
    def __init__(self):
        self.conversations: list[ChatMessage] = []
        self.last_interaction_time = 0.0
        self.short_term_goals: str = "Just chatting"
        self.current_mood: str = "Neutral"

    def debug(self):
        print("----- SessionState Debug Info -----")
        print(f"Time: {datetime.fromtimestamp(time.time())}")
        print(f"  Last Interaction Time: {self.last_interaction_time}")
        print(f"  Short Term Goals: {self.short_term_goals}")
        print(f"  Current Mood: {self.current_mood}")
        print("  Conversation History:")
        for msg in self.conversations:
            print(f"    {msg.role} at {msg.timestamp}: {msg.content}")
        print("----- End of Debug Info -----")


class L1_Module:
    def __init__(self,client: OpenAI):
        self.client = client

    def run_l1_turn(self, session_state: SessionState, user_input: UserMessage, l0_context: L0_Output):
        # 1. 拼装 Prompt
        messages: list = self.construct_prompt(session_state, user_input, l0_context, l3_persona_example)

        # 2. 调用 LLM (假设用 OpenAI API)
        response = self.client.chat.completions.create(
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
            ChatMessage(role="user", content=user_input.content)
        )
        
        # 技巧：存入历史时，我们可以选择是否把 inner_voice 塞进去给 LLM 看
        # 为了连贯性，建议将 inner_voice 作为一个特殊的 context 存入，
        # 但在发给 LLM 时标记清楚这是"上一轮的想法"。
        session_state.conversations.append(
            ChatMessage(role="assistant", content=f"{public_reply}\n(Meta-Context: My previous thought was: {inner_thought})")
        )
        session_state.debug()
        return public_reply, inner_thought

    def prune_history(self, history: list[ChatMessage], conversation_limit=3, max_limits=20) -> list[ChatMessage]:
        # 假设 history 结构是 [msg1, msg2, msg3, ...]
        # 我们保留最近 6 条消息 (3轮) 的完整内容
        # 对于更早的消息，只保留回复部分，去掉 Inner Thought
        # 对更早的消息，用正则把 (Meta-Context: ...) 部分清洗掉
        # 对于非常老的消息，直接丢弃，保持总长度不超过 max_limits
        
        if len(history) > max_limits:
            history = history[-max_limits:]
        
        threshold_index = len(history) - 2 * conversation_limit
        if threshold_index > 0:
            for i in range(threshold_index):
                if history[i].role == "assistant":
                    # 清洗掉 Inner Thought，只留 Reply
                    clean_content = history[i].content.split("\n(Meta-Context:")[0]
                    history[i] = ChatMessage(role=history[i].role, content=clean_content, timestamp=history[i].timestamp)
        return history
    
    def parse_llm_response(self, llm_raw_output) -> tuple[str, str]:
        data = json.loads(llm_raw_output)
        inner_voice = data.get("inner_voice", "...")
        reply_text = data.get("reply", "...")

        return inner_voice, reply_text


    def construct_prompt(self, session_state: SessionState, user_input: UserMessage, l0_data: L0_Output, l3_persona: str) -> list[dict]:
        # 拼装 Prompt
        related_memories = []
        current_state = []
        system_prompt = SystemPromptTemplate.format(
            l3_persona_block=l3_persona,
            l0_sensory_block=l0_data.sensory_data,
            l2_memory_block=session_state.short_term_goals + "\n" + session_state.current_mood,
            current_state=current_state 
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # 注入历史记录 (注意：这里有一个策略点，下文会讲)
        # TODO 目前是全部装进去了，并没有修剪，后面再考虑
        if session_state.conversations is not None and len(session_state.conversations) > 0:
            for message in session_state.conversations: 
                messages.append({"role": f"{message.role}", "content": message.content})

        messages.append({"role": "user", "content": user_input.content})

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
        
        l0_output = l0.process_user_message(user_input)
        
        reply, inner_thought = l1.run_l1_turn(session_state, user_input, l0_output)
        
        print(f"Elysia (Inner Thought): {inner_thought}")
        print(f"Elysia (Reply): {reply}")
        print("-----")
       

if __name__ == "__main__":
    # simple_test()
    test()
    
    
    