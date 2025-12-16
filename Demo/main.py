
from Demo.L1 import L1_Module, SessionState
from Demo.L0 import L0_Module, UserMessage, L0_Output
from Demo.Reflector import Reflector
from openai import OpenAI

import os

def main():
    openai_client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com"))
    
    l0 = L0_Module(openai_client)
    l1 = L1_Module(openai_client)

    reflector = Reflector(openai_client)
    
    session_state = SessionState()
    
    while(True):
        user_input = UserMessage(input("User: "))
        
        l0_output = l0.run(user_input)
        
        l1_output = l1.run(session_state, user_input, l0_output)
        
        reply, inner_thought = l1_output
        
        print("---------------------------------------------------------------------------")
        print(f"Elysia (Inner Thought): {inner_thought}")
        print(f"Elysia (Reply): {reply}")
        print("---------------------------------------------------------------------------")

        # reflector.run_l1_to_l2_reflection()
        
if __name__ == "__main__":
    main()
    
    