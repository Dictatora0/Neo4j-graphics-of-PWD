"""
图谱相关 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.models import GraphData, PathResult, PathQueryParams
from app.database import get_neo4j
from app.services.graph_service import GraphService

router = APIRouter()


@router.get("/", response_model=GraphData)
async def get_graph(
    limit: int = Query(100, ge=1, le=1000, description="节点数量限制"),
    node_type: Optional[str] = Query(None, description="节点类型筛选"),
    relation_type: Optional[str] = Query(None, description="关系类型筛选"),
    exclude_other: bool = Query(False, description="排除Other类型节点"),
    neo4j = Depends(get_neo4j)
):
    """
    获取图谱数据
    
    - **limit**: 返回节点数量限制
    - **node_type**: 节点类型筛选（可选）
    - **relation_type**: 关系类型筛选（可选）
    """
    service = GraphService(neo4j)
    return service.get_graph_data(
        limit=limit,
        node_type=node_type,
        relation_type=relation_type,
        exclude_other=exclude_other
    )


@router.post("/path", response_model=PathResult)
async def find_path(
    params: PathQueryParams,
    neo4j = Depends(get_neo4j)
):
    """
    查找两个节点之间的路径
    
    - **source**: 源节点名称
    - **target**: 目标节点名称
    - **max_length**: 最大路径长度
    """
    service = GraphService(neo4j)
    return service.find_shortest_paths(
        source=params.source,
        target=params.target,
        max_length=params.max_length
    )


@router.get("/subgraph/{node_name}", response_model=GraphData)
async def get_subgraph(
    node_name: str,
    depth: int = Query(1, ge=1, le=3, description="扩展深度"),
    neo4j = Depends(get_neo4j)
):
    """
    获取以指定节点为中心的子图
    
    - **node_name**: 节点名称
    - **depth**: 扩展深度（1-3）
    """
    service = GraphService(neo4j)
    return service.get_subgraph(node_name=node_name, depth=depth)
