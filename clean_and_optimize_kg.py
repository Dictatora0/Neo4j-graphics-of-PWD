#!/usr/bin/env python3
"""
知识图谱数据清洗和优化
修复：乱码实体、空实体、复杂关系类型、类别分布不均
"""
import pandas as pd
import re
from collections import Counter

print("="*80)
print("知识图谱数据清洗和优化")
print("="*80)

# ============================================================================
# 1. 读取原始数据
# ============================================================================
print("\n📖 读取原始数据...")
concepts_df = pd.read_csv('output/concepts.csv')
relationships_df = pd.read_csv('output/relationships.csv')

print(f"  原始概念数: {len(concepts_df)}")
print(f"  原始关系数: {len(relationships_df)}")

# ============================================================================
# 2. 清理实体
# ============================================================================
print("\n🧹 清理实体...")

# 2.1 移除空实体
empty_mask = concepts_df['entity'].isna() | (concepts_df['entity'].astype(str).str.strip() == '') | (concepts_df['entity'].astype(str) == 'nan')
empty_count = empty_mask.sum()
concepts_df = concepts_df[~empty_mask]
print(f"  ✓ 移除空实体: {empty_count} 个")

# 2.2 移除乱码实体（包含\u转义序列）
garbled_mask = concepts_df['entity'].astype(str).str.contains(r'\\u[0-9a-f]{4}', regex=True, na=False)
garbled_entities = concepts_df[garbled_mask]['entity'].tolist()
garbled_count = garbled_mask.sum()
concepts_df = concepts_df[~garbled_mask]
print(f"  ✓ 移除乱码实体: {garbled_count} 个")
if garbled_entities:
    print(f"    示例: {garbled_entities[:3]}")

# 2.3 移除过短实体（<2字符）
short_mask = concepts_df['entity'].astype(str).str.len() < 2
short_count = short_mask.sum()
concepts_df = concepts_df[~short_mask]
print(f"  ✓ 移除过短实体: {short_count} 个")

# 2.4 移除重复实体
dup_count = concepts_df.duplicated(subset=['entity']).sum()
concepts_df = concepts_df.drop_duplicates(subset=['entity'], keep='first')
print(f"  ✓ 移除重复实体: {dup_count} 个")

# 2.5 改进类别分类
print("\n🏷️  改进实体类别...")

# 定义类别映射规则
category_rules = {
    '疾病': ['病', '病害', 'disease', 'pwd', '线虫病'],
    '病原体': ['线虫', 'nematode', 'xylophilus', 'bursaphelenchus', '细菌', 'bacteria'],
    '媒介': ['天牛', 'beetle', 'monochamus', 'alternatus', '墨天牛', '褐梗'],
    '寄主': ['松', 'pine', 'pinus', '马尾松', '黑松', '湿地松', 'thunbergii', 'massoniana'],
    '症状': ['叶片', '枯萎', '变色', '萎蔫', '针叶', 'leaf', 'symptom'],
    '防治': ['防治', '诱捕', '生物防治', '药剂', 'control', 'treatment', '治疗'],
    '环境': ['温度', '湿度', '海拔', '气候', 'temperature', 'climate', '降水'],
    '地点': ['疫区', '分布区', '风景区', '县', '市', '省', 'area', 'region'],
    '技术': ['光谱', '遥感', '监测', 'spectral', 'sentinel', 'detection', '数据'],
}

def classify_entity(entity_name, current_category):
    """根据实体名称重新分类"""
    entity_lower = str(entity_name).lower()
    
    # 如果当前类别不是"其他"，保持原分类
    if current_category not in ['其他', 'misc', 'other']:
        return current_category
    
    # 根据规则重新分类
    for category, keywords in category_rules.items():
        for keyword in keywords:
            if keyword in entity_lower:
                return category
    
    return '其他'

concepts_df['category'] = concepts_df.apply(
    lambda row: classify_entity(row['entity'], row['category']), 
    axis=1
)

# 统计新的类别分布
new_category_dist = concepts_df['category'].value_counts()
print("  新类别分布:")
for cat, count in new_category_dist.items():
    pct = count / len(concepts_df) * 100
    print(f"    {cat:15s}: {count:3d} ({pct:5.1f}%)")

# ============================================================================
# 3. 清理关系
# ============================================================================
print("\n🔗 清理关系...")

# 3.1 移除涉及已删除实体的关系
valid_entities = set(concepts_df['entity'].astype(str))
before_rel_count = len(relationships_df)

relationships_df = relationships_df[
    relationships_df['node_1'].astype(str).isin(valid_entities) &
    relationships_df['node_2'].astype(str).isin(valid_entities)
]
removed_rel_count = before_rel_count - len(relationships_df)
print(f"  ✓ 移除无效关系: {removed_rel_count} 个")

# 3.2 简化复杂关系类型
print("\n🎯 简化关系类型...")

