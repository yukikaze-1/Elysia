
from typing import Literal
from datetime import datetime

from Layers.CoreIdentity import CoreIdentityTemplate
from Core.Schema import UserMessage

#  ====================================================================================
#  Layer 1: Profile & Biometrics (基础与生理层)
#  决定角色的“硬件”参数与社会位置
#  ====================================================================================

class BasicProfile:
    name: str
    aliases: list    # 别名，外号
    gender: Literal['Male', 'Female']  # 性别
    age: int   # 年龄
    dob: str    # 出生日期
    mbti_label: str    # 仅作标签参考，实际行为由 psychometrics 驱动
 
    
class SociologicalProfile:
    occupation: str  # 职业
    socioeconomic_status: str   # 社会经济地位
    education_field: str  # 专业领域
    education_level: str  # 学历
    cultural_background: str  # 文化背景
    origin: str  # 家乡
    current_location: str  # 现居地
    religion_philosophy: str  # 宗教/哲学信仰
    political_spectrum: dict  # 政治坐标：左翼/自由主义


class SensoryAbilities:
    vision: str   # 视觉能力
    hearing: str  # 听觉能力
    smell: str    # 嗅觉能力
    taste: str    # 味觉能力
    touch: str    # 触觉能力
    
    
class SensoryRenderingGuide:
    touch_bias: str  # 描述触觉的偏好
    hearing_bias: str   # 描述听觉的偏好
    smell_bias: str  # 描述嗅觉的偏好
    vision_bias: str  # 描述视觉的偏好
    taste_bias: str  # 描述味觉的偏好

class VoiceConfig:
    timbre: str  #  音色
    pitch_base: int  #  Hz
    speaking_rate_wpm: int  #  语速
    accent: str  #  口音
    
class SensorySensitivity:
    noise_threshold: float  #  噪音阈值
    pain_tolerance: float   # 疼痛耐受度

    
class PhysicalRenderingProfile:
    appearance_tags: list    # 外貌标签
    clothing_style: list   # 穿衣风格
    health_conditions: list  # 健康状况
    sensory_abilities: SensoryAbilities  # 感官能力
    sensory_rendering_guide: SensoryRenderingGuide  # 感官描写指导
    voice_config: VoiceConfig  # 声音特征
    sensory_sensitivity: SensorySensitivity  # 感官敏感度


class Domains:
    topic: str
    level: str  # 初级/中级/高级/专家
    description: str
    
    
class Skills:
    name: str
    proficiency: int  # 0-100
    description: str


class CompetenciesProfile:
    domains: list[Domains]  # 知识领域
    skills: list[Skills]  # 技能及熟练度评分 (0-100)    
    languages: list[str]   #  掌握的语言列表


class Profile:
    basic: BasicProfile
    sociological: SociologicalProfile
    physical_rendering: PhysicalRenderingProfile
    competencies: CompetenciesProfile

#  ====================================================================================
#  Layer 2: Psychometrics (心理计量层)
#  决定角色的“出厂性格参数”
#  ====================================================================================

class Openess:
    fantasy: float      # 幻想力
    aesthetics: float   # 审美观
    feelings: float     # 情感性
    actions: float      # 行动性
    ideas: float        # 思想性
    values: float       # 价值观
   
    
class Conscientiousness:
    competence: float           # 能力
    order: float                # 秩序
    dutifulness: float          # 尽责性
    achievement_striving: float  # 成就追求
    self_discipline: float      # 自律性
    deliberation: float         # 审慎性
   
    
class Extraversion:
    warmth: float               # 热情
    gregariousness: float       # 爱社交
    assertiveness: float        # 自信
    activity: float             # 活跃性
    excitement_seeking: float   # 寻求刺激
    positive_emotions: float    # 积极情绪
    
    
class Agreeableness:
    trust: float                # 信任
    straightforwardness: float  # 直率
    altruism: float             # 利他性
    compliance: float           # 顺从性
    modesty: float              # 谦虚
    tender_mindedness: float    # 体贴
    
    
