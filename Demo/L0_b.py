"""
L0_b 模块：
    2. 生成本能反应 ---> 输出本能反应
    
eg.
    L0 (潜意识/边缘系统/杏仁核)：
        职责：处理原始信号。它不负责社交，不负责语言，只负责**“产生情绪化学反应”**。
        特点：它很快，很原始，无法控制。
        输入：时间、心跳、沉默时长。
        输出：状态 (State) —— 如“焦虑”、“饥饿”、“兴奋”。
        例子：“我在发抖，我心跳很快。”（这不需要逻辑，这是生理反应）。

    L1 (主意识/前额叶皮层)：
        职责：处理社会行为。它负责把 L0 产生的情绪包装成语言。
        特点：它是理性的，它会撒谎，会伪装。
        输入：用户的话 + L0 传来的状态。
        输出：行为 (Behavior) —— 如“假装不在意”、“撒娇”、“阴阳怪气”。
        例子：“虽然我很慌（L0），但我决定深呼吸，回一句‘没事’（L1）。”
        
    模拟“口是心非” (Internal Conflict)
        这是拟人化最高级的地方。 只有当 L0 和 L1 分离时，你才能制造出完美的“口是心非”。
        L0 输出：State: Vulnerable, Lonely (我很脆弱，很想他)。
        L1 思考：潜意识告诉我我很想他，但我不能表现得太廉价（Elysia 的自尊心）。
        L1 最终表现：冷淡地回一句“哦，你来了。”（但内心独白是“太好了他终于来了”）。
        如果只有 L1，它很难同时hold住“原始欲望”和“社会面具”两个维度的计算，往往会顾此失彼。

ps:
    L0（潜意识/身体）
    L1（主意识/大脑皮层）
    专门的“情绪预处理器
    如果只有 L1，它很难同时hold住“原始欲望”和“社会面具”两个维度的计算，往往会顾此失彼。
    如果你想要 Elysia 偶尔“理智控制不住情绪”，或者“嘴硬心软”，那么保留 L0 是必须的，因为它代表了那个“无法控制的身体本能”
"""

from Demo.L0_a import EnvironmentInformation

class AmygdalaOutput:
    """ L0_b Amygdala 输出类"""
    def __init__(self, perception: str, envs: EnvironmentInformation):
        self.perception: str = perception
        self.envs: EnvironmentInformation = envs
        
    def to_dict(self) -> dict:
        """将 L0_b Amygdala 输出转换为字典格式"""
        return {
            "perception": self.perception,
            "envs": self.envs
        }
        
    def debug(self):
        print(f"perception: {self.perception} \n envs:{self.envs.to_dict()}")

from openai import OpenAI
from datetime import datetime
from Demo.L0_a import TimeInfo
from Demo.Session import  UserMessage

class Amygdala:
    """ L0_b 杏仁核模块"""
    def __init__(self, openai_client: OpenAI):
        self.openai_client = openai_client
        self.l3_core_dientity: str = self.get_l3_core_dientity()
        
    def get_l3_core_dientity(self):
        """获取L3核心身份信息"""
        # TODO 从L3模块获取
        from Demo.Prompt import l0_elysia_persona_block
        return l0_elysia_persona_block
    
    def run(self, user_message: UserMessage, current_env: EnvironmentInformation) -> AmygdalaOutput:
        #  生成描述
        sensory_description: str = self.generate_sensory_description( user_message, current_env)
        #  更新最后交互时间

        return AmygdalaOutput(sensory_description, current_env)
    
    
    def generate_sensory_description(self, user_message: UserMessage, envs: EnvironmentInformation)-> str:
        """生成本能描述"""
        
        latency_desc = envs.time_envs.user_latency
        dt = datetime.fromtimestamp(envs.time_envs.current_time)
        
        # 构建 Prompt
        from Demo.Prompt import L0_SubConscious_System_Prompt, L0_SubConscious_User_Prompt, l0_elysia_persona_block
        system_prompt = L0_SubConscious_System_Prompt.format(
            character_name="Elysia",
            l3_persona_block=self.get_l3_core_dientity()
        )
        user_prompt = L0_SubConscious_User_Prompt.format(
            current_time=dt.isoformat(),
            day_of_week=dt.strftime("%A"),
            time_of_day=envs.time_envs.time_of_day,
            season=envs.time_envs.season,
            latency=envs.time_envs.user_latency,
            latency_description=latency_desc,
            user_message=user_message.content
        )
        print("User Prompt:")
        print(user_prompt)
        
        # 调用 OpenAI API 生成描述
        response = self.openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            stream=False
        )
        
        if not response.choices[0].message.content:
            print("Error! Get empty response content.")
            return ""
        # 获取生成的文本    
        raw_content = response.choices[0].message.content
        
        return raw_content
    
    
def test():
    import time
    from dotenv import load_dotenv
    from openai import OpenAI
    import os
    load_dotenv()
    
    url = os.getenv("DEEPSEEK_API_BETA")
    openai_client =  OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=url)
    amygdala = Amygdala(openai_client)
    
    # 构造测试环境信息
    time_info = TimeInfo(
        current_time=time.time(),
        user_latency=5.0,
        last_message_timestamp=time.time() - 10.0
    )
    from Demo.L0_a import EnvironmentInformation
    env_info = EnvironmentInformation(time_info)
    user_message = UserMessage(content="我今天分手了，我不知道该怎么办。")
    output = amygdala.run(user_message, env_info)
    output.debug()
    
    
if __name__ == "__main__":
    test()
    
    