"""
Neo4j 数据库连接管理
"""
from neo4j import GraphDatabase
from app.config import settings


class Neo4jConnection:
    """Neo4j 连接管理器"""
    
    def __init__(self):
        self._driver = None
    
    def connect(self):
        """建立连接"""
        if not self._driver:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
        return self._driver
    
    def close(self):
        """关闭连接"""
        if self._driver:
            self._driver.close()
            self._driver = None
    
    def verify_connectivity(self):
        """验证连接"""
        driver = self.connect()
        driver.verify_connectivity()
    
    def execute_query(self, query: str, parameters: dict = None):
        """执行查询"""
        driver = self.connect()
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def execute_write(self, query: str, parameters: dict = None):
        """执行写入"""
        driver = self.connect()
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = session.write_transaction(
                lambda tx: tx.run(query, parameters or {})
            )
            return result


# 全局 Neo4j 连接实例
neo4j_connection = Neo4jConnection()
neo4j_driver = neo4j_connection.connect()


def close_neo4j_connection():
    """关闭 Neo4j 连接"""
    neo4j_connection.close()


def get_neo4j():
    """依赖注入: 获取 Neo4j 连接"""
    return neo4j_connection