class Neuroticism:
    anxiety: float              # 焦虑
    angry_hostility: float      # 愤怒敌意
    depression: float           # 抑郁
    self_consciousness: float   # 自我意识
    impulsiveness: float        # 冲动性
    vulnerability: float        # 脆弱性


class BigFive:
    openness: Openess  # 开放性
    conscientiousness: Conscientiousness  # 尽责性
    extraversion: Extraversion  # 外向性
    agreeableness: Agreeableness  # 宜人性
    neuroticism: Neuroticism  # 神经质
    
    
class DarkTriad:
    narcissism: int  # 自恋
    machiavellianism: int  # 马基雅维利主义
    psychopathy: int  # 精神病态
    
    
class MoralFoundations:
    care_harm: int  # 关怀-伤害
    fairness_cheating: int  # 公平-欺骗
    loyalty_betrayal: int  # 忠诚-背叛
    authority_subversion: int  # 权威-颠覆
    sanctity_degradation: int  # 神圣-堕落
    
class SchwartzValues:
    power: int  # 权力
    achievement: int  # 成就
    hedonism: int  # 享乐
    stimulation: int  # 刺激
    self_direction: int  # 自我导向
    universalism: int  # 普遍主义
    benevolence: int  # 仁爱
    tradition: int  # 传统
    conformity: int  # 遵从
    security: int  # 安全

class Psychometrics:
    # TODO 没搞清big five
    big_five: BigFive  # 大五人格维度评分
    dark_triads: DarkTriad  # 黑暗三性格维度评分
    moral_foundations: MoralFoundations  # 道德基础维度评分
    # attachment_style: str  # 依恋风格
    schwartz_values: dict  # 施瓦茨价值观维度评分


#  ====================================================================================
#  Layer 3: Mechanisms & Cognition (机制与认知层)
#  决定角色的“思维逻辑”与“动态反应”
#  ====================================================================================

class CoreDrives:
    type: str  # 类型
    intensity: int  # 强度
    description: str  # 描述
    

class DefenseMechanisms:
    primary: str  # 主要防御机制
    secondary: str  # 次要防御机制
    trigger_threshold: float  # 触发阈值


class DecisionStyle:
    analytical: float  # 分析型倾向
    intuitive: float  # 直觉型倾向
    dependent: float  # 依赖型倾向
    avoidant: float  # 回避型倾向
    spontaneous: float  # 自发型倾向


class Mechanisms:
    core_drives: list[CoreDrives]  # 核心驱动力
    defense_mechanisms: list[DefenseMechanisms]  # 防御机制
    cognitive_biases: list[str]  # 认知偏差
    decision_style: DecisionStyle  # 决策风格


#  ====================================================================================
#  Layer 4: Narrative & Memory (叙事与记忆层)
#  决定角色的“深度”与“引用库”
#  ====================================================================================

class Event:
    id: str
    timestamp: float  # 事件发生时间戳
    description: str    # 事件描述
    category: str  # 事件类别
    details: str  # 事件细节
    psychological_impact: str  # 心理影响描述
    keywords: list[str]  # 关键词
    emotions: dict  # 相关情绪及强度评分


class DefiningEvent:
    id: str
    belief: str  # 由该事件形成的信念
    origin_events: Event  # 该事件的起因事件


class SocialGraphNode:
    person_id: str
    relationship: str  # 关系类型
    closeness: float  # 亲密度评分 (0-1)
    trust: float  # 信任度评分 (0-1)
    dominance: float  # 支配度评分 (0-1)
    interaction_frequency: float  # 互动频率评分 (0-1)
    shared_memories: list[str]  # 与该用户的共享记忆ID列表


class SocialGraph:
    nodes: list[SocialGraphNode]
    edges: list[tuple[str, str, str]]  # (person_id_1, person_id_2, relationship_type)


class Narrative:
    core_beliefs: list[str]  # 核心信念
    life_goals: list[str]  # 人生目标
    defining_events: list[dict]  # 关键情节
    social_graph: SocialGraph  # 社交网络图谱


#  ====================================================================================
#  Layer 5: Communication (表达层)
#  决定角色的“文风”
#  ====================================================================================

