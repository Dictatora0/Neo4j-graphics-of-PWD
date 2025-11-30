#!/usr/bin/env python3
"""
将concepts.csv和relationships.csv转换为三元组格式
"""

import pandas as pd
from pathlib import Path

def main():
    print("="*60)
    print("转换为三元组格式")
    print("="*60)
    
    # 读取数据
    concepts_df = pd.read_csv("output/concepts.csv", encoding='utf-8-sig')
    relationships_df = pd.read_csv("output/relationships.csv", encoding='utf-8-sig')
    
    print(f"\n读取数据:")
    print(f"  - 概念: {len(concepts_df)}")
    print(f"  - 关系: {len(relationships_df)}")
    
    # 创建实体ID映射
    entity_to_id = {
        row['entity'].lower(): f"E{i+1:04d}" 
        for i, row in concepts_df.iterrows()
    }
    
    # 转换为三元组格式
    triples = []
    
    for _, rel in relationships_df.iterrows():
        node1 = rel['node_1'].lower()
        node2 = rel['node_2'].lower()
        edge = rel['edge']
        
        if node1 in entity_to_id and node2 in entity_to_id:
            # 获取概念信息
            concept1 = concepts_df[concepts_df['entity'].str.lower() == node1].iloc[0]
            concept2 = concepts_df[concepts_df['entity'].str.lower() == node2].iloc[0]
            
            # 获取权重（如果有的话）
            weight = rel.get('weight', 0.8)
            
            triples.append({
                'node_1': concept1['entity'],
                'node_1_type': concept1.get('category', 'other'),
                'relationship': edge,
                'node_2': concept2['entity'],
                'node_2_type': concept2.get('category', 'other'),
                'weight': weight
            })
    
    # 保存三元组
    triples_df = pd.DataFrame(triples)
    output_file = "output/triples_export.csv"
    triples_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"\n转换完成:")
    print(f"  - 三元组数量: {len(triples_df)}")
    print(f"  - 输出文件: {output_file}")
    print(f"\n可以执行以下命令导入Neo4j:")
    print(f"  python import_to_neo4j_final.py")

if __name__ == "__main__":
    main()
