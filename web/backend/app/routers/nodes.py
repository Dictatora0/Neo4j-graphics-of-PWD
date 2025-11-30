"""
节点相关 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from typing import Optional, List

from app.models import Node, NodeDetail, GraphData
from app.database import get_neo4j
from app.services.graph_service import GraphService

router = APIRouter()


@router.get("/{node_id}", response_model=NodeDetail)
async def get_node_detail(
    node_id: str = Path(..., description="节点ID"),
    neo4j = Depends(get_neo4j)
):
    """
    获取节点详情
    
    包括节点基本信息、邻居节点和关联关系
    """
    service = GraphService(neo4j)
    node_detail = service.get_node_detail(node_id)
    
    if not node_detail:
        raise HTTPException(status_code=404, detail=f"节点 {node_id} 不存在")
    
    return node_detail


@router.get("/{node_id}/neighbors", response_model=GraphData)
async def get_node_neighbors(
    node_id: str = Path(..., description="节点ID"),
    depth: int = Query(1, ge=1, le=3, description="邻居深度"),
    neo4j = Depends(get_neo4j)
):
    """
    获取节点的邻居节点和关系
    
    - **node_id**: 节点ID
    - **depth**: 邻居深度（1-3跳）
    """
    service = GraphService(neo4j)
    return service.get_node_neighbors(node_id, depth)


@router.get("/", response_model=List[Node])
async def list_nodes(
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    category: Optional[str] = Query(None, description="节点类别"),
    min_importance: Optional[int] = Query(None, ge=1, le=5, description="最小重要性"),
    neo4j = Depends(get_neo4j)
):
    """
    获取节点列表
    
    支持分页和筛选
    """
    service = GraphService(neo4j)
    return service.list_nodes(
        limit=limit,
        offset=offset,
        category=category,
        min_importance=min_importance
    )
