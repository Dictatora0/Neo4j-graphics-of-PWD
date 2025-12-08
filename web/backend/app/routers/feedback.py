"""
人机回环反馈 API 路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from human_feedback_manager import HumanFeedbackManager

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

# 初始化反馈管理器
feedback_manager = HumanFeedbackManager()


class RelationDirectionFeedback(BaseModel):
    """关系方向反馈模型"""
    node_1: str
    node_2: str
    relation_type: str
    correct_direction: str  # "reverse" or "correct"
    user_id: Optional[str] = "anonymous"
    comment: Optional[str] = ""


class RelationTypeFeedback(BaseModel):
    """关系类型反馈模型"""
    node_1: str
    node_2: str
    wrong_relation: str
    correct_relation: str
    user_id: Optional[str] = "anonymous"
    comment: Optional[str] = ""


class EntityMergeFeedback(BaseModel):
    """实体合并反馈模型"""
    entity_1: str
    entity_2: str
    canonical_name: str
    user_id: Optional[str] = "anonymous"
    comment: Optional[str] = ""


class MissingRelationFeedback(BaseModel):
    """缺失关系反馈模型"""
    node_1: str
    node_2: str
    relation_type: str
    user_id: Optional[str] = "anonymous"
    comment: Optional[str] = ""


@router.post("/relation-direction")
async def submit_relation_direction_feedback(feedback: RelationDirectionFeedback):
    """
    提交关系方向纠错反馈
    
    用户发现关系方向错误时调用此接口
    """
    try:
        feedback_id = feedback_manager.record_relation_direction_error(
            node_1=feedback.node_1,
            node_2=feedback.node_2,
            relation_type=feedback.relation_type,
            correct_direction=feedback.correct_direction,
            user_id=feedback.user_id,
            comment=feedback.comment
        )
        
        return {
            "status": "success",
            "feedback_id": feedback_id,
            "message": "反馈已记录，感谢您的贡献！"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relation-type")
async def submit_relation_type_feedback(feedback: RelationTypeFeedback):
    """
    提交关系类型纠错反馈
    
    用户发现关系类型错误时调用此接口
    """
    try:
        feedback_id = feedback_manager.record_relation_type_error(
            node_1=feedback.node_1,
            node_2=feedback.node_2,
            wrong_relation=feedback.wrong_relation,
            correct_relation=feedback.correct_relation,
            user_id=feedback.user_id,
            comment=feedback.comment
        )
        
        return {
            "status": "success",
            "feedback_id": feedback_id,
            "message": "反馈已记录，感谢您的贡献！"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entity-merge")
async def submit_entity_merge_feedback(feedback: EntityMergeFeedback):
    """
    提交实体合并建议
    
    用户发现两个实体应该合并时调用此接口
    """
    try:
        feedback_id = feedback_manager.record_entity_merge(
            entity_1=feedback.entity_1,
            entity_2=feedback.entity_2,
            canonical_name=feedback.canonical_name,
            user_id=feedback.user_id,
            comment=feedback.comment
        )
        
        return {
            "status": "success",
            "feedback_id": feedback_id,
            "message": "反馈已记录，感谢您的贡献！"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/missing-relation")
async def submit_missing_relation_feedback(feedback: MissingRelationFeedback):
    """
    提交缺失关系反馈
    
    用户发现应该存在但缺失的关系时调用此接口
    """
    try:
        feedback_id = feedback_manager.record_missing_relation(
            node_1=feedback.node_1,
            node_2=feedback.node_2,
            relation_type=feedback.relation_type,
            user_id=feedback.user_id,
            comment=feedback.comment
        )
        
        return {
            "status": "success",
            "feedback_id": feedback_id,
            "message": "反馈已记录，感谢您的贡献！"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
async def get_feedback_report():
    """
    获取反馈统计报告
    
    管理员查看反馈统计信息
    """
    try:
        report = feedback_manager.generate_feedback_report()
        return report
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/error-patterns")
async def get_error_patterns():
    """
    获取常见错误模式
    
    用于分析和改进系统
    """
    try:
        patterns = feedback_manager.get_error_patterns()
        return patterns
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export-training-data")
async def export_training_data():
    """
    导出训练数据
    
    管理员导出反馈数据用于模型优化
    """
    try:
        feedback_manager.export_training_data()
        return {
            "status": "success",
            "message": "训练数据已导出到 output/feedback_training_data.json"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
