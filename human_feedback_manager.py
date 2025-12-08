#!/usr/bin/env python3
"""
人机回环反馈管理模块

功能:
1. 记录用户对知识图谱的纠错反馈
2. 构建"错题集"用于 Prompt 优化或模型微调
3. 支持关系方向纠正、实体合并/拆分等操作
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import json
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)


class FeedbackType:
    """反馈类型枚举"""
    RELATION_DIRECTION_ERROR = "relation_direction_error"  # 关系方向错误
    RELATION_TYPE_ERROR = "relation_type_error"  # 关系类型错误
    ENTITY_MERGE = "entity_merge"  # 实体应该合并
    ENTITY_SPLIT = "entity_split"  # 实体应该拆分
    MISSING_RELATION = "missing_relation"  # 缺失关系
    SPURIOUS_RELATION = "spurious_relation"  # 虚假关系
    ENTITY_CATEGORY_ERROR = "entity_category_error"  # 实体类别错误
    OTHER = "other"  # 其他


class HumanFeedbackManager:
    """
    人机回环反馈管理器
    
    功能:
    - 记录用户反馈
    - 生成纠错报告
    - 导出训练数据
    """
    
    def __init__(self, feedback_file: str = "output/human_feedback.jsonl"):
        """
        Args:
            feedback_file: 反馈记录文件路径（JSONL 格式）
        """
        self.feedback_file = Path(feedback_file)
        self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载已有反馈
        self.feedbacks = self._load_feedbacks()
        
        logger.info(f"HumanFeedbackManager initialized with {len(self.feedbacks)} existing feedbacks")
    
    def _load_feedbacks(self) -> List[Dict]:
        """加载已有反馈记录"""
        if not self.feedback_file.exists():
            return []
        
        feedbacks = []
        try:
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        feedbacks.append(json.loads(line))
            
            logger.info(f"Loaded {len(feedbacks)} feedbacks from {self.feedback_file}")
        
        except Exception as e:
            logger.error(f"Failed to load feedbacks: {e}")
        
        return feedbacks
    
    def _save_feedback(self, feedback: Dict):
        """保存单条反馈"""
        try:
            with open(self.feedback_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(feedback, ensure_ascii=False) + '\n')
            
            logger.info(f"Saved feedback: {feedback['feedback_type']}")
        
        except Exception as e:
            logger.error(f"Failed to save feedback: {e}")
    
    def record_relation_direction_error(self, 
                                       node_1: str,
                                       node_2: str,
                                       relation_type: str,
                                       correct_direction: str,
                                       user_id: str = "anonymous",
                                       comment: str = "") -> str:
        """
        记录关系方向错误
        
        Args:
            node_1: 源节点
            node_2: 目标节点
            relation_type: 关系类型
            correct_direction: 正确方向 ("reverse" 或 "correct")
            user_id: 用户 ID
            comment: 备注
        
        Returns:
            反馈 ID
        """
        feedback = {
            'feedback_id': f"fb_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            'feedback_type': FeedbackType.RELATION_DIRECTION_ERROR,
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'data': {
                'original': {
                    'node_1': node_1,
                    'node_2': node_2,
                    'relation_type': relation_type
                },
                'correction': {
                    'correct_direction': correct_direction,
                    'corrected_node_1': node_2 if correct_direction == "reverse" else node_1,
                    'corrected_node_2': node_1 if correct_direction == "reverse" else node_2
                }
            },
            'comment': comment
        }
        
        self.feedbacks.append(feedback)
        self._save_feedback(feedback)
        
        return feedback['feedback_id']
    
    def record_relation_type_error(self,
                                   node_1: str,
                                   node_2: str,
                                   wrong_relation: str,
                                   correct_relation: str,
                                   user_id: str = "anonymous",
                                   comment: str = "") -> str:
        """
        记录关系类型错误
        
        Args:
            node_1: 源节点
            node_2: 目标节点
            wrong_relation: 错误的关系类型
            correct_relation: 正确的关系类型
            user_id: 用户 ID
            comment: 备注
        
        Returns:
            反馈 ID
        """
        feedback = {
            'feedback_id': f"fb_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            'feedback_type': FeedbackType.RELATION_TYPE_ERROR,
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'data': {
                'node_1': node_1,
                'node_2': node_2,
                'wrong_relation': wrong_relation,
                'correct_relation': correct_relation
            },
            'comment': comment
        }
        
        self.feedbacks.append(feedback)
        self._save_feedback(feedback)
        
        return feedback['feedback_id']
    
    def record_entity_merge(self,
                           entity_1: str,
                           entity_2: str,
                           canonical_name: str,
                           user_id: str = "anonymous",
                           comment: str = "") -> str:
        """
        记录实体合并建议
        
        Args:
            entity_1: 实体1
            entity_2: 实体2
            canonical_name: 标准名称
            user_id: 用户 ID
            comment: 备注
        
        Returns:
            反馈 ID
        """
        feedback = {
            'feedback_id': f"fb_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            'feedback_type': FeedbackType.ENTITY_MERGE,
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'data': {
                'entity_1': entity_1,
                'entity_2': entity_2,
                'canonical_name': canonical_name
            },
            'comment': comment
        }
        
        self.feedbacks.append(feedback)
        self._save_feedback(feedback)
        
        return feedback['feedback_id']
    
    def record_missing_relation(self,
                                node_1: str,
                                node_2: str,
                                relation_type: str,
                                user_id: str = "anonymous",
                                comment: str = "") -> str:
        """
        记录缺失关系
        
        Args:
            node_1: 源节点
            node_2: 目标节点
            relation_type: 关系类型
            user_id: 用户 ID
            comment: 备注
        
        Returns:
            反馈 ID
        """
        feedback = {
            'feedback_id': f"fb_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            'feedback_type': FeedbackType.MISSING_RELATION,
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'data': {
                'node_1': node_1,
                'node_2': node_2,
                'relation_type': relation_type
            },
            'comment': comment
        }
        
        self.feedbacks.append(feedback)
        self._save_feedback(feedback)
        
        return feedback['feedback_id']
    
    def generate_feedback_report(self) -> Dict:
        """
        生成反馈统计报告
        
        Returns:
            统计报告字典
        """
        if not self.feedbacks:
            return {'total': 0, 'by_type': {}, 'by_user': {}}
        
        # 按类型统计
        by_type = {}
        for fb in self.feedbacks:
            fb_type = fb['feedback_type']
            by_type[fb_type] = by_type.get(fb_type, 0) + 1
        
        # 按用户统计
        by_user = {}
        for fb in self.feedbacks:
            user_id = fb['user_id']
            by_user[user_id] = by_user.get(user_id, 0) + 1
        
        report = {
            'total': len(self.feedbacks),
            'by_type': by_type,
            'by_user': by_user,
            'recent_feedbacks': self.feedbacks[-10:]  # 最近 10 条
        }
        
        return report
    
    def export_training_data(self, output_file: str = "output/feedback_training_data.json"):
        """
        导出训练数据（用于 Prompt 优化或模型微调）
        
        Args:
            output_file: 输出文件路径
        """
        if not self.feedbacks:
            logger.warning("No feedbacks to export")
            return
        
        training_data = []
        
        for fb in self.feedbacks:
            fb_type = fb['feedback_type']
            data = fb['data']
            
            # 根据反馈类型构建训练样本
            if fb_type == FeedbackType.RELATION_DIRECTION_ERROR:
                training_data.append({
                    'input': f"关系: {data['original']['node_1']} → {data['original']['relation_type']} → {data['original']['node_2']}",
                    'output': f"正确方向: {data['correction']['corrected_node_1']} → {data['original']['relation_type']} → {data['correction']['corrected_node_2']}",
                    'feedback_type': fb_type
                })
            
            elif fb_type == FeedbackType.RELATION_TYPE_ERROR:
                training_data.append({
                    'input': f"关系: {data['node_1']} → {data['wrong_relation']} → {data['node_2']}",
                    'output': f"正确关系: {data['node_1']} → {data['correct_relation']} → {data['node_2']}",
                    'feedback_type': fb_type
                })
            
            elif fb_type == FeedbackType.ENTITY_MERGE:
                training_data.append({
                    'input': f"实体: {data['entity_1']}, {data['entity_2']}",
                    'output': f"应合并为: {data['canonical_name']}",
                    'feedback_type': fb_type
                })
        
        # 保存训练数据
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(training_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Exported {len(training_data)} training samples to {output_file}")
        
        except Exception as e:
            logger.error(f"Failed to export training data: {e}")
    
    def get_error_patterns(self) -> Dict:
        """
        分析常见错误模式
        
        Returns:
            错误模式统计
        """
        patterns = {
            'common_direction_errors': {},  # 常见方向错误
            'common_type_errors': {},  # 常见类型错误
            'common_merge_suggestions': []  # 常见合并建议
        }
        
        for fb in self.feedbacks:
            fb_type = fb['feedback_type']
            data = fb['data']
            
            if fb_type == FeedbackType.RELATION_DIRECTION_ERROR:
                rel_type = data['original']['relation_type']
                patterns['common_direction_errors'][rel_type] = \
                    patterns['common_direction_errors'].get(rel_type, 0) + 1
            
            elif fb_type == FeedbackType.RELATION_TYPE_ERROR:
                error_pair = f"{data['wrong_relation']} → {data['correct_relation']}"
                patterns['common_type_errors'][error_pair] = \
                    patterns['common_type_errors'].get(error_pair, 0) + 1
            
            elif fb_type == FeedbackType.ENTITY_MERGE:
                patterns['common_merge_suggestions'].append({
                    'entities': [data['entity_1'], data['entity_2']],
                    'canonical': data['canonical_name']
                })
        
        return patterns


if __name__ == "__main__":
    # 测试示例
    print("="*80)
    print("人机回环反馈管理器测试")
    print("="*80)
    
    manager = HumanFeedbackManager()
    
    # 记录关系方向错误
    fb_id = manager.record_relation_direction_error(
        node_1="松褐天牛",
        node_2="松材线虫",
        relation_type="传播",
        correct_direction="correct",
        comment="方向正确，无需修改"
    )
    print(f"\n记录反馈 ID: {fb_id}")
    
    # 生成报告
    report = manager.generate_feedback_report()
    print(f"\n反馈统计: {report}")
    
    # 导出训练数据
    manager.export_training_data()
    print("\n训练数据已导出")
