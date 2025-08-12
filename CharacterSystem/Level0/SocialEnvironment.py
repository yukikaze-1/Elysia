"""
    社交环境负责  “关系、氛围、互动模式”  等主观/抽象层
"""
from dataclasses import dataclass
from enum import Enum, IntEnum, StrEnum
from re import L
from typing import List, Dict, Optional, Set
from datetime import datetime
from logging import Logger

from CharacterSystem.Level0.PhysicalEntity import Item, Person

from Logger import setup_logger

# ================================
# 全局Person管理器
# ================================
class GlobalPersonManager:
    """全局Person管理器"""
    _instance = None
    _persons: List[Person | None] = []
    logger: Logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._persons = []
            cls.logger = setup_logger("GlobalPersonManager")
        return cls._instance
    
    def add_person(self, person: Person) -> int:
        """添加Person并返回ID"""
        person_id = len(self._persons)
        person.person_id = person_id
        self._persons[person_id] = person
        return person_id
    
    def get_person(self, person_id: int) -> Optional[Person]:
        """通过ID获取Person"""
        return self._persons[person_id] if 0 <= person_id < len(self._persons) else None

    def remove_person(self, person_id: int):
        """移除Person（标记为已删除，保持索引稳定）"""
        if 0 <= person_id < len(self._persons):
            if self._persons[person_id] is not None:
                self._persons[person_id] = None  # 标记为已删除而不是真正删除
                self.logger.info(f"Person {person_id} removed")
            else:
                self.logger.warning(f"Person {person_id} already removed")
        else:
            self.logger.error("Person ID out of range")
    
    def get_all_active_persons(self) -> List[Person]:
        """获取所有活跃的Person（未被删除的）"""
        return [person for person in self._persons if person is not None]

# 全局Person管理器实例
global_person_manager = GlobalPersonManager()

# ================================
# 关系图
# ================================

class RelationType(StrEnum):
    """关系类型"""
    FRIEND = "朋友"
    FAMILY = "家人"
    COLLEAGUE = "同事"
    STRANGER = "陌生人"
    ACQUAINTANCE = "熟人"
    PARTNER = "伴侣"
    
@dataclass
class RelationshipEdge:
    """关系边，描述两个实体之间的关系"""
    from_entity: int    # 实体id(就是Person中的person_id)
    to_entity: int      # 实体id
    relation_type: RelationType
    intimacy_level: float  # 0-1 亲密度
    trust_level: float     # 0-1 信任度
    interaction_frequency: int  # 交互频率
    last_interaction: Optional[datetime] = None

class RelationshipGraph:
    """关系图"""
    def __init__(self):
        self.edges: Dict[tuple, RelationshipEdge] = {}  # 关系边
        self.entities: Set[int] = set() # 实体（人）集合
    
    def add_entity(self, person_id: int):
        """添加实体"""
        self.entities.add(person_id)

    def add_relationship(self, from_entity: int, to_entity: int, 
                        relation_type: RelationType, **kwargs):
        """添加关系"""
        edge_key = (from_entity, to_entity)
        self.edges[edge_key] = RelationshipEdge(
            from_entity, to_entity, relation_type, **kwargs
        )
        self.entities.update([from_entity, to_entity])

    def update_relationship(self, from_entity: int, to_entity: int, **kwargs):
        """更新关系"""
        edge = self.edges.get((from_entity, to_entity))
        if edge:
            for key, value in kwargs.items():
                setattr(edge, key, value)

    def get_relationship(self, from_entity: int, to_entity: int) -> Optional[RelationshipEdge]:
        """获取关系"""
        return self.edges.get((from_entity, to_entity))
    
    def get_all_relationships_for(self, entity: int) -> List[RelationshipEdge]:
        """获取某个实体的所有关系"""
        return [edge for edge in self.edges.values() 
                if edge.from_entity == entity or edge.to_entity == entity]
        
        
# ================================
# 全局关系图管理器
# ================================
class GlobalRelationshipManager:
    """全局关系图管理器 - 单例模式"""
    _instance = None
    _relationship_graph: RelationshipGraph = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._relationship_graph = RelationshipGraph()
        return cls._instance
    
    @property
    def graph(self) -> RelationshipGraph:
        return self._relationship_graph
    
    def get_relationship(self, from_entity: int, to_entity: int) -> Optional[RelationshipEdge]:
        """获取关系"""
        return self._relationship_graph.get_relationship(from_entity, to_entity)
    
    def add_relationship(self, from_entity: int, to_entity: int, relation_type: RelationType, **kwargs):
        """添加关系"""
        self._relationship_graph.add_relationship(from_entity, to_entity, relation_type, **kwargs)

# 全局关系图实例
global_relationship_manager = GlobalRelationshipManager()
        
