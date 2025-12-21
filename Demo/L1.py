import json
from openai import OpenAI

from Demo.Prompt import SystemPromptTemplate
from Demo.Utils import MilvusAgent
from Demo.L0_a import EnvironmentInformation
from Demo.L0_b import AmygdalaOutput 
from Demo.Session import SessionState, ChatMessage, UserMessage

class L1_Module:
    """大脑"""
    def __init__(self,openai_client: OpenAI):
        self.openai_client = openai_client
        self.milvus_agent = MilvusAgent(collection_name="l2_associative_memory")

    def run(self, session_state: SessionState, user_input: UserMessage, l0_output: AmygdalaOutput):
        # 1. 拼装 Prompt
        messages: list = self.construct_prompt(session_state, user_input, l0_output)
        
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
        # 3. 处理返回结果
        raw_content = response.choices[0].message.content
        if raw_content:
            raw_content = '{' + raw_content
        print("----- LLM Raw Response -----")
        print(raw_content)
        print("----- End of LLM Raw Response -----")

        # 4. 解析
        inner_thought, public_reply = self.parse_llm_response(raw_content)
        
        # 5. 更新 会话状态
        session_state.add_messages(
            [ChatMessage(role="妖梦", content=user_input.content)]
        )
        session_state.add_messages(
            [ChatMessage(role="Elysia", content=public_reply, inner_voice=inner_thought)]
        )
        
        session_state.debug()
        
        print(f"This turn useage: Token:{response.usage}")
        return public_reply, inner_thought

    
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


    def construct_prompt(self, session_state: SessionState, 
                         user_input: UserMessage, 
                         l0_output: AmygdalaOutput) -> list[dict]:
        """ 拼装 Prompt """
        # 1. 构造 L0 感官区块
        from Demo.Prompt import l0_sensory_block_template
        l0_sensory_block = l0_sensory_block_template.format(
            current_time=l0_output.envs.time_envs.current_time,
            time_of_day=l0_output.envs.time_envs.time_of_day,
            day_of_week=l0_output.envs.time_envs.day_of_week,
            season=l0_output.envs.time_envs.season,
            latency=l0_output.envs.time_envs.user_latency,
            perception=l0_output.perception
        )
        
        # 2. 检索记忆
        related_memories: list[dict] = self.milvus_agent.retrieve(query_text=user_input.content)
        
        print("--------------------DEBUG Related Memories--------------------")
        for r in related_memories:
            print(r)
        print("-------------------------------------------------------------------")
        
        l2_related_memories = []
        for memory in related_memories:
            l2_related_memories.append(f'  {memory['content']}')
        l2_related_memories = "[\n" + "\n".join(l2_related_memories) + "\n]"
        
        # 3. 获取L3 人格设定
        from Demo.Prompt import l3_persona_example
        l3_persona: str = l3_persona_example
        
        # 4. 拼装 System Prompt
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
        
        # 5. 拼装消息列表
        messages = [{"role": "system", "content": system_prompt}]
        
        # 注入历史记录 
        if session_state.conversations is not None and len(session_state.conversations) > 0:
            for msg in session_state.conversations: 
                if msg.role == "妖梦":
                    messages.append({"role": "user", "content": msg.content})
                elif msg.role == "Elysia":
                    messages.append({"role": "assistant", "content": msg.content + f'\n(内心想法):{msg.inner_voice}'})
                else:
                    raise ValueError(f"Role error: {msg.role}")
        # 注入当前用户输入
        messages.append({"role": "user", "content": user_input.content})
        
        return messages 


def test():
    from Demo.L0_a import L0_Sensory_Processor
    from Demo.L0_b import Amygdala, AmygdalaOutput
    from dotenv import load_dotenv
    import os
    load_dotenv()
    url = os.getenv("DEEPSEEK_API_BETA")
    client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=url)
    
    l0_a = L0_Sensory_Processor()
    l0_b = Amygdala(client)
    l1 = L1_Module(client)
    session_state = SessionState(user_name="妖梦", role="Elysia")
    
    while(True):
        user_input = UserMessage(input("User: "))
        l0_a_output: EnvironmentInformation = l0_a.get_envs()
        l0_b_output: AmygdalaOutput = l0_b.run(user_message=user_input, current_env=l0_a_output)
        l0_output = l0_b_output
        
        print("------------------------L0 output------------------------")
        print(l0_b_output.debug())
        print("-------------------------------------------------------------------------")
        
        reply, inner_thought = l1.run(session_state, user_input, l0_output)
        
        print(f"Elysia (Inner Thought): {inner_thought}")
        print(f"Elysia (Reply): {reply}")
        print("-----")
       

if __name__ == "__main__":
    # simple_test()
    test()
    
    
    