#!/usr/bin/env python3
"""
应用最终的实体合并和重新分类
"""
import pandas as pd
import json
import os

print("="*80)
print("应用最终合并和重新分类")
print("="*80)

# 加载数据
concepts_df = pd.read_csv('output/concepts_disambiguated.csv')
relationships_df = pd.read_csv('output/relationships_disambiguated.csv')

print(f"\n原始数据:")
print(f"  实体: {len(concepts_df)} 个")
print(f"  关系: {len(relationships_df)} 个")

# ============================================================================
# 1. 定义需要合并的实体对
# ============================================================================
merges = {
    # Sentinel-2 系列合并
    'sentinel-2': 'sentinel-2 卫星遥感影像',
    'sentinel-2 卫星影像': 'sentinel-2 卫星遥感影像',
    
    # 天牛种类合并
    'monochamus ahernatus': 'monochamus alternatus',  # 这两个可能是拼写错误
    'rusticus': 'arhopalus rusticus',
    '云杉小墨天牛': '云杉花墨天牛',  # 可能是同一物种的不同叫法
    
    # 伴生细菌合并
    '伴生细菌': '松材线虫伴生细菌',
    
    # 高光谱数据合并
    '无人机高光谱': '无人机高光谱数据',
    '高光谱数据': '无人机高光谱数据',
    
    # 林地类型合并
    '落叶阔叶林': '温带落叶阔叶林',
    
    # 褐梗天牛合并（保留成虫）
    '褐梗天牛幼虫': '褐梗天牛',
}

print(f"\n📝 计划合并 {len(merges)} 对实体")

# ============================================================================
# 2. 应用合并
# ============================================================================
print("\n🔄 应用合并...")
merged_count = 0

for old_name, new_name in merges.items():
    # 检查两个实体是否都存在
    if old_name not in concepts_df['entity'].values:
        print(f"  ⊘ 跳过: {old_name} (不存在)")
        continue
    
    if new_name not in concepts_df['entity'].values:
        print(f"  ⚠️  目标实体不存在: {new_name}，保留 {old_name}")
        continue
    
    print(f"  ✓ {old_name} -> {new_name}")
    
    # 更新关系
    relationships_df.loc[relationships_df['node_1'] == old_name, 'node_1'] = new_name
    relationships_df.loc[relationships_df['node_2'] == old_name, 'node_2'] = new_name
    
    # 删除旧实体
    concepts_df = concepts_df[concepts_df['entity'] != old_name]
    merged_count += 1

print(f"\n  已合并: {merged_count} 对")

# ============================================================================
# 3. 去重关系
# ============================================================================
print("\n🔄 去重关系...")
before_dedup = len(relationships_df)

relationships_df = relationships_df.groupby(
    ['node_1', 'node_2', 'edge'], as_index=False
).agg({
    'weight': 'max',
    'source': lambda x: ','.join(sorted(set(','.join(x).split(',')))),
    'chunk_id': 'first'
})

after_dedup = len(relationships_df)
print(f"  ✓ {before_dedup} -> {after_dedup} (移除 {before_dedup - after_dedup} 个)")

# ============================================================================
# 4. 重新分类实体
# ============================================================================
print("\n🏷️  重新分类实体...")

reclassifications = {
    # 地点类
    '南天门': '地点',
    '天烛峰': '地点',
    '桃花峪': '地点',
    '玉泉寺': '地点',
    '竹林寺': '地点',
    '巴山': '地点',
    '吉林': '地点',
    '黑龙江': '地点',
    
    # 寄主类
    '松林': '寄主',
    '杂木林': '寄主',
    '麻栎林': '寄主',
    '青松': '寄主',
    
    # 媒介类（昆虫科）
    '吉丁科': '媒介',
    '小蠢科': '媒介',
    '白蚁科': '媒介',
    
    # 其他
    '林业': '其他',
    '林区': '地点',
    '分布区': '地点',
}

