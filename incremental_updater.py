"""
增量更新模块
支持只处理新增的PDF文件，避免重复处理已处理的文件
"""

import os
import pandas as pd
from pathlib import Path
from typing import Set, List, Dict
from datetime import datetime
from logger_config import get_logger

logger = get_logger('IncrementalUpdater')


class IncrementalUpdater:
    """增量更新管理器"""
    
    def __init__(self, output_dir: str = "./output"):
        """初始化增量更新管理器
        
        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.processed_files_path = self.output_dir / "processed_files.txt"
        self.processed_files = self.load_processed_list()
        
        logger.info(f"增量更新管理器已初始化，已处理 {len(self.processed_files)} 个文件")
    
    def load_processed_list(self) -> Set[str]:
        """加载已处理的文件列表
        
        Returns:
            已处理文件名的集合
        """
        if not self.processed_files_path.exists():
            logger.info("未找到已处理文件列表，将创建新列表")
            return set()
        
        try:
            with open(self.processed_files_path, 'r', encoding='utf-8') as f:
                files = set(line.strip() for line in f if line.strip())
            logger.info(f"已加载 {len(files)} 个已处理文件")
            return files
        except Exception as e:
            logger.error(f"加载已处理文件列表失败: {e}")
            return set()
    
    def save_processed_list(self, files: Set[str]):
        """保存已处理的文件列表
        
        Args:
            files: 已处理文件名的集合
        """
        try:
            with open(self.processed_files_path, 'w', encoding='utf-8') as f:
                for file in sorted(files):
                    f.write(f"{file}\n")
            logger.info(f"已保存 {len(files)} 个已处理文件")
        except Exception as e:
            logger.error(f"保存已处理文件列表失败: {e}")
    
    def get_new_files(self, pdf_dir: str) -> List[str]:
        """获取新增的 PDF 文件
        
        Args:
            pdf_dir: PDF 文件目录
        
        Returns:
            新增文件列表
        """
        all_files = set(f for f in os.listdir(pdf_dir) if f.endswith('.pdf'))
        new_files = all_files - self.processed_files
        
        logger.info(f"扫描目录: {pdf_dir}")
        logger.info(f"  总文件数: {len(all_files)}")
        logger.info(f"  已处理: {len(self.processed_files)}")
        logger.info(f"  新增文件: {len(new_files)}")
        
        return sorted(list(new_files))
    
    def mark_as_processed(self, filename: str):
        """标记文件为已处理
        
        Args:
            filename: 文件名
        """
        self.processed_files.add(filename)
        self.save_processed_list(self.processed_files)
    
    def mark_batch_as_processed(self, filenames: List[str]):
        """批量标记文件为已处理
        
        Args:
            filenames: 文件名列表
        """
        self.processed_files.update(filenames)
        self.save_processed_list(self.processed_files)
        logger.info(f"已标记 {len(filenames)} 个文件为已处理")
    
    def merge_entities(self, old_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
        """合并旧实体数据和新实体数据
        
        Args:
            old_df: 旧实体数据
            new_df: 新实体数据
        
        Returns:
            合并后的实体数据
        """
        if old_df.empty:
            logger.info("无旧数据，直接使用新数据")
            return new_df
        
        if new_df.empty:
            logger.info("无新数据，保留旧数据")
            return old_df
        
        logger.info(f"合并实体数据: 旧 {len(old_df)} + 新 {len(new_df)}")
        
        # 合并
        combined = pd.concat([old_df, new_df], ignore_index=True)
        
        # 去重（按 name + type）
        before_dedup = len(combined)
        combined = combined.drop_duplicates(subset=['name', 'type'], keep='first')
        after_dedup = len(combined)
        
        # 重新分配 ID
        combined = combined.reset_index(drop=True)
        combined['id'] = range(1, len(combined) + 1)
        combined = combined[['id', 'name', 'type', 'source_pdf']]
        
        logger.info(f"  合并后: {before_dedup} 个")
        logger.info(f"  去重后: {after_dedup} 个")
        logger.info(f"  移除重复: {before_dedup - after_dedup} 个")
        
        return combined
    
    def merge_relations(self, old_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
        """合并旧关系数据和新关系数据
        
        Args:
            old_df: 旧关系数据
            new_df: 新关系数据
        
        Returns:
            合并后的关系数据
        """
        if old_df.empty:
            logger.info("无旧数据，直接使用新数据")
            return new_df
        
        if new_df.empty:
            logger.info("无新数据，保留旧数据")
            return old_df
        
        logger.info(f"合并关系数据: 旧 {len(old_df)} + 新 {len(new_df)}")
        
        # 合并
        combined = pd.concat([old_df, new_df], ignore_index=True)
        
        # 去重（按 head + relation + tail）
        before_dedup = len(combined)
        combined = combined.drop_duplicates(subset=['head', 'relation', 'tail'], keep='first')
        after_dedup = len(combined)
        
        # 重置索引
        combined = combined.reset_index(drop=True)
        
        logger.info(f"  合并后: {before_dedup} 个")
        logger.info(f"  去重后: {after_dedup} 个")
        logger.info(f"  移除重复: {before_dedup - after_dedup} 个")
        
        return combined
    
    def backup_current_results(self):
        """备份当前的输出文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = self.output_dir / f"backup_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        files_to_backup = [
            'entities_clean.csv',
            'relations_clean.csv',
            'statistics_report.txt'
        ]
        
        backed_up = 0
        for filename in files_to_backup:
            src = self.output_dir / filename
            if src.exists():
                dst = backup_dir / filename
                import shutil
                shutil.copy2(src, dst)
                backed_up += 1
        
        if backed_up > 0:
            logger.info(f"已备份 {backed_up} 个文件到: {backup_dir}")
        
        return backup_dir if backed_up > 0 else None


if __name__ == "__main__":
    # 测试增量更新管理器
    updater = IncrementalUpdater()
    
    # 获取新文件
    new_files = updater.get_new_files("./文献")
    print(f"新增文件: {new_files}")
    
    # 测试合并
    old_entities = pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['松材线虫病', '松材线虫', '马尾松'],
        'type': ['Disease', 'Pathogen', 'Host'],
        'source_pdf': ['old.pdf'] * 3
    })
    
    new_entities = pd.DataFrame({
        'id': [1, 2],
        'name': ['松材线虫病', '黑松'],  # 第一个重复
        'type': ['Disease', 'Host'],
        'source_pdf': ['new.pdf'] * 2
    })
    
    merged = updater.merge_entities(old_entities, new_entities)
    print(f"\n合并结果:")
    print(merged)

