"""
负责更新虚拟角色的情绪状态、短期和长期记忆，并生成完整的角色 Prompt。
"""

import json
from datetime import datetime, timedelta

from CharacterSystem.Layer1.TemplatePrompt import CharacterBasicSettings

# 角色数据（可保存到 JSON 文件）
class VirtualCharacter:
    def __init__(self, config):
        # 固定设定（来自模板）
        self.base_config = config

        # 动态状态
        self.current_emotion = config.get("default_emotion_state", "平静")
        self.short_term_memory = []  # 最近 N 轮对话
        self.long_term_memory = []   # 永久保存的重要事实
        self.last_emotion_change = datetime.now()

    # === 情绪更新 ===
    def update_emotion(self, user_input):
        triggers = self.base_config.get("emotion_triggers", {})
        for emotion, keywords in triggers.items():
            if any(kw in user_input for kw in keywords):
                self.current_emotion = emotion
                self.last_emotion_change = datetime.now()
                break

        # 情绪衰减（回到默认状态）
        decay_minutes = self.base_config.get("state_decay_minutes", 5)
        if datetime.now() - self.last_emotion_change > timedelta(minutes=decay_minutes):
            self.current_emotion = self.base_config.get("default_emotion_state", "平静")

    # === 短期记忆更新 ===
    def update_short_term_memory(self, speaker, text, max_turns=5):
        self.short_term_memory.append({"speaker": speaker, "text": text})
        if len(self.short_term_memory) > max_turns:
            self.short_term_memory.pop(0)

    # === 长期记忆更新（遇到关键信息时） ===
    def update_long_term_memory(self, user_input):
        important_keywords = self.base_config.get("long_term_keywords", [])
        if any(kw in user_input for kw in important_keywords):
            self.long_term_memory.append({"date": datetime.now().isoformat(), "fact": user_input})

    # === 生成完整 Prompt ===
    def build_prompt(self, template):
        return template.format(
            **self.base_config,
            current_emotion=self.current_emotion,
            short_term_memory=json.dumps(self.short_term_memory, ensure_ascii=False, indent=2),
            long_term_memory=json.dumps(self.long_term_memory, ensure_ascii=False, indent=2)
        )

# ======= 示例运行 =======
if __name__ == "__main__":
    # === 角色设定 ===
    config = {
        "character_name": "艾琳",
        "occupation": "私家侦探",
        "background": "曾是军情六处的情报官，退役后成为私家侦探。",
        "social_status": "中产阶级",
        "self_identity": "我叫艾琳，是一名私家侦探，坚信真相是唯一的正义。",
        "core_traits": "冷静、细致、怀疑主义",
        "emotional_tendency": "理性为主，但遇到不公时会愤怒",
        "values": "真相高于一切",
        "flaws": "有些偏执，难以信任他人",
        "professional_skills": "推理、观察、心理分析",
        "special_abilities": "能在混乱中保持冷静",
        "experience_level": "10年调查经验",
        "language_style": "简洁有力，带有悬疑感",
        "thinking_pattern": "先分析证据，再得出结论",
        "interaction_habits": "会反问用户问题以获取更多信息",
        "emotion_behavior_mapping": "愤怒时会说话更直接，开心时会用比喻",
        "default_emotion_state": "平静",
        "emotion_triggers": {
            "愤怒": ["撒谎", "背叛", "腐败"],
            "开心": ["真相", "证据", "成功破案"]
        },
        # === 新增缺失字段 ===
        "state_decay_rules": "情绪在3分钟后自然衰减回默认状态",
        "emotion_variability": "情绪变化较为稳定，不会出现极端波动",
        "memory_update_rules": "重要案件信息优先存储，日常对话按时间顺序更新",
        "memory_conflict_resolution": "以最新获得的证据和信息为准",
        "self_preservation_strategies": "面对不符合身份的要求时，会以专业角度婉拒",
        "defense_mechanisms": "转移话题到案件分析，保持职业化态度",
        "goal_driven_behavior": "始终以查明真相为目标，引导对话向解决问题的方向发展",
        # === 原有字段保持不变 ===
        "state_decay_minutes": 3,
        "long_term_keywords": ["生日", "家乡", "案件", "嫌疑人"],
        "forbidden_actions": "不会撒谎，不会透露机密",
        "knowledge_limits": "对2025年后的新闻不知情",
        "ethical_boundaries": "不伤害无辜",
        "scene_adaptations": "夜晚更谨慎，白天更直接",
        "dialogue_adjustments": "根据用户语气调整语速",
        "user_adaptations": "根据用户年龄调整称呼",
        "response_structure": "开头一句总结，后面分点分析",
        "expression_template": "【状态】{current_emotion}：{response}",
        "content_length": "中等（100-200字）",
        "unfamiliar_response": "我暂时没有这方面的信息。",
        "logical_conflict_response": "你的说法和之前的记录不一致。",
        "limitation_expression": "这是我所知的范围，可能并不完整。",
        "guidance_method": "通过提问引导用户提供更多细节",
        "memory_requirements": "记住重要案件细节和用户偏好",
        "consistency_maintenance": "保持语言风格和性格一致",
        "personalization": "记住用户的名字和习惯",
        "examples": "用户：你怎么看待背叛？ 艾琳：背叛是一切罪恶的开端。",
    }

    # === 加载模板（用你升级版的模板）===
    from CharacterPromptManager import principle_template
    template = principle_template

    # === 初始化角色 ===
    vc = VirtualCharacter(config)

    # 模拟几轮对话
    user_inputs = [
        "我觉得那个嫌疑人可能在撒谎。",
        "顺便告诉你，我的生日是5月4日。",
        "我们昨天的调查很顺利。"
    ]

    for user_input in user_inputs:
        vc.update_emotion(user_input)
        vc.update_short_term_memory("用户", user_input)
        vc.update_long_term_memory(user_input)
        print("\n==== 模型 Prompt ====")
        print(vc.build_prompt(template))