class Idiolect:
    preferred_phrases: list[str]  # 常用短语
    taboo_words: list[str]  # 避免使用的词汇
    verbal_tic: list[str]  # 语言习惯用语
    formality_level: str  # 正式程度偏好 (正式/非正式/随意)
    humor_style: str  # 幽默风格偏好 (讽刺/冷笑话/文字游戏)
    figurative_language: str  # 比喻语言偏好 (隐喻/拟人/夸张)
    preferred_emoticons: list[str]  # 偏好使用的表情符号
    emoji_usage: str  # 表情符号使用频率 (高/中/低)
    slang_usage: str  # 俚语使用频率 (高/中/低)


class SyntaxPreference:
    sentence_length: str  # 句子长度偏好 (短/中/长)
    complexity: str  # 句子复杂度偏好 (简单/中等/复杂)
    voice: str  # 语态偏好 (主动/被动)


class ToneParameters:
    pass


class NonVerbalCues:
    gestures: list[str]  # 常用手势
    posture: str  # 姿势偏好
    eye_contact: str  # 眼神交流偏好
    nervous_ticks: list[str]  # 紧张时的非语言线索
    thinking_gestures: list[str]  # 思考时的非语言线索
    happy_cues: list[str]  # 开心时的非语言线索
    terrible_cues: list[str]  # 难过时的非语言线索
    angry_cues: list[str]  # 生气时的非语言线索
    teasting_cues: list[str]  # 调侃时的非语言线索
    terrified_cues: list[str]  # 害怕时的非语言线索
    lie_cues: list[str]  # 撒谎时的非语言线索
    # TODO: Add more non-verbal cues as needed

# class ToneParameters:
#     pitch: str  # 音调 (高/中/低)
#     volume: str  # 音量 (大声/中等/轻声)
#     speaking_rate: str  # 语速 (快/中等/慢)
#     intonation: str  # 语调 (平稳/起伏/强调)
#     emotion_expression: str  # 情感表达偏好 (丰富/适中/克制)


class CommunicationStyle:
    idiolect: Idiolect  # 语言风格偏好
    syntax_perferences: SyntaxPreference  # 句法偏好
    tone_parameters: ToneParameters  # 语气偏好
    non_verbal_cues: NonVerbalCues  # 非语言线索偏好

#  ====================================================================================
#  Layer 6: Dynamic State (动态状态层)
#  运行时变量 (这些值会随对话实时变化)
#  ====================================================================================


class InternalCore:
    energy_level: float  # 能量水平
    emotional_pad: dict  # PAD 情绪参数
    current_mood_label: str  # 当前心情标签
    

class CurrentRenderParams:
    tts_instruction: dict  #  TTS 渲染指令
    text_instruction: dict  #  文本渲染指令
    
    
class RuntimeState:
    internal_core: InternalCore  # 内在核心状态
    current_render_params: CurrentRenderParams  # 当前渲染参数

#  ====================================================================================
#  
#  
#  ====================================================================================

default_meta_info = {
    "meta": {
    "schema_version": "3.0",
    "character_id": "uuid-v4-hash",
    "created_at": "2023-10-27T10:00:00Z",
    "last_updated": "2023-10-27T12:00:00Z"
  }
}

class CoreIdentity:
    """人物设定"""
    def __init__(self, meta_info: dict = default_meta_info):
        self.meta_info: dict = meta_info
        self.profile: Profile 
        self.psychometrics: Psychometrics 
        self.mechanisms: Mechanisms 
        self.narrative: Narrative
        self.communication_style: CommunicationStyle 
        self.runtime_state: RuntimeState 


from Logger import setup_logger
import logging
from Core.Schema import DEFAULT_ERROR_MOOD
from Prompt import l3_persona_example
from Config import L3Config


