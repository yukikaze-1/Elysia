from neo4j import GraphDatabase, Query
from dotenv import load_dotenv, find_dotenv
import os
from typing import Optional, Literal

class Neo4jManager:
    """Neo4j数据库管理器"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)            
        return cls._instance

    def __init__(self):
        load_dotenv(find_dotenv())
        self.uri = os.getenv("NEO4J_URL", "bolt://localhost:7687")
        self.auth = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
        print(f"Connecting to Neo4j at {self.uri} with user {self.auth[0]}")
        # 链接数据库
        self.driver = GraphDatabase.driver(self.uri, auth=self.auth)
    
    def add_node(self, label: str, properties: dict):
        """添加节点"""
        pass
    
    def add_edge(self, from_node: str, to_node: str, relationship_type: str, properties: dict):
        """添加边"""
        pass
        
    
    def execute_query(self, query: Query, parameters: dict | None= None):
        """执行查询"""
        results = self.driver.execute_query(query_=query, parameters_= parameters or {}, database_="neo4j")
        return results
    
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
            
if __name__ == "__main__":
    manager = Neo4jManager()
    print("Neo4j Manager initialized with URI:", manager.uri)
    # 这里可以添加更多测试代码来验证功能
    manager.close()
    print("Neo4j Manager closed.")