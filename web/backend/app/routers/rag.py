"""
GraphRAG 问答 API 路由
提供 Local Search 和 Community Summary 功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.database import neo4j_driver

router = APIRouter(prefix="/api/rag", tags=["GraphRAG"])


class LocalSearchRequest(BaseModel):
    """Local Search 请求"""
    query: str
    top_k: int = 5
    expand_depth: int = 1


class LocalSearchResult(BaseModel):
    """Local Search 结果"""
    answer: str
    relevant_nodes: List[Dict[str, Any]]
    relevant_edges: List[Dict[str, Any]]
    confidence: float
    sources: List[str]


class CommunitySummaryRequest(BaseModel):
    """Community Summary 请求"""
    algorithm: str = "louvain"  # louvain, leiden, label_propagation
    resolution: float = 1.0


class Community(BaseModel):
    """社区信息"""
    id: int
    title: str
    summary: str
    size: int
    core_concepts: List[str]


@router.post("/local-search", response_model=LocalSearchResult)
async def local_search(request: LocalSearchRequest):
    """
    Local Search 问答接口
    
    流程：
    1. 从 Neo4j 加载图谱数据到 DataFrame
    2. 向量检索：找到与问题最相关的 top_k 个节点
    3. 子图扩展：沿着关系扩展 expand_depth 层
    4. LLM 生成：基于召回的子图生成答案
    """
    try:
        # 导入必要的模块
        from graph_rag import LocalSearchEngine
        import pandas as pd
        
        # 初始化搜索引擎
        search_engine = LocalSearchEngine(
            model="llama3.2:3b",
            ollama_host="http://localhost:11434",
            embedding_model="BAAI/bge-m3"
        )
        
        # 从 Neo4j 加载数据
        with neo4j_driver.session() as session:
            # 加载所有节点
            nodes_result = session.run("""
                MATCH (n)
                RETURN n.name as entity, 
                       labels(n)[0] as category,
                       COALESCE(n.importance, 0) as importance,
                       COALESCE(n.degree, 0) as degree
            """)
            concepts_df = pd.DataFrame([dict(record) for record in nodes_result])
            
            # 加载所有关系
            rels_result = session.run("""
                MATCH (n1)-[r]->(n2)
                RETURN n1.name as node_1,
                       n2.name as node_2,
                       type(r) as edge,
                       COALESCE(r.weight, 1.0) as weight
            """)
            relationships_df = pd.DataFrame([dict(record) for record in rels_result])
        
        if concepts_df.empty:
            raise HTTPException(
                status_code=404,
                detail="图谱中没有数据，请先构建知识图谱"
            )
        
        # 构建索引（如果还没有）
        if not search_engine.node_index:
            search_engine.build_node_index(concepts_df)
        
        # 执行问答
        answer_result = search_engine.answer_query(
            query=request.query,
            concepts_df=concepts_df,
            relationships_df=relationships_df,
            top_k=request.top_k,
            max_hops=request.expand_depth
        )
        
        if not answer_result:
            return LocalSearchResult(
                answer="抱歉，无法生成答案。",
                relevant_nodes=[],
                relevant_edges=[],
                confidence=0.0,
                sources=[]
            )
        
        # 转换结果格式
        relevant_nodes = []
        for entity, score in answer_result.get("relevant_nodes", []):
            node_info = concepts_df[concepts_df['entity'] == entity]
            if not node_info.empty:
                relevant_nodes.append({
                    "id": entity,
                    "name": entity,
                    "category": node_info.iloc[0].get('category', ''),
                    "similarity": float(score)
                })
        
        relevant_edges = []
        for _, row in answer_result.get("subgraph_relations", pd.DataFrame()).iterrows():
            relevant_edges.append({
                "source": row['node_1'],
                "target": row['node_2'],
                "relationship": row['edge'],
                "weight": float(row.get('weight', 1.0))
            })
        
        return LocalSearchResult(
            answer=answer_result.get("answer", ""),
            relevant_nodes=relevant_nodes,
            relevant_edges=relevant_edges,
            confidence=0.85,
            sources=[node['name'] for node in relevant_nodes[:5]]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Local Search 失败: {str(e)}")


@router.post("/community-summary", response_model=List[Community])
async def get_community_summary(request: CommunitySummaryRequest):
    """
    获取社区检测和摘要
    
    使用社区检测算法（Louvain/Leiden）划分图谱，
    并为每个社区生成标题和摘要
    """
    try:
        from graph_rag import CommunityDetector, CommunitySummarizer
        
        driver = neo4j_driver
        
        # 社区检测
        detector = CommunityDetector(driver)
        communities_data = detector.detect_communities(
            algorithm=request.algorithm,
            resolution=request.resolution
        )
        
        if not communities_data:
            return []
        
        # 生成摘要
        summarizer = CommunitySummarizer(driver)
        summaries = summarizer.summarize_all_communities(communities_data)
        
        # 格式化输出
        result = []
        for comm_id, summary_data in summaries.items():
            result.append(Community(
                id=comm_id,
                title=summary_data.get("title", f"社区 {comm_id}"),
                summary=summary_data.get("summary", ""),
                size=summary_data.get("size", 0),
                core_concepts=summary_data.get("core_concepts", [])[:5]
            ))
        
        # 按大小排序
        result.sort(key=lambda x: x.size, reverse=True)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"社区分析失败: {str(e)}")


@router.get("/stats")
async def get_rag_stats():
    """获取 GraphRAG 相关统计信息"""
    try:
        from graph_rag import LocalSearchEngine
        
        driver = neo4j_driver
        search_engine = LocalSearchEngine(
            neo4j_driver=driver,
            embedding_model="BAAI/bge-m3"
        )
        
        index_exists = search_engine.check_index_exists()
        
        # 获取索引节点数
        indexed_count = 0
        if index_exists:
            with driver.session() as session:
                result = session.run(
                    "MATCH (n) WHERE n.embedding IS NOT NULL RETURN count(n) as count"
                )
                record = result.single()
                if record:
                    indexed_count = record["count"]
        
        return {
            "local_search_ready": index_exists,
            "indexed_nodes": indexed_count,
            "embedding_model": "BAAI/bge-m3"
        }
        
    except Exception as e:
        return {
            "local_search_ready": False,
            "indexed_nodes": 0,
            "error": str(e)
        }
