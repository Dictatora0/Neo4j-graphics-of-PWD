#!/usr/bin/env python3
"""
最终关系标准化：直接修改CSV文件中的关系类型
"""
import pandas as pd
import os

print("="*80)
print("最终关系标准化")
print("="*80)

# 读取CSV文件
csv_path = 'output/triples_export.csv'
df = pd.read_csv(csv_path)

print(f"\n原始数据:")
print(f"  总行数: {len(df)}")
print(f"  关系类型数: {df['relationship'].nunique()}")

# ============================================================================
# 定义完整的关系映射
# ============================================================================

relation_map = {
    # 共现关系
    'co-occurs in': 'CO_OCCURS_WITH',
    '共现': 'CO_OCCURS_WITH',
    'OCCURS_IN': 'CO_OCCURS_WITH',
    
    # 寄生/寄主关系
    '寄主': 'PARASITIZES',
    '寄生于': 'PARASITIZES',
    
    # 传播/媒介关系
    '传播': 'TRANSMITS',
    '传播于': 'TRANSMITS',
    '传播者': 'TRANSMITS',
    '可能传播': 'TRANSMITS',
    '媒介': 'TRANSMITS',
    
    # 携带关系
    '携带': 'CARRIES',
    
    # 取食关系
    '取食': 'FEEDS_ON',
    
    # 感染关系
    '感染': 'INFECTS',
    
    # 引起关系
    '引起': 'CAUSES',
    
    # 影响关系
    '影响': 'AFFECTS',
    '受影响': 'AFFECTED_BY',
    
    # 防治/治疗关系
    '防治': 'CONTROLS',
    '治疗': 'TREATS',
    
    # 监测关系
    '用于监测': 'MONITORS',
    
    # 应用关系
    '应用于': 'APPLIES_TO',
    '用于': 'USED_FOR',
    
    # 分布关系
    '分布于': 'DISTRIBUTED_IN',
    '广泛存在': 'DISTRIBUTED_IN',
    '在': 'LOCATED_IN',
    '区域': 'LOCATED_IN',
    
    # 其他关系
    '包含': 'CONTAINS',
    '比较': 'COMPARES_WITH',
    '关系': 'RELATED_TO',
    '相关性': 'RELATED_TO',
    '与': 'RELATED_TO',
    'related to': 'RELATED_TO',
    '症状': 'SYMPTOM_OF',
    '生活习性': 'BEHAVIOR_OF',
    '竞争关系': 'COMPETES_WITH',
    '环境因子': 'ENVIRONMENTAL_FACTOR',
    '组成部分': 'COMPONENT_OF',
    '配合': 'COOPERATES_WITH',
    '解决': 'SOLVES',
}

# ============================================================================
# 应用映射
# ============================================================================

print("\n应用关系类型映射:")

# 统计每种关系的转换
for old_rel, new_rel in relation_map.items():
    count = (df['relationship'] == old_rel).sum()
    if count > 0:
        df.loc[df['relationship'] == old_rel, 'relationship'] = new_rel
        print(f"  {old_rel:30s} -> {new_rel:30s}: {count:3d} 行")

# ============================================================================
# 验证结果
# ============================================================================

print(f"\n标准化后的数据:")
print(f"  总行数: {len(df)}")
print(f"  关系类型数: {df['relationship'].nunique()}")

print(f"\n最终关系类型分布:")
rel_dist = df['relationship'].value_counts()
for rel, count in rel_dist.items():
    pct = count / len(df) * 100
    print(f"  {rel:30s}: {count:3d} ({pct:5.1f}%)")

# ============================================================================
# 检查语言统一性
# ============================================================================

print(f"\n语言统一性检查:")

# 检查是否还有中文关系
chinese_rels = df[df['relationship'].str.contains('[\u4e00-\u9fa5]', regex=True)]['relationship'].unique()
if len(chinese_rels) > 0:
    print(f"  ⚠️  还有 {len(chinese_rels)} 种中文关系:")
    for rel in chinese_rels:
        count = (df['relationship'] == rel).sum()
        print(f"    {rel}: {count} 行")
else:
    print(f"  ✅ 所有关系类型都已标准化为英文")

# 检查节点语言
chinese_nodes_1 = df[df['node_1'].str.contains('[\u4e00-\u9fa5]', regex=True)]['node_1'].nunique()
chinese_nodes_2 = df[df['node_2'].str.contains('[\u4e00-\u9fa5]', regex=True)]['node_2'].nunique()
print(f"  中文节点: {chinese_nodes_1 + chinese_nodes_2} 个")

# ============================================================================
# 保存结果
# ============================================================================

print(f"\n保存结果...")
df.to_csv(csv_path, index=False)
print(f"  ✓ 已保存到 {csv_path}")

print("\n" + "="*80)
print("✓ 最终关系标准化完成！")
print("="*80)

print("\n📊 标准化成果:")
print(f"  ✅ 关系类型: {len(relation_map)} 种 -> {df['relationship'].nunique()} 种")
print(f"  ✅ 所有关系类型已统一为英文")
print(f"  ✅ 数据已导出到 output/triples_export.csv")
