#!/usr/bin/env python3
"""
可视化当前知识图谱
"""
import pandas as pd
from collections import Counter

print("="*80)
print("松材线虫病知识图谱概览")
print("="*80)

# 读取数据
try:
    concepts_df = pd.read_csv('output/concepts.csv')
    relations_df = pd.read_csv('output/relationships.csv')
except Exception as e:
    print(f"错误: 无法读取文件 - {e}")
    exit(1)

print(f"\n📊 基本统计")
print(f"  实体总数: {len(concepts_df)}")
print(f"  关系总数: {len(relations_df)}")

# 核心实体（重要性>=4）
print(f"\n⭐ 核心实体（重要性>=4）")
core_entities = concepts_df[concepts_df['importance'] >= 4].sort_values('importance', ascending=False)
for idx, row in core_entities.head(20).iterrows():
    entity = str(row['entity'])
    if len(entity) > 30:
        entity = entity[:27] + "..."
    print(f"  [{row['importance']}] {entity:35s} ({row['category']})")

# 类别分布
print(f"\n📁 实体类别分布")
category_counts = concepts_df['category'].value_counts()
for cat, count in category_counts.head(10).items():
    pct = count / len(concepts_df) * 100
    print(f"  {cat:20s}: {count:3d} ({pct:5.1f}%)")

# 关系类型（简化显示）
print(f"\n🔗 主要关系类型（前15个）")
# 提取关系类型
if 'edge' in relations_df.columns:
    edge_col = 'edge'
elif 'relationship' in relations_df.columns:
    edge_col = 'relationship'
else:
    edge_col = relations_df.columns[2]  # 假设第三列是关系类型

edge_counts = relations_df[edge_col].value_counts()
for edge, count in edge_counts.head(15).items():
    edge_display = edge if len(edge) <= 40 else edge[:37] + "..."
    pct = count / len(relations_df) * 100
    print(f"  {edge_display:42s}: {count:3d} ({pct:5.1f}%)")

# 核心关系示例
print(f"\n🌐 核心关系示例（权重最高的10个）")
if 'weight' in relations_df.columns:
    top_relations = relations_df.nlargest(10, 'weight')
    for idx, row in top_relations.iterrows():
        node1 = row['node_1'] if len(row['node_1']) <= 20 else row['node_1'][:17] + "..."
        node2 = row['node_2'] if len(row['node_2']) <= 20 else row['node_2'][:17] + "..."
        edge = row[edge_col] if len(row[edge_col]) <= 25 else row[edge_col][:22] + "..."
        weight = row['weight']
        print(f"  {node1:22s} --[{edge:27s}]--> {node2:22s} (权重: {weight:.3f})")
else:
    print("  (权重信息不可用)")

# 关键实体的连接度
print(f"\n🔝 连接度最高的实体（前10个）")
node1_counts = Counter(relations_df['node_1'])
node2_counts = Counter(relations_df['node_2'])
all_nodes = node1_counts + node2_counts
for node, count in all_nodes.most_common(10):
    node_display = node if len(node) <= 35 else node[:32] + "..."
    print(f"  {node_display:37s}: {count:3d} 个连接")

# 问题检测
print(f"\n⚠️  数据质量问题")
issues = []

# 检查空实体
empty_entities = concepts_df[concepts_df['entity'].str.strip() == '']
if len(empty_entities) > 0:
    issues.append(f"空实体: {len(empty_entities)} 个")

# 检查乱码（包含\u的Unicode转义）
garbled = concepts_df[concepts_df['entity'].str.contains(r'\\u[0-9a-f]{4}', regex=True, na=False)]
if len(garbled) > 0:
    issues.append(f"乱码实体: {len(garbled)} 个")
    print(f"  乱码实体示例:")
    for entity in garbled['entity'].head(5):
        print(f"    - {entity}")

# 检查过短实体
short_entities = concepts_df[concepts_df['entity'].str.len() < 2]
if len(short_entities) > 0:
    issues.append(f"过短实体(<2字符): {len(short_entities)} 个")

# 检查"其他"类别占比
other_pct = (concepts_df['category'] == '其他').sum() / len(concepts_df) * 100
if other_pct > 50:
    issues.append(f"'其他'类别占比过高: {other_pct:.1f}%")

if issues:
    for issue in issues:
        print(f"  ⚠️  {issue}")
else:
    print(f"  ✅ 未发现明显问题")

# 关系来源分布
if 'source' in relations_df.columns:
    print(f"\n📍 关系来源分布")
    source_counts = relations_df['source'].value_counts()
    for source, count in source_counts.items():
        pct = count / len(relations_df) * 100
        print(f"  {source:20s}: {count:3d} ({pct:5.1f}%)")

print("\n" + "="*80)
print("✓ 图谱概览生成完成")
print("="*80)
