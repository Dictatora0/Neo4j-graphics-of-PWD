"""
Pydantic 数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class Node(BaseModel):
    """节点模型"""
    id: str = Field(..., description="节点ID")
    name: str = Field(..., description="节点名称")
    category: str = Field(..., description="节点类别")
    importance: Optional[int] = Field(None, description="重要性评分(1-5)")
    total_degree: Optional[int] = Field(None, description="总连接数")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="其他属性")


class Edge(BaseModel):
    """边模型"""
    id: str = Field(..., description="边ID")
    source: str = Field(..., description="源节点ID")
    target: str = Field(..., description="目标节点ID")
    relationship: str = Field(..., description="关系类型")
    weight: Optional[float] = Field(None, description="权重")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="其他属性")


class GraphData(BaseModel):
    """图谱数据模型"""
    nodes: List[Node] = Field(default_factory=list, description="节点列表")
    edges: List[Edge] = Field(default_factory=list, description="边列表")
    total_nodes: int = Field(0, description="总节点数")
    total_edges: int = Field(0, description="总边数")


class NodeDetail(BaseModel):
    """节点详情模型"""
    node: Node
    neighbors: List[Node] = Field(default_factory=list, description="邻居节点")
    relationships: List[Edge] = Field(default_factory=list, description="关联关系")


class SearchResult(BaseModel):
    """搜索结果模型"""
    nodes: List[Node] = Field(default_factory=list, description="匹配的节点")
    total: int = Field(0, description="总匹配数")
    query: str = Field(..., description="搜索关键词")


class PathResult(BaseModel):
    """路径查询结果"""
    paths: List[List[str]] = Field(default_factory=list, description="路径列表")
    total_paths: int = Field(0, description="路径总数")


class StatsData(BaseModel):
    """统计数据模型"""
    total_nodes: int = Field(0, description="总节点数")
    total_edges: int = Field(0, description="总边数")
    node_distribution: Dict[str, int] = Field(default_factory=dict, description="节点类型分布")
    edge_distribution: Dict[str, int] = Field(default_factory=dict, description="边类型分布")
    top_nodes: List[Node] = Field(default_factory=list, description="核心节点")
    density: Optional[float] = Field(None, description="图密度")
    avg_degree: Optional[float] = Field(None, description="平均度数")


class QueryParams(BaseModel):
    """查询参数"""
    limit: int = Field(100, ge=1, le=1000, description="返回数量限制")
    offset: int = Field(0, ge=0, description="偏移量")
    node_type: Optional[str] = Field(None, description="节点类型筛选")
    relation_type: Optional[str] = Field(None, description="关系类型筛选")
    min_importance: Optional[int] = Field(None, ge=1, le=5, description="最小重要性")


class PathQueryParams(BaseModel):
    """路径查询参数"""
    source: str = Field(..., description="源节点名称")
    target: str = Field(..., description="目标节点名称")
    max_length: int = Field(5, ge=1, le=10, description="最大路径长度")
