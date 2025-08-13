"""
    社交环境负责  “关系、氛围、互动模式”  等主观/抽象层
"""
from dataclasses import dataclass
from enum import Enum, IntEnum, StrEnum
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime
from logging import Logger
import rustworkx as rx
import copy

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
        self._persons.append(person)
        return person_id
    
    def get_person(self, person_id: int) -> Optional[Person]:
        """通过ID获取Person"""
        if 0 <= person_id < len(self._persons):
            return self._persons[person_id]
        return None

# ================================
# 关系图Node和Edge定义
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
    # from_entity: int    # 实体id(就是Person中的person_id)
    # to_entity: int      # 实体id
    relation_type: RelationType
    intimacy_level: float  # 0-1 亲密度
    trust_level: float     # 0-1 信任度
    interaction_frequency: int  # 交互频率
    last_interaction: Optional[datetime] = None

# ================================
# 全局关系图管理器
# ================================
class GlobalRelationshipManager:
    """全局关系图管理器 - 单例模式"""
    _instance = None
    _relationship_graph: rx.PyDiGraph = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._relationship_graph = rx.PyDiGraph()
        return cls._instance
    
    @property
    def graph(self) -> rx.PyDiGraph:
        """获取关系图"""
        return self._relationship_graph
    
    def sub_view(self, nodes: List[int]):
        """获取子图"""
        return self._relationship_graph.subgraph(nodes)
    
    def get_relationship(self, from_entity: int, to_entity: int) -> Optional[RelationshipEdge]:
        """获取关系"""
        return self._relationship_graph.get_edge_data(from_entity, to_entity)

    def add_person(self, person_id: int):
        """添加实体"""
        self._relationship_graph.add_node(person_id)
       
    def add_relationship(self, from_entity: int, to_entity: int, relation: RelationshipEdge):
        """添加关系"""
        # 验证节点是否存在
        if not self._relationship_graph.has_node(from_entity):
            self.add_person(from_entity)
        if not self._relationship_graph.has_node(to_entity):
            self.add_person(to_entity)
        self._relationship_graph.add_edge(from_entity, to_entity, relation)

    def update_relationship(self, from_entity: int, to_entity: int, relation: RelationshipEdge):
        """更新关系"""
        self._relationship_graph.update_edge(from_entity, to_entity, relation)
    
    def get_all_in_relationships_for(self, person_id: int) -> List[Tuple[int, RelationshipEdge]]:
        """获取某个实体的所有的入关系"""
        in_edges = self._relationship_graph.in_edges(person_id)
        return [(ei, self._relationship_graph.get_edge_data(ei, eo)) for ei, eo, __ in in_edges]
    
    def get_all_out_relationships_for(self, person_id: int) -> List[Tuple[int, RelationshipEdge]]:
        """获取某个实体的所有的出关系"""
        out_edges = self._relationship_graph.out_edges(person_id)
        return [(eo, self._relationship_graph.get_edge_data(ei, eo)) for ei, eo, __ in out_edges]


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

    def update_scene(self, new_scene: SocialSceneType):
        """更新社交场景"""
        self.scene = new_scene

    def update_atmosphere(self, new_atmosphere: SocialAtmosphereType):
        """更新社交氛围"""
        self.atmosphere = new_atmosphere


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

    def update_emotion(self, new_emotion: SocialEmotionState):
        """更新社交情绪状态"""
        self.emotion = new_emotion


class InteractionType(StrEnum):
    """交互类型"""
    COMMUNICATION = "交流"
    COLLABORATION = "协作"
    OBSERVATION = "观察"
    USE = "使用"


class InteractionObject:
    """交互对象"""
    def __init__(self, target: int, interaction_type: InteractionType) -> None:
        self.target: int = target  # 交互对象的目标的实体ID，可以是人或物品
        self.interaction_type: InteractionType = interaction_type  # 交互对象的交互类型
        self.last_interaction_time: Optional[datetime] = None  # 上次交互时间

    def update_interaction(self,  new_interaction_type: InteractionType):
        """更新交互对象的交互类型"""
        self.interaction_type = new_interaction_type
        self.update_last_interaction_time(datetime.now())

    def update_last_interaction_time(self, new_time: datetime):
        """更新交互对象的上次交互时间"""
        self.last_interaction_time = new_time