reclass_count = 0
for entity, new_category in reclassifications.items():
    if entity in concepts_df['entity'].values:
        old_cat = concepts_df[concepts_df['entity'] == entity]['category'].iloc[0]
        if old_cat != new_category:
            concepts_df.loc[concepts_df['entity'] == entity, 'category'] = new_category
            print(f"  ✓ {entity:20s}: {old_cat} -> {new_category}")
            reclass_count += 1

print(f"\n  已重新分类: {reclass_count} 个")

# ============================================================================
# 5. 统计结果
# ============================================================================
print("\n📊 最终统计")
print("="*80)

print(f"\n数据量:")
print(f"  实体: {len(concepts_df)} 个")
print(f"  关系: {len(relationships_df)} 个")

print(f"\n类别分布:")
category_counts = concepts_df['category'].value_counts()
for cat, count in category_counts.items():
    pct = count / len(concepts_df) * 100
    print(f"  {cat:15s}: {count:3d} ({pct:5.1f}%)")

print(f"\n关系类型分布（前10）:")
edge_counts = relationships_df['edge'].value_counts()
for edge, count in edge_counts.head(10).items():
    pct = count / len(relationships_df) * 100
    edge_display = edge if len(edge) <= 30 else edge[:27] + "..."
    print(f"  {edge_display:32s}: {count:3d} ({pct:5.1f}%)")

# ============================================================================
# 6. 保存结果
# ============================================================================
print("\n💾 保存最终数据...")

concepts_df.to_csv('output/concepts_final.csv', index=False, encoding='utf-8-sig')
relationships_df.to_csv('output/relationships_final.csv', index=False, encoding='utf-8-sig')

print(f"  ✓ 已保存: output/concepts_final.csv")
print(f"  ✓ 已保存: output/relationships_final.csv")

# 生成Neo4j导入文件
print("\n🔄 生成Neo4j导入文件...")

nodes_df = pd.DataFrame({
    'id': range(len(concepts_df)),
    'name': concepts_df['entity'],
    'label': concepts_df['category'],
    'importance': concepts_df['importance']
})
nodes_df.to_csv('output/neo4j_import/nodes_final.csv', index=False, encoding='utf-8-sig')

relations_df = pd.DataFrame({
    'start_id': relationships_df['node_1'],
    'relation': relationships_df['edge'],
    'end_id': relationships_df['node_2'],
    'confidence': relationships_df['weight']
})
relations_df.to_csv('output/neo4j_import/relations_final.csv', index=False, encoding='utf-8-sig')

print(f"  ✓ 已保存: output/neo4j_import/nodes_final.csv")
print(f"  ✓ 已保存: output/neo4j_import/relations_final.csv")

# 保存所有合并记录
all_merges = {}
if os.path.exists('output/entity_merges.json'):
    with open('output/entity_merges.json', 'r', encoding='utf-8') as f:
        all_merges = json.load(f)

all_merges.update(merges)

with open('output/all_entity_merges.json', 'w', encoding='utf-8') as f:
    json.dump(all_merges, f, ensure_ascii=False, indent=2)

print(f"  ✓ 合并记录: output/all_entity_merges.json")

print("\n" + "="*80)
print("✓ 最终优化完成！")
print("="*80)

print("\n📌 改进总结:")
print(f"  • 合并实体: {merged_count} 对")
print(f"  • 重新分类: {reclass_count} 个")
print(f"  • 去重关系: {before_dedup - after_dedup} 个")
print(f"  • 最终实体数: {len(concepts_df)}")
print(f"  • 最终关系数: {len(relationships_df)}")
print(f"  • '其他'类别占比: {category_counts.get('其他', 0) / len(concepts_df) * 100:.1f}%")

print("\n📌 下一步:")
print("  1. 重新导入Neo4j:")
print("     python3 reimport_final_graph.py")
print("  2. 可视化验证:")
print("     python3 visualize_final_graph.py")