# ================================
# 关系人
# ================================        
class Relations:
    """
    关系人，通过ID引用Person实体，并管理与该人的关系信息
    """
    def __init__(self, person_id: int, my_id: int = 0):
        self.person_id: int = person_id  # 引用的Person ID
        self.my_id: int = my_id  # 我的ID，用于查询关系
        
        # 引用全局关系图
        self._relationship_manager = global_relationship_manager
        # 引用全局人员管理器
        self._persons_manager = global_person_manager
    
    @property
    def person(self) -> Optional[Person]:
        """通过ID获取Person实体"""
        return self._persons_manager.get_person(self.person_id)

    @property
    def relationship_with_me(self) -> Optional[RelationshipEdge]:
        """获取与我的关系"""
        return self._relationship_manager.get_relationship(self.my_id, self.person_id)
    
    def update_relationship_with_me(self, relation_type: RelationType, **kwargs):
        """更新与我的关系"""
        self._relationship_manager.add_relationship(
            self.my_id, self.person_id, relation_type, **kwargs
        )
    
    def get_relationship_with(self, other_person_id: int) -> Optional[RelationshipEdge]:
        """获取与其他人的关系"""
        return self._relationship_manager.get_relationship(self.person_id, other_person_id)
    

class SocialSceneType(StrEnum):
    """社交场景类型"""
    PRIVATE = "私人空间"
    PUBLIC= "公共场所"
    VIRTUAL= "虚拟环境"

class SocialAtmosphereType(StrEnum):
    """社交氛围类型"""
    CASUAL = "随意"
    FORMAL = "正式"
    HALF_FORMAL = "半正式"
    INTIMATE = "亲密"

class SocialScene:
    """
    社交场合
    描述社交场景的类型和氛围
    """
    def __init__(self) -> None:
        self.scene: SocialSceneType = SocialSceneType.PRIVATE   # 当前场景，私人/半私人/公共or其他
        self.atmosphere: SocialAtmosphereType = SocialAtmosphereType.CASUAL # 当前社交场景的氛围, 正式/半正式/轻松/亲密
        

class SocialEmotionState(StrEnum):
    """社交情绪状态"""
    RELAXED = "放松"
    ENGAGED = "投入"
    ANXIOUS = "焦虑"
    EXCITED = "兴奋"
    BORED = "无聊"
    FRUSTRATED = "沮丧"
    TERRIFIED = "恐惧"
    CONFUSED = "困惑"
    SCARED = "害怕"

class SocialEmotionStates:
    """社交情绪状态"""
    def __init__(self) -> None:
        self.emotion: SocialEmotionState = SocialEmotionState.RELAXED
       
class InteractionType(StrEnum):
    """交互类型"""
    COMMUNICATION = "交流"
    COLLABORATION = "协作"
    OBSERVATION = "观察"
    USE = "使用"

class InteractionObject:
    """交互对象"""
    def __init__(self) -> None:
        self.target: int # 交互对象的目标的实体ID，可以是人或物品
        self.interaction_type: InteractionType = InteractionType.COMMUNICATION  # 交互对象的交互类型
        self.last_interaction_time: Optional[datetime] = None   # 上次交互时间


class SocialEnvironment:
    """社交环境"""
    def __init__(self):
        # 基本信息
        self.me_id: int = 0  # 我(Elysia)是谁
        self.relationship_graph = RelationshipGraph()   # 全局人员关系图
        self.persons_manager = GlobalPersonManager()    # 全局人员管理
        
        # 环境感知数据
        self.people_present: List[Relations] = []
        self.items_present: List[Item] = []
        self.interaction_target: List[InteractionObject] = []   # 当前社交场景中，"我(Elysia)正在交互的对象"
        
        # 上下文信息
        self.theme_activity : str | None = None # 当前社交场景中的主要活动
        self.conversation_topic: str | None = None  # 当前社交场景中对话的话题
        
        # 环境变化检测 - 参考文档第0层设计
        self.previous_state: Optional['SocialEnvironment'] = None
        self.change_detection_enabled: bool = True
        
        # 社交氛围评估
        self.social_scene: SocialScene = SocialScene()
        self.emotion_states: SocialEmotionStates = SocialEmotionStates()
        
        self.description: str | None = "这是一个社交场景"   # 当前社交场景的总的描述

    
    def detect_social_changes(self) -> List[Dict]:
        """检测社交环境变化"""
        changes = []
        if self.previous_state:
            # 检测人员变化
            if len(self.people_present) != len(self.previous_state.people_present):
                changes.append({
                    "type": "people_count_change",
                    "impact_level": "medium",
                    "details": f"人数从{len(self.previous_state.people_present)}变为{len(self.people_present)}"
                })
            
            # 检测话题变化
            if self.conversation_topic != self.previous_state.conversation_topic:
                changes.append({
                    "type": "topic_change", 
                    "impact_level": "low",
                    "details": f"话题从'{self.previous_state.conversation_topic}'变为'{self.conversation_topic}'"
                })
        
        return changes
    
    def build_social_context_prompt(self) -> str:
        """为上层生成社交上下文描述"""
        return f"""
        ## 当前社交环境
        - 场景类型: {self.social_scene.scene}
        - 社交氛围: {self.social_scene.atmosphere}  
        - 在场人数: {len(self.people_present)}
        - 当前话题: {self.conversation_topic or '无特定话题'}
        - 主要活动: {self.theme_activity or '日常交流'}
        - 我的角色: {', '.join(self.relationship_graph.get)}
        """



