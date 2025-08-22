from datetime import datetime
from json import load
from typing import Optional, Dict, List, Tuple
from logging import Logger
from enum import StrEnum
from dataclasses import dataclass

from httpx import delete

from Logger import setup_logger
from CharacterSystem.Layer0.Entity.PersonEntity import Person

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
        id = len(self._persons)
        person.id = id
        self._persons.append(person)
        return id
    
    def get_person(self, id: int) -> Optional[Person]:
        """通过ID获取Person"""
        if 0 <= id < len(self._persons):
            return self._persons[id]
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
    from_entity: int    # 实体id(就是Person中的id)
    to_entity: int      # 实体id
    relation_type: RelationType
    intimacy_level: float  # 0-1 亲密度
    trust_level: float     # 0-1 信任度
    interaction_frequency: int  # 交互频率
    last_interaction: Optional[datetime] = None

# ================================
# 全局关系图管理器
# ================================
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv, find_dotenv

class GlobalRelationshipManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        load_dotenv(find_dotenv())
        self.url = os.getenv("NEO4J_URL","")
        self.auth = (os.getenv("NEO4J_USER",""), os.getenv("NEO4J_PASSWORD",""))
        self.driver = GraphDatabase.driver(self.url, auth=self.auth)
        
    def add_relationship(self, from_person: Person, to_person: Person, relationship: RelationshipEdge):
        """添加关系"""
        with self.driver.session() as session:
            session.run(
                "MERGE (a:Person {id: $from_id}) "
                "MERGE (b:Person {id: $to_id}) "
                "MERGE (a)-[r:RELATIONSHIP {type: $type, intimacy: $intimacy, trust: $trust, frequency: $frequency, last_interaction: $last_interaction}]->(b)",
                from_id=from_person.id,
                to_id=to_person.id,
                type=relationship.relation_type,
                intimacy=relationship.intimacy_level,
                trust=relationship.trust_level,
                frequency=relationship.interaction_frequency,
                last_interaction=relationship.last_interaction
            )
            
    def add_person(self, person: Person)->int:
        """添加Person节点"""
        with self.driver.session() as session:
            session.run(
                "MERGE (p:Person {id: $id, name: $name})",
                id=person.id,
                name=person.name
            )
            return person.id 
            
    def get_someones_relationships(self, person: Person) -> List[RelationshipEdge]:
        """获取某个人的所有关系"""
        with self.driver.session() as session:
            result = session.run(
                "MATCH (a:Person {id: $id})-[r:RELATIONSHIP]->(b:Person) "
                "RETURN b.id AS to_id, r.type AS relation_type, r.intimacy AS intimacy_level, "
                "r.trust AS trust_level, r.frequency AS interaction_frequency, r.last_interaction AS last_interaction",
                id=person.id
            )
            relationships = []
            for record in result:
                relationships.append(RelationshipEdge(
                    from_entity=person.id,
                    to_entity=record["to_id"],
                    relation_type=RelationType(record["relation_type"]),
                    intimacy_level=record["intimacy_level"],
                    trust_level=record["trust_level"],
                    interaction_frequency=record["interaction_frequency"],
                    last_interaction=record["last_interaction"]
                ))
            return relationships
            
    def delete_relationship(self, from_person: Person, to_person: Person):
        """删除两个人之间的关系"""
        with self.driver.session() as session:
            session.run(
                "MATCH (a:Person {id: $from_id})-[r:RELATIONSHIP]->(b:Person {id: $to_id}) "
                "DELETE r",
                from_id=from_person.id,
                to_id=to_person.id
            )
    
    def delete_person(self, person: Person):
        """删除Person节点及其所有关系"""
        with self.driver.session() as session:
            session.run(
                "MATCH (p:Person {id: $id}) "
                "DETACH DELETE p",
                id=person.id
            )
            # 清除全局管理器中的Person
            global_person_manager = get_global_person_manager()
            global_person_manager._persons = [p for p in global_person_manager._persons if p.id != person.id]
            
if __name__ == "__main__":
    """测试全局关系图管理器"""
    r_manager = GlobalRelationshipManager()
    # 添加Person
    person1 = Person(name="Alice", id=1, age=25)
    person2 = Person(name="Bob", id=2, age=30)    
    person1_id = r_manager.add_person(person1)
    person2_id = r_manager.add_person(person2)
    print(f"Added Person1 ID: {person1_id}, Person2 ID: {person2_id}")
    # 添加关系
    relationship = RelationshipEdge(
        from_entity=person1_id,
        to_entity=person2_id,
        relation_type=RelationType.FRIEND,
        intimacy_level=0.8,
        trust_level=0.9,
        interaction_frequency=5,
        last_interaction=datetime.now()
    )
    r_manager.add_relationship(person1, person2, relationship)
    print(f"Added relationship from {person1.name} to {person2.name}: {relationship.relation_type}, Intimacy: {relationship.intimacy_level}, Trust: {relationship.trust_level}, Frequency: {relationship.interaction_frequency}, Last Interaction: {relationship.last_interaction}")
    
    # 获取关系
    relationships = r_manager.get_someones_relationships(person1)
    print(f"Relationships for {person1.name}:")
    for rel in relationships:
        print(f"  To: {rel.relation_type}: ID:{rel.from_entity}, Intimacy: {rel.intimacy_level}, Trust: {rel.trust_level}, Frequency: {rel.interaction_frequency}, Last Interaction: {rel.last_interaction}") 
    # 删除关系
    r_manager.delete_relationship(person1, person2)
    print(f"Deleted relationship from {person1.name} to {person2.name}")    
    # 删除Person
    r_manager.delete_person(person1)
    print(f"Deleted Person: {person1.name}")
    r_manager.delete_person(person2)
    print(f"Deleted Person: {person2.name}")
    
    