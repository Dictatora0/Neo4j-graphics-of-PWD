#!/usr/bin/env python3
"""
将 Neo4j 数据库中的所有三元组导出到 CSV 文件
"""

from neo4j import GraphDatabase
import pandas as pd
import os
from datetime import datetime

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

OUTPUT_DIR = "output"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, f"neo4j_export_{TIMESTAMP}.csv")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 80)
print("从 Neo4j 导出三元组到 CSV")
print("=" * 80)

with driver.session() as session:
    # 查询所有三元组
    query = """
    MATCH (s)-[r]->(t)
    RETURN 
        s.name as node_1,
        type(r) as relationship,
        t.name as node_2,
        r.weight as weight,
        labels(s)[0] as node_1_type,
        labels(t)[0] as node_2_type
    ORDER BY s.name, type(r), t.name
    """
    
    print("\n查询 Neo4j 数据库...")
    result = session.run(query)
    records = list(result)
    
    print(f"查询完成，共 {len(records)} 条三元组")
    
    # 转换为 DataFrame
    df = pd.DataFrame([dict(record) for record in records])
    
    # 只保留基本列（与原始 triples_export.csv 格式一致）
    df_export = df[["node_1", "relationship", "node_2", "weight"]].copy()
    
    # 保存到 CSV
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df_export.to_csv(OUTPUT_PATH, index=False)
    
    print(f"\n已导出到: {OUTPUT_PATH}")
    print(f"  总行数: {len(df_export)}")
    print(f"  关系类型数: {df_export['relationship'].nunique()}")
    print(f"  唯一节点数: {len(set(df_export['node_1'].unique()) | set(df_export['node_2'].unique()))}")
    
    # 打印统计信息
    print("\n关系类型分布:")
    rel_dist = df_export['relationship'].value_counts()
    for rel_type, count in rel_dist.items():
        print(f"  {rel_type:20s}: {count:3d}")
    
    # 打印节点类型分布
    print("\n节点类型分布:")
    node_type_dist = pd.concat([
        df['node_1_type'].value_counts(),
        df['node_2_type'].value_counts()
    ]).groupby(level=0).sum().sort_values(ascending=False)
    for node_type, count in node_type_dist.items():
        print(f"  {node_type:20s}: {count:3d}")
    
    # 打印权重统计
    print("\n权重统计:")
    print(f"  最小值: {df_export['weight'].min():.4f}")
    print(f"  最大值: {df_export['weight'].max():.4f}")
    print(f"  平均值: {df_export['weight'].mean():.4f}")
    print(f"  中位数: {df_export['weight'].median():.4f}")
    
    # 创建带详细信息的导出版本（包含节点类型）
    OUTPUT_DETAILED_PATH = os.path.join(OUTPUT_DIR, f"neo4j_export_detailed_{TIMESTAMP}.csv")
    df.to_csv(OUTPUT_DETAILED_PATH, index=False)
    print(f"\n详细版本已导出到: {OUTPUT_DETAILED_PATH}")
    print("  包含列: node_1, relationship, node_2, weight, node_1_type, node_2_type")

print("\n" + "=" * 80)
print("导出完成")
print("=" * 80)

driver.close()
