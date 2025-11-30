"""
统计相关 API 路由
"""
from fastapi import APIRouter, Depends

from app.models import StatsData
from app.database import get_neo4j
from app.services.stats_service import StatsService

router = APIRouter()


@router.get("/", response_model=StatsData)
async def get_statistics(neo4j = Depends(get_neo4j)):
    """
    获取图谱统计数据
    
    包括：
    - 总节点数和总边数
    - 节点类型分布
    - 关系类型分布
    - 核心节点排名
    - 图密度
    """
    service = StatsService(neo4j)
    return service.get_graph_statistics()


@router.get("/distribution/nodes")
async def get_node_distribution(neo4j = Depends(get_neo4j)):
    """获取节点类型分布"""
    service = StatsService(neo4j)
    return service.get_node_distribution()


@router.get("/distribution/edges")
async def get_edge_distribution(neo4j = Depends(get_neo4j)):
    """获取关系类型分布"""
    service = StatsService(neo4j)
    return service.get_edge_distribution()


@router.get("/top-nodes")
async def get_top_nodes(
    limit: int = 10,
    neo4j = Depends(get_neo4j)
):
    """获取核心节点排行"""
    service = StatsService(neo4j)
    return service.get_top_nodes(limit)
