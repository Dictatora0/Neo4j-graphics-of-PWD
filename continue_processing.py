#!/usr/bin/env python3
"""
继续处理现有checkpoint数据
完成去重、过滤和导出步骤
"""

import pandas as pd
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from concept_deduplicator import (
    ConceptDeduplicator,
    RelationshipDeduplicator,
    ConceptImportanceFilter,
    SentenceTransformerEmbedding
)
from logger_config import get_logger

logger = get_logger('ContinueProcessing')


def main():
    """主处理流程"""
    # 该脚本只做“后半程”: 基于 checkpoint 导出的 CSV 完成去重、过滤和最终汇总
    logger.info("="*60)
    logger.info("继续处理现有checkpoint数据")
    logger.info("="*60)
    
    # 1. 读取incremental数据
    logger.info("\n[Step 1/4] 读取checkpoint数据...")
    
    concepts_file = Path("output/checkpoints/concepts_incremental.csv")
    relationships_file = Path("output/checkpoints/relationships_incremental.csv")
    
    if not concepts_file.exists():
        logger.error(f"找不到概念文件: {concepts_file}")
        return
    
    if not relationships_file.exists():
        logger.error(f"找不到关系文件: {relationships_file}")
        return
    
    concepts_df = pd.read_csv(concepts_file, encoding='utf-8-sig')
    relationships_df = pd.read_csv(relationships_file, encoding='utf-8-sig')
    
    logger.info(f"  - 概念数量: {len(concepts_df)}")
    logger.info(f"  - 关系数量: {len(relationships_df)}")
    logger.info(f"  - 唯一概念: {concepts_df['entity'].nunique()}")
    
    # 2. 语义去重
    logger.info("\n[Step 2/4] 语义去重与实体对齐...")
    
    try:
        embedding_provider = SentenceTransformerEmbedding()
        deduplicator = ConceptDeduplicator(
            embedding_provider=embedding_provider,
            similarity_threshold=0.85
        )
        
        logger.info("  - 开始去重...")
        deduplicated_concepts_df, concept_mapping = deduplicator.deduplicate_concepts(concepts_df)
        
        logger.info(f"  - 去重后概念数量: {len(deduplicated_concepts_df)}")
        logger.info(f"  - 合并概念对数量: {len([k for k, v in concept_mapping.items() if k != v])}")
        
        # 更新关系
        logger.info("  - 更新关系端点...")
        updated_relationships_df = RelationshipDeduplicator.update_relationships(
            relationships_df, concept_mapping
        )
        
        logger.info(f"  - 更新后关系数量: {len(updated_relationships_df)}")
        
    except Exception as e:
        logger.warning(f"  - 语义去重失败，跳过此步骤: {e}")
        deduplicated_concepts_df = concepts_df
        updated_relationships_df = relationships_df
    
    # 3. 重要性过滤
    logger.info("\n[Step 3/4] 重要性与连通度过滤...")
    
    try:
        concept_filter = ConceptImportanceFilter()
        filtered_concepts_df = concept_filter.filter_concepts(
            deduplicated_concepts_df,
            updated_relationships_df,
            min_importance=2,
            min_connections=1
        )
        
        logger.info(f"  - 过滤后概念数量: {len(filtered_concepts_df)}")
        
        # 过滤关系（只保留两端都存在的关系）
        valid_entities = set(filtered_concepts_df['entity'].str.lower())
        filtered_relationships_df = updated_relationships_df[
            (updated_relationships_df['node_1'].str.lower().isin(valid_entities)) &
            (updated_relationships_df['node_2'].str.lower().isin(valid_entities))
        ].copy()
        
        logger.info(f"  - 过滤后关系数量: {len(filtered_relationships_df)}")
        
    except Exception as e:
        logger.warning(f"  - 过滤失败，使用去重后数据: {e}")
        filtered_concepts_df = deduplicated_concepts_df
        filtered_relationships_df = updated_relationships_df
    
    # 4. 保存最终结果
    logger.info("\n[Step 4/4] 保存最终结果...")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    concepts_output = output_dir / "concepts.csv"
    relationships_output = output_dir / "relationships.csv"
    
    filtered_concepts_df.to_csv(concepts_output, index=False, encoding='utf-8-sig')
    filtered_relationships_df.to_csv(relationships_output, index=False, encoding='utf-8-sig')
    
    logger.info(f"  - 概念文件: {concepts_output}")
    logger.info(f"  - 关系文件: {relationships_output}")
    
    # 统计信息
    logger.info("\n" + "="*60)
    logger.info("处理完成！最终统计:")
    logger.info("="*60)
    logger.info(f"概念数量: {len(filtered_concepts_df)}")
    logger.info(f"关系数量: {len(filtered_relationships_df)}")
    logger.info(f"概念类别分布:")
    
    if 'category' in filtered_concepts_df.columns:
        category_counts = filtered_concepts_df['category'].value_counts()
        for category, count in category_counts.items():
            logger.info(f"  - {category}: {count}")
    
    logger.info(f"\n输出文件:")
    logger.info(f"  - {concepts_output}")
    logger.info(f"  - {relationships_output}")
    logger.info("\n可以使用以下命令导入Neo4j:")
    logger.info("  python import_to_neo4j_final.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n用户中断处理")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n处理失败: {e}", exc_info=True)
        sys.exit(1)