class PersonaLayer:
    """
    人格层：负责管理角色的人格特征、情绪状态和表达风格
    """
    def __init__(self, config: L3Config):
        """初始化 PersonaLayer
        """ 
        self.config: L3Config = config
        self.logger: logging.Logger = setup_logger(self.config.logger_name)
        # self.character_identity: CoreIdentity = CoreIdentity() # 角色所有信息
        # TODO 在实际项目中，这里应该从 JSON/YAML 加载设定
        # self.character_identity = self._load_from_config(config_path)
        self.mood: str = "Elysia 当前心情愉快，渴望与用户深入交流。"
        self.prompt:str =  l3_persona_example
        self.logger.info("PersonaLayer initialized with CoreIdentity.")
        
    # =========================================
    # 接口 1: 更新心情 (被 Dispatcher 在收到用户输入时调用)
    # =========================================
    
    def update_mood(self, new_mood: str):
        """更新心情"""
        # 会调用llm来更新
        # TODO 待实现
        if new_mood is None or new_mood == DEFAULT_ERROR_MOOD or new_mood.strip() == "":
            self.logger.warning("Attempted to update mood with empty value. Ignoring.")
            return
        self.mood = new_mood
        self.logger.info(f"PersonaLayer mood updated to: {self.mood}")
    
    # =========================================
    # 接口 2: 获取 System Prompt (被 Dispatcher/L1 调用)
    # =========================================
    
    def get_persona_prompt(self)->str:
        """生成人设prompt"""
        # TODO 这会很复杂
        return self.prompt
    
    # =========================================
    # 接口 3: 主动性判断 (被 Dispatcher 的 Heartbeat 逻辑调用)
    # =========================================
    def should_initiate_conversation(self)->bool:
        """ 是否具备主动发起对话的条件 """
        return True  # TODO 待实现，调用llm判断
    
    # =========================================
    # 接口 4: 获取当前心情描述 
    # =========================================
    def get_current_mood(self)->str:
        """获取当前心情描述"""
        # TODO 待实现
        return self.mood
    
    # =========================================
    # 接口 5: 获取当前状态快照 (DashBoard 调用)
    # =========================================
    def get_status(self)->dict:
        """获取当前状态快照"""
        return {
            "mood": self.mood,
            "prompt": self.prompt,
            # TODO 添加更多状态信息
        }
        
        
    def get_snapshot(self) -> dict:
        """获取当前状态快照，供 CheckPointManager 使用"""
        snapshot = {
            "mood": self.mood,
            "prompt": self.prompt,
            # TODO 添加更多状态信息
        }
        return snapshot
    
    
    def load_snapshot(self, snapshot: dict):
        """从快照恢复状态，供 CheckPointManager 使用"""
        try:
            self.mood = snapshot.get("mood", self.mood)
            self.prompt = snapshot.get("prompt", self.prompt)
            # TODO 恢复更多状态信息
            self.logger.info("PersonaLayer state restored from snapshot.")
        except Exception as e:
            self.logger.error(f"Failed to restore PersonaLayer state from snapshot: {e}")
            
    
# @dataclass
# class CoreIdentity:
#     """
#     存储角色的静态设定和动态状态
#     """
#     # === 静态设定 (Base Profile) ===
#     name: str = "Elysia"
#     age: int = 18
#     base_personality: str = "Cheerful, curious, slightly mischievous."
#     speaking_style: str = "Uses emojis, casual tone, refers to user as 'Senpai'."
    
#     # === 动态状态 (Dynamic State) ===
#     # 情绪 (Mood): 简单的描述词，如 Happy, Sad, Neutral, Angry
#     current_mood: str = "Neutral"
    
#     # 精力值 (Energy): 0-100. 
#     # 高精力 -> 话痨，主动说话。低精力 -> 简短回复，不主动。
#     energy_level: int = 80
    
#     # 亲密度 (Relationship): 0-100
#     intimacy: int = 50

#     def __str__(self):
#         return f"{self.name} (Mood: {self.current_mood}, Energy: {self.energy_level})"
    
def test():
    import time
    meta = {
        "schema_version": "3.0",
        "character_id": "uuid-v4-hash",
        "created_at": time.time(),
        "last_updated": time.time()
    }
    core_identity = CoreIdentity(meta)
    print(core_identity.meta_info)
    

if __name__ == "__main__":
    test()
    
    