
from openai import OpenAI

import os

from Demo.L0_a import EnvironmentInformation, L0_Sensory_Processor
from Demo.L0_b import Amygdala, AmygdalaOutput
from Demo.L1 import L1_Module, UserMessage, ChatMessage, SessionState
from Demo.Reflector import MemoryReflector

def main():
    from dotenv import load_dotenv
    load_dotenv()
    
    openai_client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com"))
    
    l0_a = L0_Sensory_Processor()
    l0_b = Amygdala(openai_client)
    l1 = L1_Module(openai_client)
    reflector = MemoryReflector(openai_client)
    
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
    main()
    
    