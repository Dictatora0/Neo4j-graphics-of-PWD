#!/usr/bin/env python3
"""
Checkpoint Manager - 进度管理与断点续传
用于长时间运行的 LLM 任务，支持增量保存和断点恢复
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
from logger_config import get_logger

logger = get_logger('CheckpointManager')


class CheckpointManager:
    """
    进度管理器 - 支持增量保存和断点续传
    
    功能：
    1. 记录已处理的文本块 ID
    2. 增量保存概念和关系
    3. 程序重启后自动恢复
    4. 定期保存 checkpoint
    """
    
    def __init__(self, checkpoint_dir: str = "output/checkpoints"):
        """
        初始化 checkpoint 管理器
        
        Args:
            checkpoint_dir: checkpoint 文件保存目录
        """
        self.checkpoint_dir = checkpoint_dir
        self.progress_file = os.path.join(checkpoint_dir, ".progress.json")
        self.concepts_file = os.path.join(checkpoint_dir, "concepts_incremental.csv")
        self.relationships_file = os.path.join(checkpoint_dir, "relationships_incremental.csv")
        
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        self.progress = self._load_progress()
        logger.info(f"Checkpoint manager initialized: {checkpoint_dir}")
        
        if self.progress["processed_chunks"]:
            logger.info(f"Found existing progress: {len(self.progress['processed_chunks'])} chunks processed")
    
    def _load_progress(self) -> Dict:
        """加载进度文件"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                logger.info(f"Loaded progress from {self.progress_file}")
                return progress
            except Exception as e:
                logger.warning(f"Failed to load progress file: {e}")
        
        return {
            "processed_chunks": [],
            "total_concepts": 0,
            "total_relationships": 0,
            "started_at": datetime.now().isoformat(),
            "last_update": None
        }
    
    def _save_progress(self):
        """保存进度文件"""
        self.progress["last_update"] = datetime.now().isoformat()
        
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")
    
    def is_processed(self, chunk_id: str) -> bool:
        """检查文本块是否已处理"""
        return chunk_id in self.progress["processed_chunks"]
    
    def get_processed_chunks(self) -> List[str]:
        """获取已处理的文本块列表"""
        return self.progress["processed_chunks"]
    
    def save_chunk_results(self, chunk_id: str, concepts: List[Dict], 
                          relationships: List[Dict]):
        """
        保存单个文本块的处理结果
        
        Args:
            chunk_id: 文本块 ID
            concepts: 抽取的概念列表（可能为 None）
            relationships: 抽取的关系列表（可能为 None）
        """
        # 处理 None 情况（LLM 失败时可能返回 None）
        if concepts is None:
            concepts = []
        if relationships is None:
            relationships = []
        
        # 更新进度
        if chunk_id not in self.progress["processed_chunks"]:
            self.progress["processed_chunks"].append(chunk_id)
        
        self.progress["total_concepts"] += len(concepts)
        self.progress["total_relationships"] += len(relationships)
        
        # 增量保存 CSV
        self._append_to_csv(self.concepts_file, concepts)
        self._append_to_csv(self.relationships_file, relationships)
        
        # 保存进度文件
        self._save_progress()
        
        logger.debug(f"Saved results for chunk: {chunk_id}")
    
    def _append_to_csv(self, filepath: str, data: List[Dict]):
        """增量追加数据到 CSV"""
        if not data:
            return
        
        df = pd.DataFrame(data)
        
        # 如果文件存在，追加；否则创建
        if os.path.exists(filepath):
            df.to_csv(filepath, mode='a', header=False, index=False, 
                     encoding='utf-8-sig')
        else:
            df.to_csv(filepath, mode='w', header=True, index=False, 
                     encoding='utf-8-sig')
    
    def save_checkpoint(self, chunk_index: int, concepts_df: pd.DataFrame, 
                       relationships_df: pd.DataFrame):
        """
        保存完整 checkpoint（定期调用）
        
        Args:
            chunk_index: 当前处理到的块索引
            concepts_df: 当前所有概念
            relationships_df: 当前所有关系
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        checkpoint_concepts = os.path.join(
            self.checkpoint_dir, 
            f"checkpoint_concepts_{chunk_index}_{timestamp}.csv"
        )
        checkpoint_relationships = os.path.join(
            self.checkpoint_dir,
            f"checkpoint_relationships_{chunk_index}_{timestamp}.csv"
        )
        
        try:
            concepts_df.to_csv(checkpoint_concepts, index=False, encoding='utf-8-sig')
            relationships_df.to_csv(checkpoint_relationships, index=False, 
                                   encoding='utf-8-sig')
            
            logger.info(f"✓ Checkpoint saved at chunk {chunk_index}")
            logger.info(f"  - Concepts: {len(concepts_df)}")
            logger.info(f"  - Relationships: {len(relationships_df)}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def load_incremental_results(self) -> tuple:
        """
        加载增量保存的结果
        
        Returns:
            (concepts_df, relationships_df)
        """
        concepts_df = pd.DataFrame()
        relationships_df = pd.DataFrame()
        
        if os.path.exists(self.concepts_file):
            try:
                concepts_df = pd.read_csv(self.concepts_file, encoding='utf-8-sig')
                logger.info(f"Loaded {len(concepts_df)} concepts from checkpoint")
            except Exception as e:
                logger.warning(f"Failed to load concepts: {e}")
        
        if os.path.exists(self.relationships_file):
            try:
                relationships_df = pd.read_csv(self.relationships_file, 
                                              encoding='utf-8-sig')
                logger.info(f"Loaded {len(relationships_df)} relationships from checkpoint")
            except Exception as e:
                logger.warning(f"Failed to load relationships: {e}")
        
        return concepts_df, relationships_df
    
    def clear(self):
        """清除所有 checkpoint 数据（开始新任务时调用）"""
        logger.info("Clearing all checkpoints...")
        
        # 删除进度文件
        if os.path.exists(self.progress_file):
            os.remove(self.progress_file)
        
        # 删除增量 CSV
        if os.path.exists(self.concepts_file):
            os.remove(self.concepts_file)
        if os.path.exists(self.relationships_file):
            os.remove(self.relationships_file)
        
        # 重置进度
        self.progress = {
            "processed_chunks": [],
            "total_concepts": 0,
            "total_relationships": 0,
            "started_at": datetime.now().isoformat(),
            "last_update": None
        }
        
        logger.info("All checkpoints cleared")
    
    def get_summary(self) -> Dict:
        """获取进度摘要"""
        return {
            "processed_chunks": len(self.progress["processed_chunks"]),
            "total_concepts": self.progress["total_concepts"],
            "total_relationships": self.progress["total_relationships"],
            "started_at": self.progress.get("started_at"),
            "last_update": self.progress.get("last_update")
        }


if __name__ == "__main__":
    # 测试代码
    manager = CheckpointManager()
    
    # 模拟保存结果
    test_concepts = [
        {"entity": "松材线虫", "importance": 5, "category": "Pathogen"},
        {"entity": "马尾松", "importance": 4, "category": "Host"}
    ]
    
    test_relationships = [
        {"node_1": "松材线虫", "node_2": "马尾松", "edge": "INFECTS", "weight": 0.9}
    ]
    
    manager.save_chunk_results("chunk_001", test_concepts, test_relationships)
    
    # 打印摘要
    summary = manager.get_summary()
    print("\nCheckpoint Summary:")
    print(f"  Processed chunks: {summary['processed_chunks']}")
    print(f"  Total concepts: {summary['total_concepts']}")
    print(f"  Total relationships: {summary['total_relationships']}")
