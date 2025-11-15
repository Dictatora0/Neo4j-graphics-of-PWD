#!/usr/bin/env python3
"""
查看和审查剩余的合并候选
"""
import pandas as pd
from difflib import SequenceMatcher
import json

print("="*80)
print("剩余合并候选审查")
print("="*80)

# 加载消歧后的数据
concepts_df = pd.read_csv('output/concepts_disambiguated.csv')
relationships_df = pd.read_csv('output/relationships_disambiguated.csv')

print(f"\n当前数据:")
print(f"  实体: {len(concepts_df)} 个")
print(f"  关系: {len(relationships_df)} 个")

# 重新查找候选（使用较低阈值）
print("\n🔍 查找剩余合并候选...")

entities = concepts_df['entity'].tolist()
categories = concepts_df['category'].tolist()

candidates = []

# 1. 包含关系
for i, (e1, c1) in enumerate(zip(entities, categories)):
    for j, (e2, c2) in enumerate(zip(entities, categories)):
        if i >= j:
            continue
        
        e1_lower = str(e1).lower()
        e2_lower = str(e2).lower()
        
        if e1_lower in e2_lower and len(e1) >= 3:
            if c1 == c2 or c1 == '其他' or c2 == '其他':
                candidates.append({
                    'entity1': e1,
                    'entity2': e2,
                    'type': '包含',
                    'keep': e2 if len(e2) > len(e1) else e1,
                    'cat1': c1,
                    'cat2': c2,
                    'confidence': 0.9
                })
        elif e2_lower in e1_lower and len(e2) >= 3:
            if c1 == c2 or c1 == '其他' or c2 == '其他':
                candidates.append({
                    'entity1': e1,
                    'entity2': e2,
                    'type': '包含',
                    'keep': e1 if len(e1) > len(e2) else e2,
                    'cat1': c1,
                    'cat2': c2,
                    'confidence': 0.9
                })

# 2. 高相似度
for i, (e1, c1) in enumerate(zip(entities, categories)):
    for j, (e2, c2) in enumerate(zip(entities, categories)):
        if i >= j:
            continue
        
        sim = SequenceMatcher(None, e1.lower(), e2.lower()).ratio()
        
        if sim > 0.8 and c1 == c2:
            candidates.append({
                'entity1': e1,
                'entity2': e2,
                'type': f'相似({sim:.2f})',
                'keep': e1 if len(e1) >= len(e2) else e2,
                'cat1': c1,
                'cat2': c2,
                'confidence': sim
            })

print(f"  ✓ 发现 {len(candidates)} 个候选")

if not candidates:
    print("\n✓ 没有剩余的合并候选")
else:
    # 按置信度排序
    candidates.sort(key=lambda x: x['confidence'], reverse=True)
    
    print("\n" + "="*80)
    print("合并候选列表")
    print("="*80)
    
    for i, c in enumerate(candidates, 1):
        print(f"\n{i}. [{c['type']}] 置信度: {c['confidence']:.2f}")
        print(f"   实体1: {c['entity1']} ({c['cat1']})")
        print(f"   实体2: {c['entity2']} ({c['cat2']})")
        print(f"   建议保留: {c['keep']}")
        
        # 显示关系数
        e1_rels = len(relationships_df[
            (relationships_df['node_1'] == c['entity1']) |
            (relationships_df['node_2'] == c['entity1'])
        ])
        e2_rels = len(relationships_df[
            (relationships_df['node_1'] == c['entity2']) |
            (relationships_df['node_2'] == c['entity2'])
        ])
        print(f"   关系数: {c['entity1']}({e1_rels}), {c['entity2']}({e2_rels})")

# 查看需要重新分类的实体
print("\n" + "="*80)
print("类别分布检查")
print("="*80)

category_counts = concepts_df['category'].value_counts()
print("\n当前类别分布:")
for cat, count in category_counts.items():
    pct = count / len(concepts_df) * 100
    print(f"  {cat:15s}: {count:3d} ({pct:5.1f}%)")

# 检查"其他"类别中可能需要重新分类的实体
other_entities = concepts_df[concepts_df['category'] == '其他']
if len(other_entities) > 0:
    print(f"\n'其他'类别实体 ({len(other_entities)}个):")
    
    # 分析这些实体
    reclassify_suggestions = []
    
    for idx, row in other_entities.iterrows():
        entity = row['entity'].lower()
        
        # 基于关键词建议分类
        if any(kw in entity for kw in ['病', 'disease', '线虫病']):
            reclassify_suggestions.append((row['entity'], '疾病'))
        elif any(kw in entity for kw in ['天牛', 'beetle', 'monochamus']):
            reclassify_suggestions.append((row['entity'], '媒介'))
        elif any(kw in entity for kw in ['松', 'pine', 'pinus']):
            reclassify_suggestions.append((row['entity'], '寄主'))
        elif any(kw in entity for kw in ['线虫', 'nematode', '细菌']):
            reclassify_suggestions.append((row['entity'], '病原体'))
        elif any(kw in entity for kw in ['叶', 'leaf', '枯萎', '症状']):
            reclassify_suggestions.append((row['entity'], '症状'))
        elif any(kw in entity for kw in ['防治', '诱捕', 'control']):
            reclassify_suggestions.append((row['entity'], '防治'))
    
    if reclassify_suggestions:
        print(f"\n建议重新分类 ({len(reclassify_suggestions)}个):")
        for entity, suggested_cat in reclassify_suggestions[:20]:
            print(f"  {entity:30s} -> {suggested_cat}")

# 检查可疑的短实体
print("\n" + "="*80)
print("可疑短实体检查")
print("="*80)

short_entities = concepts_df[concepts_df['entity'].str.len() <= 3]
if len(short_entities) > 0:
    print(f"\n发现 {len(short_entities)} 个短实体:")
    for idx, row in short_entities.iterrows():
        entity = row['entity']
        cat = row['category']
        
        # 统计关系数
        rel_count = len(relationships_df[
            (relationships_df['node_1'] == entity) |
            (relationships_df['node_2'] == entity)
        ])
        
        print(f"  {entity:10s} ({cat:10s}) - {rel_count} 个关系")

print("\n" + "="*80)
print("建议操作")
print("="*80)
print("\n1. 如需手动审查所有候选:")
print("   python3 interactive_kg_review.py")
print("\n2. 如需批量应用建议的重新分类:")
print("   python3 apply_reclassification.py")
print("\n3. 查看当前图谱:")
print("   python3 visualize_graph.py")
