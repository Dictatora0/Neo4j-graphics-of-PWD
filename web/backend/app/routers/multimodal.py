"""
多模态 API 路由
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from multimodal_graph_builder import MultimodalRetriever
import pandas as pd

router = APIRouter(prefix="/api/multimodal", tags=["multimodal"])

# 初始化多模态检索器（延迟加载）
retriever = None


def get_retriever():
    """获取多模态检索器实例"""
    global retriever
    
    if retriever is None:
        try:
            # 加载图片-概念关系
            rels_df = pd.read_csv('output/image_concept_relationships.csv')
            retriever = MultimodalRetriever(rels_df)
        except FileNotFoundError:
            # 如果文件不存在，返回空检索器
            retriever = MultimodalRetriever(pd.DataFrame())
    
    return retriever


class ImageRetrievalRequest(BaseModel):
    """图片检索请求模型"""
    concepts: List[str]
    max_images_per_concept: Optional[int] = 3


@router.post("/retrieve-images")
async def retrieve_images(request: ImageRetrievalRequest):
    """
    根据概念检索相关图片
    
    用于 Graph RAG 时召回关联图片
    """
    try:
        retriever = get_retriever()
        
        if not retriever.concept_to_images:
            return {
                "status": "success",
                "images": [],
                "message": "多模态功能未启用或无可用图片"
            }
        
        images = retriever.retrieve_images_for_concepts(
            concepts=request.concepts,
            max_images_per_concept=request.max_images_per_concept
        )
        
        return {
            "status": "success",
            "images": images,
            "total": len(images)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/image/{image_path:path}")
async def get_image(image_path: str):
    """
    获取图片文件
    
    返回图片的实际文件
    """
    try:
        # 安全检查：防止路径遍历攻击
        image_file = Path("output/pdf_images") / image_path
        
        if not image_file.exists():
            raise HTTPException(status_code=404, detail="图片不存在")
        
        if not image_file.is_file():
            raise HTTPException(status_code=400, detail="无效的图片路径")
        
        return FileResponse(image_file)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images/list")
async def list_images():
    """
    列出所有可用图片
    
    返回图片列表及其元数据
    """
    try:
        images_df = pd.read_csv('output/images.csv')
        
        images_list = images_df.to_dict('records')
        
        return {
            "status": "success",
            "images": images_list,
            "total": len(images_list)
        }
    
    except FileNotFoundError:
        return {
            "status": "success",
            "images": [],
            "total": 0,
            "message": "未找到图片数据"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/concept/{concept_name}/images")
async def get_concept_images(concept_name: str, max_images: int = 5):
    """
    获取特定概念的关联图片
    
    Args:
        concept_name: 概念名称
        max_images: 最多返回的图片数
    """
    try:
        retriever = get_retriever()
        
        if not retriever.concept_to_images:
            return {
                "status": "success",
                "concept": concept_name,
                "images": [],
                "message": "多模态功能未启用"
            }
        
        images = retriever.retrieve_images_for_concepts(
            concepts=[concept_name],
            max_images_per_concept=max_images
        )
        
        return {
            "status": "success",
            "concept": concept_name,
            "images": images,
            "total": len(images)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_multimodal_stats():
    """
    获取多模态数据统计
    
    返回图片数量、概念覆盖率等信息
    """
    try:
        # 加载数据
        images_df = pd.read_csv('output/images.csv')
        rels_df = pd.read_csv('output/image_concept_relationships.csv')
        
        stats = {
            "total_images": len(images_df),
            "total_relationships": len(rels_df),
            "concepts_with_images": rels_df['concept'].nunique(),
            "avg_images_per_concept": len(rels_df) / rels_df['concept'].nunique() if len(rels_df) > 0 else 0
        }
        
        return {
            "status": "success",
            "stats": stats
        }
    
    except FileNotFoundError:
        return {
            "status": "success",
            "stats": {
                "total_images": 0,
                "total_relationships": 0,
                "concepts_with_images": 0,
                "avg_images_per_concept": 0
            },
            "message": "多模态功能未启用"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
