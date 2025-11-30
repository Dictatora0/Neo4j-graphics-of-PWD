"""
图谱服务
处理图谱相关的业务逻辑
"""
from typing import Optional, List
from app.models import GraphData, Node, Edge, NodeDetail, PathResult
from app.config import settings


class GraphService:
    """图谱服务类"""
    
    def __init__(self, neo4j_connection):
        self.neo4j = neo4j_connection
    
    def get_graph_data(
        self,
        limit: int = 100,
        node_type: Optional[str] = None,
        relation_type: Optional[str] = None,
        exclude_other: bool = False
    ) -> GraphData:
        """获取图谱数据"""
        
        # 构建节点查询 - 使用labels()获取节点类型
        # 优先返回非Other类型和高度数节点
        filters = []
        if node_type:
            filters.append(f"'{node_type}' IN labels(n)")
        if exclude_other:
            filters.append("n.type <> 'Other'")
        
        node_filter = "WHERE " + " AND ".join(filters) if filters else ""
        node_query = f"""
        MATCH (n)
        {node_filter}
        RETURN elementId(n) as id, n.name as name, 
               COALESCE(n.type, labels(n)[0], 'Other') as category,
               n.importance as importance, 
               COALESCE(n.total_degree, 0) as total_degree
        ORDER BY 
            CASE WHEN n.type = 'Other' THEN 1 ELSE 0 END,
            COALESCE(n.total_degree, 0) DESC
        LIMIT {limit}
        """
        
        # 执行节点查询
        nodes_data = self.neo4j.execute_query(node_query)
        
        # 提取节点ID
        node_ids = [node['id'] for node in nodes_data]
        
        # 构建关系查询
        relation_filter = f"WHERE type(r) = '{relation_type}'" if relation_type else ""
        edge_query = f"""
        MATCH (n)-[r]->(m)
        {relation_filter}
        WHERE elementId(n) IN $node_ids AND elementId(m) IN $node_ids
        RETURN elementId(r) as id, elementId(n) as source, elementId(m) as target,
               type(r) as relationship, r.weight as weight
        """
        
        # 查询关系
        edges_data = self.neo4j.execute_query(edge_query, {'node_ids': node_ids})
        
        # 转换为模型
        nodes = [Node(**node) for node in nodes_data]
        edges = [Edge(**edge) for edge in edges_data]
        
        return GraphData(
            nodes=nodes,
            edges=edges,
            total_nodes=len(nodes),
            total_edges=len(edges)
        )
    
    def get_node_detail(self, node_id: str) -> Optional[NodeDetail]:
        """获取节点详情"""
        
        # 查询节点信息
        node_query = """
        MATCH (n)
        WHERE id(n) = $node_id OR n.name = $node_id
        RETURN id(n) as id, n.name as name, n.category as category,
               n.importance as importance, n.total_degree as total_degree
        """
        
        nodes = self.neo4j.execute_query(node_query, {'node_id': node_id})
        if not nodes:
            return None
        
        node_data = nodes[0]
        
        # 查询邻居节点
        neighbors_query = """
        MATCH (n)-[]-(m)
        WHERE id(n) = $node_id
        RETURN DISTINCT id(m) as id, m.name as name, m.category as category,
               m.importance as importance, m.total_degree as total_degree
        LIMIT 20
        """
        
        neighbors_data = self.neo4j.execute_query(neighbors_query, {'node_id': node_data['id']})
        
        # 查询关联关系
        relationships_query = """
        MATCH (n)-[r]-(m)
        WHERE id(n) = $node_id
        RETURN id(r) as id, id(n) as source, id(m) as target,
               type(r) as relationship, r.weight as weight
        LIMIT 50
        """
        
        relationships_data = self.neo4j.execute_query(
            relationships_query,
            {'node_id': node_data['id']}
        )
        
        return NodeDetail(
            node=Node(**node_data),
            neighbors=[Node(**n) for n in neighbors_data],
            relationships=[Edge(**r) for r in relationships_data]
        )
    
    def get_node_neighbors(self, node_id: str, depth: int = 1) -> GraphData:
        """获取节点邻居"""
        
        query = f"""
        MATCH path = (n)-[*1..{depth}]-(m)
        WHERE id(n) = $node_id OR n.name = $node_id
        WITH nodes(path) as path_nodes, relationships(path) as path_rels
        UNWIND path_nodes as node
        WITH collect(DISTINCT {{
            id: id(node),
            name: node.name,
            category: node.category,
            importance: node.importance,
            total_degree: node.total_degree
        }}) as nodes_list, path_rels
        UNWIND path_rels as rel
        WITH nodes_list, collect(DISTINCT {{
            id: id(rel),
            source: id(startNode(rel)),
            target: id(endNode(rel)),
            relationship: type(rel),
            weight: rel.weight
        }}) as edges_list
        RETURN nodes_list, edges_list
        """
        
        result = self.neo4j.execute_query(query, {'node_id': node_id})
        
        if not result:
            return GraphData(nodes=[], edges=[])
        
        nodes_data = result[0].get('nodes_list', [])
        edges_data = result[0].get('edges_list', [])
        
        return GraphData(
            nodes=[Node(**n) for n in nodes_data],
            edges=[Edge(**e) for e in edges_data],
            total_nodes=len(nodes_data),
            total_edges=len(edges_data)
        )
    
    def get_subgraph(self, node_name: str, depth: int = 1) -> GraphData:
        """获取子图"""
        return self.get_node_neighbors(node_name, depth)
    
    def find_shortest_paths(
        self,
        source: str,
        target: str,
        max_length: int = 5
    ) -> PathResult:
        """查找最短路径"""
        
        query = f"""
        MATCH path = shortestPath((n)-[*..{max_length}]-(m))
        WHERE n.name = $source AND m.name = $target
        RETURN [node in nodes(path) | node.name] as path_names
        LIMIT 10
        """
        
        result = self.neo4j.execute_query(
            query,
            {'source': source, 'target': target}
        )
        
        paths = [r['path_names'] for r in result]
        
        return PathResult(paths=paths, total_paths=len(paths))
    
    def list_nodes(
        self,
        limit: int = 100,
        offset: int = 0,
        category: Optional[str] = None,
        min_importance: Optional[int] = None
    ) -> List[Node]:
        """节点列表"""
        
        filters = []
        if category:
            filters.append(f"n.category = '{category}'")
        if min_importance:
            filters.append(f"n.importance >= {min_importance}")
        
        where_clause = "WHERE " + " AND ".join(filters) if filters else ""
        
        query = f"""
        MATCH (n)
        {where_clause}
        RETURN id(n) as id, n.name as name, n.category as category,
               n.importance as importance, n.total_degree as total_degree
        ORDER BY n.total_degree DESC
        SKIP {offset}
        LIMIT {limit}
        """
        
        result = self.neo4j.execute_query(query)
        return [Node(**n) for n in result]
