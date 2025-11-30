"""
搜索相关 API 路由
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.models import SearchResult
from app.database import get_neo4j
from app.services.search_service import SearchService

router = APIRouter()


@router.get("/", response_model=SearchResult)
async def search_nodes(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    category: Optional[str] = Query(None, description="节点类别筛选"),
    min_importance: Optional[int] = Query(None, ge=1, le=5, description="最小重要性"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    neo4j = Depends(get_neo4j)
):
    """
    搜索节点
    
    支持全文搜索和筛选
    
    - **q**: 搜索关键词（必填）
    - **category**: 节点类别筛选（可选）
    - **min_importance**: 最小重要性筛选（可选）
    - **limit**: 返回结果数量限制
    """
    service = SearchService(neo4j)
    return service.search_nodes(
        query=q,
        category=category,
        min_importance=min_importance,
        limit=limit
    )


@router.get("/suggest")
async def search_suggestions(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(5, ge=1, le=20, description="建议数量"),
    neo4j = Depends(get_neo4j)
):
    """
    搜索建议
    
    返回搜索关键词的自动补全建议
    """
    service = SearchService(neo4j)
    return service.get_suggestions(query=q, limit=limit)
