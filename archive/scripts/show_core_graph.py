#!/usr/bin/env python3
"""
展示核心知识图谱结构
"""
import pandas as pd

print("="*80)
print("松材线虫病核心知识图谱")
print("="*80)

# 读取数据
concepts_df = pd.read_csv('output/concepts.csv')
relations_df = pd.read_csv('output/relationships.csv')

# 定义核心实体（手动筛选有意义的）
core_entities = [
    '松材线虫病害',
    '松材线虫',
    '松褐天牛',
    '云杉花墨天牛',
    '马尾松',
    '黑松',
    '湿地松',
    '叶片',
    '伴生细菌',
    '美国白蛾',
    '褐梗天牛',
    '疫区',
    '防治',
    '生物防治',
    '诱捕器'
]

print(f"\n🎯 核心实体 ({len(core_entities)}个)")
for i, entity in enumerate(core_entities, 1):
    entity_info = concepts_df[concepts_df['entity'] == entity]
    if not entity_info.empty:
        importance = entity_info.iloc[0]['importance']
        category = entity_info.iloc[0]['category']
        print(f"  {i:2d}. {entity:15s} [重要性:{importance}] ({category})")
    else:
        print(f"  {i:2d}. {entity:15s} [未找到]")

# 提取核心子图的关系
print(f"\n🔗 核心关系网络")
print("="*80)

# 按类别组织关系
categories = {
    '病原-寄主': [],
    '媒介-传播': [],
    '症状-影响': [],
    '防治-措施': [],
    '其他': []
}

for _, row in relations_df.iterrows():
    node1 = row['node_1']
    node2 = row['node_2']
    edge = row['edge']
    weight = row.get('weight', 0)
    
    # 只显示核心实体之间的关系
    if node1 in core_entities and node2 in core_entities:
        relation = f"  {node1:15s} --[{edge:25s}]--> {node2:15s} (权重:{weight:.3f})"
        
        # 分类
        if '寄生' in edge or '寄主' in edge or '感染' in edge:
            categories['病原-寄主'].append(relation)
        elif '传播' in edge or '媒介' in edge or '携带' in edge:
            categories['媒介-传播'].append(relation)
        elif '症状' in edge or '引起' in edge or '影响' in edge:
            categories['症状-影响'].append(relation)
        elif '防治' in edge or '治疗' in edge or '预防' in edge:
            categories['防治-措施'].append(relation)
        else:
            categories['其他'].append(relation)

# 打印分类关系
for cat_name, relations in categories.items():
    if relations:
        print(f"\n【{cat_name}】({len(relations)}条)")
        for rel in sorted(relations)[:10]:  # 每类最多显示10条
            print(rel)

# 统计核心实体的连接度
print(f"\n📊 核心实体连接度")
print("="*80)
from collections import Counter
node1_counts = Counter(relations_df[relations_df['node_1'].isin(core_entities)]['node_1'])
node2_counts = Counter(relations_df[relations_df['node_2'].isin(core_entities)]['node_2'])
all_counts = node1_counts + node2_counts

for entity in core_entities:
    count = all_counts.get(entity, 0)
    if count > 0:
        bar = '█' * min(count // 2, 40)
        print(f"  {entity:15s}: {bar} {count}")

# 关键路径分析
print(f"\n🛤️  关键传播路径")
print("="*80)
print("  松材线虫 → 松褐天牛 → 马尾松/黑松/湿地松 → 松材线虫病害 → 叶片症状")
print("  ↓")
print("  伴生细菌（协同致病）")
print()
print("  防治措施:")
print("  - 诱捕器（捕获媒介天牛）")
print("  - 生物防治")
print("  - 疫区管理")

print("\n" + "="*80)
print("✓ 核心图谱展示完成")
print("="*80)
