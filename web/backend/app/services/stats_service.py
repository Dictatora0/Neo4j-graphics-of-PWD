"""
统计服务
处理图谱统计相关的业务逻辑
"""
from typing import Dict, List
from app.models import StatsData, Node


class StatsService:
    """统计服务类"""
    
    def __init__(self, neo4j_connection):
        self.neo4j = neo4j_connection
    
    def get_graph_statistics(self) -> StatsData:
        """获取图谱统计数据"""
        
        # 总节点数和总边数
        count_query = """
        MATCH (n)
        WITH count(n) as node_count
        MATCH ()-[r]->()
        RETURN node_count, count(r) as edge_count
        """
        
        count_result = self.neo4j.execute_query(count_query)
        total_nodes = count_result[0]['node_count'] if count_result else 0
        total_edges = count_result[0]['edge_count'] if count_result else 0
        
        # 节点类型分布
        node_dist = self.get_node_distribution()
        
        # 关系类型分布
        edge_dist = self.get_edge_distribution()
        
        # 核心节点
        top_nodes = self.get_top_nodes(10)
        
        # 图密度
        density = None
        if total_nodes > 1:
            density = round(total_edges / (total_nodes * (total_nodes - 1)), 4)
        
        return StatsData(
            total_nodes=total_nodes,
            total_edges=total_edges,
            node_distribution=node_dist,
            edge_distribution=edge_dist,
            top_nodes=top_nodes,
            density=density
        )
    
    def get_node_distribution(self) -> Dict[str, int]:
        """获取节点类型分布"""
        
        query = """
        MATCH (n)
        RETURN n.category as category, count(n) as count
        ORDER BY count DESC
        """
        
        result = self.neo4j.execute_query(query)
        return {r['category']: r['count'] for r in result}
    
    def get_edge_distribution(self) -> Dict[str, int]:
        """获取关系类型分布"""
        
        query = """
        MATCH ()-[r]->()
        RETURN type(r) as relationship, count(r) as count
        ORDER BY count DESC
        """
        
        result = self.neo4j.execute_query(query)
        return {r['relationship']: r['count'] for r in result}
    
    def get_top_nodes(self, limit: int = 10) -> List[Node]:
        """获取核心节点"""
        
        query = f"""
        MATCH (n)
        RETURN id(n) as id, n.name as name, n.category as category,
               n.importance as importance, n.total_degree as total_degree
        ORDER BY n.total_degree DESC
        LIMIT {limit}
        """
        
        result = self.neo4j.execute_query(query)
        return [Node(**n) for n in result]
