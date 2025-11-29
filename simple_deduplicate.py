#!/usr/bin/env python3
"""
简单去重脚本（不依赖 BGE-M3）
使用基于文本的相似度进行去重
"""

import pandas as pd
from difflib import SequenceMatcher

def text_similarity(a: str, b: str) -> float:
    """计算两个字符串的相似度"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def deduplicate_concepts(concepts_df: pd.DataFrame, threshold: float = 0.85) -> pd.DataFrame:
    """
    基于文本相似度去重概念
    
    Args:
        concepts_df: 概念 DataFrame
        threshold: 相似度阈值（0-1）
    """
    if concepts_df.empty:
        return concepts_df
    
    print(f"\n原始概念数: {len(concepts_df)}")
    
    # 按重要性排序（保留更重要的）
    concepts_df = concepts_df.sort_values('importance', ascending=False)
    
    keep_indices = []
    removed_count = 0
    
    for i, row in concepts_df.iterrows():
        # 检查是否与已保留的概念重复
        is_duplicate = False
        for j in keep_indices:
            existing = concepts_df.loc[j]
            similarity = text_similarity(row['entity'], existing['entity'])
            
            if similarity >= threshold:
                is_duplicate = True
                removed_count += 1
                print(f"  去重: '{row['entity']}' ≈ '{existing['entity']}' (相似度: {similarity:.2f})")
                break
        
        if not is_duplicate:
            keep_indices.append(i)
    
    result = concepts_df.loc[keep_indices].reset_index(drop=True)
    print(f"去重后概念数: {len(result)}")
    print(f"移除重复: {removed_count} 个\n")
    
    return result

def main():
    print("\n" + "="*70)
    print(" 简单去重工具（基于文本相似度）")
    print("="*70 + "\n")
    
    # 读取数据
    concepts_file = "output/concepts.csv"
    relationships_file = "output/relationships.csv"
    
    try:
        concepts_df = pd.read_csv(concepts_file)
        relationships_df = pd.read_csv(relationships_file)
    except FileNotFoundError as e:
        print(f"❌ 文件不存在: {e}")
        print("\n请先运行主管道生成结果文件")
        return
    
    print(f"✓ 读取概念: {len(concepts_df)} 个")
    print(f"✓ 读取关系: {len(relationships_df)} 个")
    
    # 去重概念
    print("\n" + "-"*70)
    print(" 开始去重...")
    print("-"*70)
    
    deduplicated_concepts = deduplicate_concepts(concepts_df, threshold=0.85)
    
    # 更新关系（移除指向已删除概念的关系）
    valid_entities = set(deduplicated_concepts['entity'].unique())
    
    original_rel_count = len(relationships_df)
    relationships_df = relationships_df[
        relationships_df['node_1'].isin(valid_entities) &
        relationships_df['node_2'].isin(valid_entities)
    ].reset_index(drop=True)
    
    removed_rel_count = original_rel_count - len(relationships_df)
    print(f"关系去重: 移除 {removed_rel_count} 个无效关系")
    
    # 保存结果
    output_concepts = "output/concepts_deduplicated.csv"
    output_relationships = "output/relationships_deduplicated.csv"
    
    deduplicated_concepts.to_csv(output_concepts, index=False, encoding='utf-8-sig')
    relationships_df.to_csv(output_relationships, index=False, encoding='utf-8-sig')
    
    print("\n" + "="*70)
    print(" ✅ 去重完成")
    print("="*70)
    print(f"\n输出文件:")
    print(f"  • {output_concepts}")
    print(f"  • {output_relationships}")
    print(f"\n统计:")
    print(f"  • 概念: {len(concepts_df)} → {len(deduplicated_concepts)} (-{len(concepts_df) - len(deduplicated_concepts)})")
    print(f"  • 关系: {original_rel_count} → {len(relationships_df)} (-{removed_rel_count})")
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()