def simplify_edge(edge_str):
    """简化复杂的关系类型"""
    edge = str(edge_str)
    
    # 如果关系类型过长或包含多个"|"，提取主要关系
    if len(edge) > 50 or edge.count('|') > 2:
        # 提取关键关系词
        parts = [p.strip() for p in edge.split('|')]
        
        # 优先级关系词
        priority_relations = ['寄生于', '传播', '引起', '感染', '媒介', '防治', '影响']
        
        for rel in priority_relations:
            if rel in parts:
                return rel
        
        # 如果没有优先关系，返回第一个非co-occurs的关系
        for part in parts:
            if part != 'co-occurs in' and part.strip():
                return part.strip()
        
        return 'co-occurs in'
    
    return edge

relationships_df['edge_original'] = relationships_df['edge']
relationships_df['edge'] = relationships_df['edge'].apply(simplify_edge)

# 统计简化效果
simplified_count = (relationships_df['edge'] != relationships_df['edge_original']).sum()
print(f"  ✓ 简化复杂关系: {simplified_count} 个")

# 3.3 合并重复关系（保留最高权重）
print("\n🔄 合并重复关系...")
before_merge = len(relationships_df)

relationships_df = relationships_df.groupby(['node_1', 'node_2', 'edge'], as_index=False).agg({
    'weight': 'max',
    'source': lambda x: ','.join(sorted(set(','.join(x).split(',')))),
    'chunk_id': 'first'
})

merged_count = before_merge - len(relationships_df)
print(f"  ✓ 合并重复关系: {merged_count} 个")

# ============================================================================
# 4. 统计清洗结果
# ============================================================================
print("\n📊 清洗结果统计")
print("="*80)

print(f"\n实体:")
print(f"  清洗前: {len(pd.read_csv('output/concepts.csv'))} 个")
print(f"  清洗后: {len(concepts_df)} 个")
print(f"  移除: {len(pd.read_csv('output/concepts.csv')) - len(concepts_df)} 个")

print(f"\n关系:")
print(f"  清洗前: {len(pd.read_csv('output/relationships.csv'))} 个")
print(f"  清洗后: {len(relationships_df)} 个")
print(f"  移除/合并: {len(pd.read_csv('output/relationships.csv')) - len(relationships_df)} 个")

# 关系类型分布
print(f"\n关系类型分布（前10）:")
edge_counts = relationships_df['edge'].value_counts()
for edge, count in edge_counts.head(10).items():
    pct = count / len(relationships_df) * 100
    edge_display = edge if len(edge) <= 30 else edge[:27] + "..."
    print(f"  {edge_display:32s}: {count:3d} ({pct:5.1f}%)")

# 关系来源分布
print(f"\n关系来源分布:")
source_counts = relationships_df['source'].value_counts()
for source, count in source_counts.items():
    pct = count / len(relationships_df) * 100
    print(f"  {source:25s}: {count:3d} ({pct:5.1f}%)")

# ============================================================================
# 5. 保存清洗后的数据
# ============================================================================
print("\n💾 保存清洗后的数据...")

# 保存到新文件
concepts_df.to_csv('output/concepts_cleaned.csv', index=False, encoding='utf-8-sig')
relationships_df.to_csv('output/relationships_cleaned.csv', index=False, encoding='utf-8-sig')

print(f"  ✓ 已保存: output/concepts_cleaned.csv")
print(f"  ✓ 已保存: output/relationships_cleaned.csv")

# 同时更新Neo4j导入文件
print("\n🔄 更新Neo4j导入文件...")

# 生成nodes.csv
nodes_df = pd.DataFrame({
    'id': range(len(concepts_df)),
    'name': concepts_df['entity'],
    'label': concepts_df['category']
})
nodes_df.to_csv('output/neo4j_import/nodes_cleaned.csv', index=False, encoding='utf-8-sig')

# 生成relations.csv
relations_df = pd.DataFrame({
    'start_id': relationships_df['node_1'],
    'relation': relationships_df['edge'],
    'end_id': relationships_df['node_2'],
    'confidence': relationships_df['weight']
})
relations_df.to_csv('output/neo4j_import/relations_cleaned.csv', index=False, encoding='utf-8-sig')

print(f"  ✓ 已保存: output/neo4j_import/nodes_cleaned.csv")
print(f"  ✓ 已保存: output/neo4j_import/relations_cleaned.csv")

print("\n" + "="*80)
print("✓ 数据清洗完成！")
print("="*80)

print("\n📌 下一步:")
print("  1. 查看清洗后的数据: output/concepts_cleaned.csv")
print("  2. 重新导入Neo4j: python3 import_graph_direct.py")
print("     (修改脚本使用 *_cleaned.csv 文件)")
print("  3. 或运行: python3 reimport_cleaned_graph.py")
