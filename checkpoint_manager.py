#!/usr/bin/env python3
"""Checkpoint Manager - 进度管理与断点续传

专门负责**长时间运行管道**(如 enhanced_pipeline_safe.py)的进度管理, 提供:

- 按块增量保存: 每处理完一个 `chunk_id` 就把其 concepts/relationships 追加到增量 CSV;
- 进度追踪: 维护 `.progress.json`, 记录已处理块列表及累计概念/关系数量;
- 定期快照: 通过 `save_checkpoint` 定期导出当前完整 DataFrame, 方便中途查看效果;
- 断点续传: 下次启动时由管道读取 `.progress.json`, 自动跳过已处理块;
- 进度清理: `clear()` 支持“一键清空 checkpoint, 从头再跑一遍”。

该模块被 `enhanced_pipeline_safe.py`、`continue_processing.py`、`check_status.py` 等多处复用,
是整个系统实现“几乎零数据丢失”能力的核心组件之一。
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
from logger_config import get_logger

logger = get_logger('CheckpointManager')


class CheckpointManager:
    """进度管理器 - 支持增量保存和断点续传

    可以把它理解为“SafePipeline 的黑匣子记录器”, 核心职责:

    - 记录已经成功处理过的 `chunk_id` 列表, 供断点续传时快速跳过;
    - 为每个 chunk 追加写入概念/关系结果到增量 CSV, 保证中途退出时已有成果都在磁盘上;
    - 按块索引定期导出完整 checkpoint CSV, 方便查看不同阶段抽取质量;
    - 提供 `get_summary()` 给状态脚本与日志使用, 让用户一眼看到当前进度概况;
    - 提供 `clear()` 在需要“全量重跑”时一键清空历史 checkpoint。
    """
    
    def __init__(self, checkpoint_dir: str = "output/checkpoints"):
        """初始化 checkpoint 管理器

        参数:
            checkpoint_dir: checkpoint 文件保存目录, 默认 `output/checkpoints`。

        初始化时会:
        - 确保目录存在, 创建 `.progress.json` 与增量 CSV 所在路径;
        - 尝试从已有 `.progress.json` 载入历史进度, 尽量复用之前长时间运行的成果;
        - 在日志中输出已处理块数量, 便于用户确认“当前是续跑还是全新任务”。
        """
        # checkpoint 根目录，默认放在 output/checkpoints 下，可通过配置覆盖
        self.checkpoint_dir = checkpoint_dir
        # 进度信息单独存成 .progress.json，方便外部脚本（status.sh 等）直接读取
        self.progress_file = os.path.join(checkpoint_dir, ".progress.json")
        # 概念结果增量 CSV，每个文本块的抽取结果都会追加到这里
        self.concepts_file = os.path.join(checkpoint_dir, "concepts_incremental.csv")
        # 关系结果增量 CSV，对应 concepts_file，用于快速恢复 DataFrame
        self.relationships_file = os.path.join(checkpoint_dir, "relationships_incremental.csv")
        
        # 确保目录存在，多次调用也不会报错
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        # 启动时尽量复用已有进度，避免一不小心覆盖之前长时间跑出的结果
        self.progress = self._load_progress()
        logger.info(f"Checkpoint manager initialized: {checkpoint_dir}")
        
        # 如果已经有处理过的块，给出一个简短提示，方便用户确认是否为预期行为
        if self.progress["processed_chunks"]:
            logger.info(f"Found existing progress: {len(self.progress['processed_chunks'])} chunks processed")
    
    def _load_progress(self) -> Dict:
        """加载进度文件 `.progress.json`

        优先从 `self.progress_file` 读取历史进度, 包含:
        - `processed_chunks`: 已处理 `chunk_id` 列表;
        - `total_concepts` / `total_relationships`: 增量统计的概念/关系条数;
        - `started_at` / `last_update`: 任务开始时间与最后更新时间。

        若文件不存在(首次运行)或读取失败(损坏等), 会返回一份干净的初始状态,
        避免因为单个 JSON 解析错误导致整个流水线直接崩溃。
        """
        # 正常情况下直接从 .progress.json 恢复；如果文件损坏或不存在，则回退到空进度
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                logger.info(f"Loaded progress from {self.progress_file}")
                return progress
            except Exception as e:
                # 这里选择容忍读取失败，打印警告后重新开始，而不是让整个管道直接崩溃
                logger.warning(f"Failed to load progress file: {e}")
        
        # 进度文件不存在（第一次运行）或读取失败时，初始化一个干净的状态
        return {
            "processed_chunks": [],
            "total_concepts": 0,
            "total_relationships": 0,
            "started_at": datetime.now().isoformat(),
            "last_update": None
        }
    
    def _save_progress(self):
        """保存当前进度到 `.progress.json`

        - 每次更新进度时都会刷新 `last_update` 时间戳;
        - 写入失败仅记为错误日志, 不抛出, 尽量不影响主流程继续运行。
        """
        self.progress["last_update"] = datetime.now().isoformat()
        
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")
    
    def is_processed(self, chunk_id: str) -> bool:
        """检查某个 `chunk_id` 是否已经处理过"""
        return chunk_id in self.progress["processed_chunks"]
    
    def get_processed_chunks(self) -> List[str]:
        """获取已处理的文本块列表(原始 `chunk_id` 列表)"""
        return self.progress["processed_chunks"]
    
    def save_chunk_results(self, chunk_id: str, concepts: List[Dict], 
                          relationships: List[Dict]):
        """保存单个文本块的处理结果(增量模式)

        参数:
            chunk_id: 文本块 ID(形如 `paper1.pdf_0`);
            concepts: 当前块抽取的概念列表(可能为 None, 会被视为 []);
            relationships: 当前块抽取的关系列表(可能为 None, 会被视为 [])。

        行为说明:
        - 将 `None` 统一转换为 `[]`, 防御上层未返回结果的情况;
        - 首次看到某个 `chunk_id` 时, 将其加入 `processed_chunks`, 避免重复统计;
        - 累加 `total_concepts` / `total_relationships`, 为进度监控脚本提供全局统计;
        - 通过 `_append_to_csv` 以“追加写”的方式把数据写入增量 CSV;
        - 调用 `_save_progress()` 刷新 `.progress.json`, 确保中断时进度尽量最新。
        """
        # 防御性编程：LLM 抽取失败时上层可能返回 None，这里统一转成空列表
        if concepts is None:
            concepts = []
        if relationships is None:
            relationships = []
        
        # 只在第一次看到某个 chunk_id 时记录一次，避免重复统计
        if chunk_id not in self.progress["processed_chunks"]:
            self.progress["processed_chunks"].append(chunk_id)
        
        # 这里统计的是“累计条目数”，方便 status.sh 等脚本直接展示抽取规模
        self.progress["total_concepts"] += len(concepts)
        self.progress["total_relationships"] += len(relationships)
        
        # 结果以追加方式写入 CSV，哪怕当前块抽取结果为空也会更新进度
        self._append_to_csv(self.concepts_file, concepts)
        self._append_to_csv(self.relationships_file, relationships)
        
        # 每次保存都刷新进度文件，保证中断时进度尽量最新
        self._save_progress()
        
        logger.debug(f"Saved results for chunk: {chunk_id}")
    
    def _append_to_csv(self, filepath: str, data: List[Dict]):
        """增量追加数据到 CSV 文件

        - 当 `data` 为空时直接返回, 避免产生空行;
        - 若目标文件已存在, 以 `mode='a', header=False` 方式追加写入;
        - 若不存在, 首次创建并写入表头, 方便人工查看和后续用 pandas 直接读取。
        """
        # 某些块可能没有抽取出任何概念或关系，此时直接跳过写盘
        if not data:
            return
        
        df = pd.DataFrame(data)
        
        # 第一次写入带表头，后续统一追加；这样既方便人肉查看，也方便后续用 pandas 直接读
        if os.path.exists(filepath):
            df.to_csv(filepath, mode='a', header=False, index=False, 
                     encoding='utf-8-sig')
        else:
            df.to_csv(filepath, mode='w', header=True, index=False, 
                     encoding='utf-8-sig')
    
    def save_checkpoint(self, chunk_index: int, concepts_df: pd.DataFrame, 
                       relationships_df: pd.DataFrame):
        """保存完整 checkpoint(定期调用)

        参数:
            chunk_index: 当前处理到的块索引(1-based, 便于在日志中直观展示进度);
            concepts_df: 截至当前块为止的“全量概念” DataFrame;
            relationships_df: 截至当前块为止的“全量关系” DataFrame。

        说明:
        - 文件名中包含 `chunk_index` 与时间戳, 例如 `checkpoint_concepts_40_YYYYMMDD_HHMMSS.csv`;
        - 主要用途是: 在长时间运行中, 可以随时打开这些快照观察抽取质量,
          或在需要时手工对某个阶段的数据做离线分析。
        """
        # 文件名里带上 chunk_index + 时间戳，便于快速比对不同阶段的抽取效果
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
            
            logger.info(f"Checkpoint saved at chunk {chunk_index}")
            logger.info(f"  - Concepts: {len(concepts_df)}")
            logger.info(f"  - Relationships: {len(relationships_df)}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def load_incremental_results(self) -> tuple:
        """加载增量保存的结果(增量 CSV → DataFrame)

        返回:
            (concepts_df, relationships_df):
            - concepts_df: 从 `concepts_incremental.csv` 读取到的概念表(可能为空 DataFrame);
            - relationships_df: 从 `relationships_incremental.csv` 读取到的关系表(可能为空 DataFrame)。

        典型使用场景:
        - `continue_processing.py` 在 LLM 抽取阶段结束后, 直接基于增量 CSV 完成“后半程”
          的去重/过滤/汇总, 无需重新跑前半程;
        - 出现异常时, 可通过该方法恢复最近一次中断前的所有已抽取结果。
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
        """清除所有 checkpoint 数据(开始新任务或更换配置时调用)

        - 删除 `.progress.json` 以及增量 CSV;
        - 将 `self.progress` 重置为初始状态, 相当于“忘记之前所有处理记录”；
        - 不会影响最终输出目录下的 `concepts.csv` / `relationships.csv` 等成果文件。
        """
        logger.info("Clearing all checkpoints...")
        
        # 通常在需要“从头重新跑一遍”时调用，旧进度和增量结果会一并删除
        # 注意：这里只影响本地 checkpoint，不会动最终输出的 concepts.csv / relationships.csv
        
        # 删除进度文件
        if os.path.exists(self.progress_file):
            os.remove(self.progress_file)
        
        # 删除增量 CSV
        if os.path.exists(self.concepts_file):
            os.remove(self.concepts_file)
        if os.path.exists(self.relationships_file):
            os.remove(self.relationships_file)
        
        # 重置进度到初始状态，下次 run() 会按全新任务处理
        self.progress = {
            "processed_chunks": [],
            "total_concepts": 0,
            "total_relationships": 0,
            "started_at": datetime.now().isoformat(),
            "last_update": None
        }
        
        logger.info("All checkpoints cleared")
    
    def get_summary(self) -> Dict:
        """获取进度摘要(供日志与监控脚本使用)

        返回的字典结构示例:
        {
            "processed_chunks": 40,
            "total_concepts": 12345,
            "total_relationships": 6789,
            "started_at": "2025-11-29T19:30:00",
            "last_update": "2025-11-29T20:48:15"
        }

        - `enhanced_pipeline_safe.py` 在启动时会读取该摘要并打印“RESUMING from previous checkpoint”；
        - `check_status.py` / `monitor.sh` 之类的工具也会依赖这些字段展示实时进度。
        """
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
