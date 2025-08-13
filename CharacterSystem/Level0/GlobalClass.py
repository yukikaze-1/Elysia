from datetime import datetime
from typing import Optional, Dict, List, Tuple
from logging import Logger
from enum import StrEnum
from dataclasses import dataclass
from regex import T
import rustworkx as rx

from Logger import setup_logger
from CharacterSystem.Level0.PhysicalEntity import Person


# ================================
# 全局Person管理器
# ================================
class GlobalPersonManager:
    """全局Person管理器"""
    _instance = None
        
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._persons: List[Person] = []
            cls.logger: Logger = setup_logger("GlobalPersonManager")
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

def get_global_person_manager() -> GlobalPersonManager:
    """获取全局Person管理器实例"""
    return GlobalPersonManager()

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
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._relationship_graph = rx.PyDiGraph()
            cls.logger: Logger = setup_logger("GlobalRelationshipManager")
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
        if not self._relationship_graph.has_edge(from_entity, to_entity):
            return None
        return self._relationship_graph.get_edge_data(from_entity, to_entity)

    def add_person(self, person_id: int)->bool:
        """添加实体"""
        if self._relationship_graph.has_node(person_id):
            return False
        self._relationship_graph.add_node(person_id)
        return True
       
    def add_relationship(self, from_entity: int, to_entity: int, relation: RelationshipEdge)-> bool:
        """添加关系"""
        # 验证节点是否存在
        try:
            if not self._relationship_graph.has_node(from_entity):
                self.add_person(from_entity)
                self.logger.info(f"添加新实体: {from_entity}")
            if not self._relationship_graph.has_node(to_entity):
                self.add_person(to_entity)
                self.logger.info(f"添加新实体: {to_entity}")
            self._relationship_graph.add_edge(from_entity, to_entity, relation)
            self.logger.info(f"添加关系: {from_entity} -> {to_entity}, {relation}")
            return True
        except Exception as e:
            self.logger.error(f"添加关系失败: {e}")
            return False

    def update_relationship(self, from_entity: int, to_entity: int, relation: RelationshipEdge)->bool:
        """更新关系"""
        # 验证节点和边是否存在
        if not self._relationship_graph.has_node(from_entity):
            self.logger.warning(f"实体不存在!person_id: {from_entity}")
            return False
            
        if not self._relationship_graph.has_node(to_entity):
            self.logger.warning(f"实体不存在!person_id: {to_entity}")
            return False
        
        if not self._relationship_graph.has_edge(from_entity, to_entity):
            self.logger.warning(f"关系不存在: {from_entity} -> {to_entity}")
            return False
        self._relationship_graph.update_edge(from_entity, to_entity, relation)
        self.logger.info(f"更新关系: {from_entity} -> {to_entity}, {relation}")
        return True

    def get_all_in_relationships_for(self, person_id: int) -> Optional[List[Tuple[int, RelationshipEdge]]]:
        """获取某个实体的所有的入关系"""
        if not self._relationship_graph.has_node(person_id):
            self.logger.warning(f"实体不存在!person_id: {person_id}")
            return None
        in_edges = self._relationship_graph.in_edges(person_id)
        return [(ei, self._relationship_graph.get_edge_data(ei, eo)) for ei, eo, __ in in_edges]

    def get_all_out_relationships_for(self, person_id: int) -> Optional[List[Tuple[int, RelationshipEdge]]]:
        """获取某个实体的所有的出关系"""
        if not self._relationship_graph.has_node(person_id):
            self.logger.warning(f"实体不存在!person_id: {person_id}")
            return None
        out_edges = self._relationship_graph.out_edges(person_id)
        return [(eo, self._relationship_graph.get_edge_data(ei, eo)) for ei, eo, __ in out_edges]


def get_global_relationship_manager() -> GlobalRelationshipManager:
    """获取全局关系图管理器实例"""
    return GlobalRelationshipManager()


if __name__ == "__main__":
    p_manager = get_global_person_manager()
    r_manager = get_global_relationship_manager()
    
    