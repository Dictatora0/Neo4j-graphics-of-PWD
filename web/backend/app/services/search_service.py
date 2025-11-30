"""
搜索服务
处理搜索相关的业务逻辑
"""
from typing import Optional, List, Dict
from app.models import SearchResult, Node


class SearchService:
    """搜索服务类"""
    
    def __init__(self, neo4j_connection):
        self.neo4j = neo4j_connection
    
    def search_nodes(
        self,
        query: str,
        category: Optional[str] = None,
        min_importance: Optional[int] = None,
        limit: int = 20
    ) -> SearchResult:
        """搜索节点"""
        
        # 构建筛选条件
        filters = [f"toLower(n.name) CONTAINS toLower('{query}')"]
        
        if category:
            filters.append(f"n.category = '{category}'")
        if min_importance:
            filters.append(f"n.importance >= {min_importance}")
        
        where_clause = " AND ".join(filters)
        
        # 查询
        cypher_query = f"""
        MATCH (n)
        WHERE {where_clause}
        RETURN id(n) as id, n.name as name, n.category as category,
               n.importance as importance, n.total_degree as total_degree
        ORDER BY n.total_degree DESC
        LIMIT {limit}
        """
        
        result = self.neo4j.execute_query(cypher_query)
        nodes = [Node(**n) for n in result]
        
        # 获取总匹配数
        count_query = f"""
        MATCH (n)
        WHERE {where_clause}
        RETURN count(n) as total
        """
        
        count_result = self.neo4j.execute_query(count_query)
        total = count_result[0]['total'] if count_result else 0
        
        return SearchResult(
            nodes=nodes,
            total=total,
            query=query
        )
    
    def get_suggestions(self, query: str, limit: int = 5) -> List[Dict]:
        """获取搜索建议"""
        
        cypher_query = f"""
        MATCH (n)
        WHERE toLower(n.name) CONTAINS toLower('{query}')
        RETURN DISTINCT n.name as name, n.category as category
        ORDER BY length(n.name)
        LIMIT {limit}
        """
        
        result = self.neo4j.execute_query(cypher_query)
        return [{'name': r['name'], 'category': r['category']} for r in result]
