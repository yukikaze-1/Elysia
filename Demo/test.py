from Core.PromptManager import PromptManager
from Config.Config import PromptManagerConfig
from Prompt.Prompt import l3_elysia_persona_block


def test():
    config = PromptManagerConfig(
        logger_name="PromptManagerTest",
        template_dir="Prompt"
    )
    pm = PromptManager(config=config)
    res = pm.render_macro(
        "Amygdala.j2",
        "AmygdalaSystemPrompt",
        character_name="Elysia",
        l3_persona_block=l3_elysia_persona_block
    )
    print(res)
    
    print(pm.render_macro(
        "Amygdala.j2",
        "AmygdalaUserPrompt",
        current_time="2024-06-01 12:00:00",
        time_of_day="afternoon",
        day_of_week="Saturday",
        season="spring",
        user_reaction_latency=1.5,
        user_message="I feel a bit lost today."
        ))
    
    
if __name__ == "__main__":
    test()
    
    