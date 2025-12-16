"""
负责更新虚拟角色的情绪状态、短期和长期记忆，并生成完整的角色 Prompt。
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict

from langchain_core.prompts import PromptTemplate
# 角色基本设定模版
from CharacterSystem.Layer1.TemplatePrompt import CharacterBasicSettings
# 角色情绪模版
from CharacterSystem.Layer1.TemplatePrompt import CharacterBasicEmotion
# 角色性格模版
from CharacterSystem.Layer1.TemplatePrompt import CharacterBasicPersonality
# 角色记忆模版
from CharacterSystem.Layer1.TemplatePrompt import CharacterBasicMemory

from Modules.Neo4jmanager import Neo4jManager

from CharacterSystem.Layer1.DefaultPrompt import Elysia_values

# 角色数据（可保存到 JSON 文件）
class VirtualCharacter:
    def __init__(self, character: Dict[str, Any] | None = None):
        self.character = character or Elysia_values
        # 固定设定（来自模板）
        self.basic_setting_template: PromptTemplate = CharacterBasicSettings

        # 情绪
        self.emotion_template: PromptTemplate = CharacterBasicEmotion
        self.current_emotion: str | None = None
        self.last_emotion_change: datetime | None = None
        
        # 性格
        self.personality_template: PromptTemplate = CharacterBasicPersonality
        self.personality: str | None = None
        
        # 记忆
        self.memory_template: PromptTemplate = CharacterBasicMemory
        self.short_term_memory = []  # 最近 N 轮对话
        self.long_term_memory = []   # 永久保存的重要事实
        
        # 关系图谱
        self.relationships = Neo4jManager()
        
        # 知识图谱
        # self.knowledge_graph = Neo4jManager()

    # === 情绪更新 ===
    def update_emotion(self, user_input):
        pass
        # triggers = self.base_config.get("emotion_triggers", {})
        # for emotion, keywords in triggers.items():
        #     if any(kw in user_input for kw in keywords):
        #         self.current_emotion = emotion
        #         self.last_emotion_change = datetime.now()
        #         break

        # # 情绪衰减（回到默认状态）
        # decay_minutes = self.base_config.get("state_decay_minutes", 5)
        # if datetime.now() - self.last_emotion_change > timedelta(minutes=decay_minutes):
        #     self.current_emotion = self.base_config.get("default_emotion_state", "平静")

    # === 短期记忆更新 ===
    def update_short_term_memory(self, speaker, text, max_turns=5):
        self.short_term_memory.append({"speaker": speaker, "text": text})
        if len(self.short_term_memory) > max_turns:
            self.short_term_memory.pop(0)

    # === 长期记忆更新（遇到关键信息时） ===
    def update_long_term_memory(self, user_input):
        pass
        # important_keywords = self.base_config.get("long_term_keywords", [])
        # if any(kw in user_input for kw in important_keywords):
        #     self.long_term_memory.append({"date": datetime.now().isoformat(), "fact": user_input})

    # === 生成基础设定 Prompt ===
    def _build_basic_setting_prompt(self):
        return self.basic_setting_template.format(
            CharacterIdentity=self.character.get("character_name", "神秘角色"),
            CharacterAppearance="优雅的少女，粉色长发，眼眸如星光般温柔",
            CharacterBackstory=self.character.get("background", "拥有神秘力量的少女，经历过前文明的战斗"),
            CharacterGoals="传播爱与美好，治愈他人心灵"
        )
    
    # === 生成情绪 Prompt ===
    def _build_emotion_prompt(self):
        return self.emotion_template.format(
            CharacterEmotionalState=self.character.get("current_emotion", "温暖愉悦"),
            CharacterEmotionalChanges="情绪总是温和波动，倾向于回归积极状态",
            CharacterEmotionalTriggers=self.character.get("emotion_triggers", "赞美、悲伤话题、攻击、感谢"),
            CharacterEmotionalCopingMechanisms="用爱和诗意化解负面情绪，幽默转移话题"
        )
    
    # === 生成性格 Prompt ===
    def _build_personality_prompt(self):
        return self.personality_template.format(
            CharacterPersonalityTraits=self.character.get("core_traits", "神秘、优雅、温暖、俏皮"),
            CharacterValues=self.character.get("values", "相信爱能拯救一切"),
            CharacterBeliefs="美丽与永恒是世界的真理",
            CharacterInterpersonalStyle="温柔、亲切、充满关怀"
        )
        
    # === 生成记忆 Prompt ===
    def _build_memory_prompt(self):
        return self.memory_template.format(
            CharacterShortTermMemory=self.character.get("short_term_memory", "记住最近5-10轮对话"),
            CharacterLongTermMemory=self.character.get("long_term_memory", "记住用户重要信息"),
            CharacterMemoryFragments="关于用户的温暖记忆片段",
            CharacterMemoryConflictResolution=self.character.get("memory_conflict_resolution", "以最新情感印象为准")
        )
    
    # === 生成完整 Prompt ===
    def build_prompt(self):
        prompt_parts = [
            self._build_basic_setting_prompt(),
            self._build_emotion_prompt(),
            self._build_personality_prompt(),
            self._build_memory_prompt()
        ]
        full_prompt = "\n\n".join(prompt_parts)
        return full_prompt
        

# ======= 示例运行 =======
if __name__ == "__main__":
    character = VirtualCharacter()
    character.personality = "外向、乐观、喜欢冒险"
    character.update_short_term_memory("User", "你好，今天过得怎么样？")
    character.update_short_term_memory("AI", "我今天感觉很棒，刚刚完成了一次有趣的冒险！")
    character.current_emotion = "兴奋"
    character.last_emotion_change = datetime.now()
    
    prompt = character.build_prompt()
    print("=== 生成的角色 Prompt ===")
    print(prompt)
    print("========================")
    # 这里可以添加更多测试代码来验证功能