class SocialEnvironment:
    """社交环境"""
    def __init__(self):
        # 基本信息
        self.me_id: int = 0  # 我(Elysia)是谁
        self.relationship_graph =  GlobalRelationshipManager() # 全局人员关系图引用
        self.relationship_graph_sub_view = self.relationship_graph.sub_view([self.me_id])  # 关系图的子视图，包含我(Elysia)和相关人员[一开始只有我(Elysia)]
        self.persons_manager = GlobalPersonManager() # 全局人员管理
        self.roles: List[str] = ["学生"]  # 我(Elysia)的角色列表，例如：学生/老师/朋友/家人等

        # 环境感知数据
        self.people_present: List[int] = []     # 存放在场人员的ID
        self.items_present: List[int] = []       # 存放在场物品的ID
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

    
    def update_people_present_add(self, new_people: List[int]):
        """更新在场人员并同步关系图子视图"""
        # 去重处理
        unique_new_people = [p for p in new_people if p not in self.people_present]
        self.people_present.extend(unique_new_people)
        
        # 更新子视图包含所有相关人员
        all_relevant_people = list(set([self.me_id] + self.people_present))
        self.relationship_graph_sub_view = self.relationship_graph.sub_view(all_relevant_people)
        
    def update_people_present_remove(self, people: List[int]):
        """更新在场人员并同步关系图子视图"""
        self.people_present = [p for p in self.people_present if p not in people]
        # 更新子视图包含所有相关人员
        all_relevant_people = [self.me_id] + self.people_present
        self.relationship_graph_sub_view = self.relationship_graph.sub_view(all_relevant_people)
        
    def add_interaction_target(self, target_id: int, interaction_type: InteractionType):
        """添加交互目标"""
        # 检查是否已存在该目标
        for obj in self.interaction_target:
            if obj.target == target_id:
                # 如果已存在，更新交互类型
                obj.update_interaction(interaction_type)
                return
        
        # 如果不存在，创建新的交互对象
        interaction_obj = InteractionObject(target=target_id, interaction_type=interaction_type)
        interaction_obj.last_interaction_time = datetime.now()
        self.interaction_target.append(interaction_obj)

    def remove_interaction_target(self, target_id: int):
        """移除交互目标"""
        self.interaction_target = [obj for obj in self.interaction_target if obj.target != target_id]

    def infer_social_context(self):
        """基于当前状态推断社交场景"""
        # TODO 后面再用llm来生成
        pass
    
    def validate_social_state(self) -> List[str]:
        """验证当前社交状态的合理性"""
        warnings = []
        
        # 检查是否有人员但没有交互
        if len(self.people_present) > 0 and len(self.interaction_target) == 0:
            warnings.append("有人在场但没有交互目标")
        
        # 检查关系图子图中是否包含所有在场人员
        for person_id in self.people_present:
            if not self.relationship_graph_sub_view.has_node(person_id):
                warnings.append(f"人员 {person_id} 不在关系图中")
        
        return warnings
    
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
    
    def get_social_statistics(self) -> Dict:
        """获取当前社交环境的统计信息"""
        return {
            "total_people": len(self.people_present),
            "my_relationships": len(self.relationship_graph.get_all_out_relationships_for(self.me_id)),
            "scene_type": self.social_scene.scene,
            "atmosphere": self.social_scene.atmosphere,
            "emotion": self.emotion_states.emotion
        }
        
    def build_social_context_prompt(self) -> str:
        """为上层生成社交上下文描述"""
        return f"""
        ## 当前社交环境
        - 场景类型: {self.social_scene.scene}
        - 社交氛围: {self.social_scene.atmosphere}  
        - 在场人数: {len(self.people_present)}
        - 当前话题: {self.conversation_topic or '无特定话题'}
        - 主要活动: {self.theme_activity or '日常交流'}
        - 我的角色: {', '.join(self.roles) or '无特定角色'}
        - 总的描述:{self.description or '无特定描述'}
        """

    def store_current_social_environment(self):
        """将当前社交场景的一切(快照)存档"""
        # 需要深拷贝，否则修改当前状态会影响历史状态
        self.previous_state = copy.deepcopy(self)
        # 避免无限递归，清除previous_state的previous_state
        if self.previous_state:
            self.previous_state.previous_state = None


if __name__ == "__main__":
    serv = SocialEnvironment()
    print("Current")
    print(serv.build_social_context_prompt())
    serv.store_current_social_environment()
    print("Previous:")
    print(serv.previous_state.build_social_context_prompt()if serv.previous_state else "无历史记录")