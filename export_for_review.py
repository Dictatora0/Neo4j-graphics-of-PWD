#!/usr/bin/env python3
"""
导出三元组便于人工审查
生成多种格式的导出文件，包含详细的统计和分析信息
"""
import pandas as pd
import os
from datetime import datetime

print("="*80)
print("导出三元组便于人工审查")
print("="*80)

# 读取原始CSV
csv_path = 'output/triples_export.csv'
df = pd.read_csv(csv_path)

print(f"\n原始数据统计:")
print(f"  总行数: {len(df)}")
print(f"  关系类型: {df['relationship'].nunique()}")
print(f"  唯一节点: {len(set(df['node_1'].unique()) | set(df['node_2'].unique()))}")

# ============================================================================
# 1. 生成按关系类型分类的审查表
# ============================================================================
print("\n" + "="*80)
print("1. 生成按关系类型分类的审查表")
print("="*80)

# 按关系类型分组
rel_groups = df.groupby('relationship')

review_file = 'output/triples_by_relationship.csv'
with open(review_file, 'w', encoding='utf-8') as f:
    f.write("# 知识图谱三元组 - 按关系类型分类\n")
    f.write(f"# 生成时间: {datetime.now().isoformat()}\n")
    f.write(f"# 总行数: {len(df)}\n")
    f.write(f"# 关系类型: {df['relationship'].nunique()}\n\n")
    
    for rel_type in df['relationship'].unique():
        rel_df = df[df['relationship'] == rel_type].sort_values('weight', ascending=False)
        count = len(rel_df)
        avg_weight = rel_df['weight'].mean()
        
        f.write(f"\n{'='*80}\n")
        f.write(f"关系类型: {rel_type}\n")
        f.write(f"数量: {count} 条\n")
        f.write(f"平均权重: {avg_weight:.4f}\n")
        f.write(f"{'='*80}\n")
        f.write("node_1,relationship,node_2,weight\n")
        
        for _, row in rel_df.iterrows():
            f.write(f"{row['node_1']},{row['relationship']},{row['node_2']},{row['weight']}\n")

print(f"  ✓ 已生成 {review_file}")

# ============================================================================
# 2. 生成关系类型统计表
# ============================================================================
print("\n" + "="*80)
print("2. 生成关系类型统计表")
print("="*80)

rel_stats = df.groupby('relationship').agg({
    'weight': ['count', 'mean', 'min', 'max', 'std']
}).round(4)

rel_stats.columns = ['count', 'avg_weight', 'min_weight', 'max_weight', 'std_weight']
rel_stats = rel_stats.sort_values('count', ascending=False)

stats_file = 'output/relationship_statistics.csv'
rel_stats.to_csv(stats_file)
print(f"  ✓ 已生成 {stats_file}")

print("\n  关系类型统计（前15）:")
for rel, row in rel_stats.head(15).iterrows():
    print(f"    {rel:30s}: {int(row['count']):3d} 条, 平均权重: {row['avg_weight']:.4f}")

# ============================================================================
# 3. 生成节点统计表
# ============================================================================
print("\n" + "="*80)
print("3. 生成节点统计表")
print("="*80)

# 统计每个节点的出度和入度
out_degree = df.groupby('node_1').size().rename('out_degree')
in_degree = df.groupby('node_2').size().rename('in_degree')

all_nodes = list(set(df['node_1'].unique()) | set(df['node_2'].unique()))
node_stats = pd.DataFrame(index=all_nodes)
node_stats['out_degree'] = out_degree
node_stats['in_degree'] = in_degree
node_stats = node_stats.fillna(0).astype(int)
node_stats['total_degree'] = node_stats['out_degree'] + node_stats['in_degree']
node_stats = node_stats.sort_values('total_degree', ascending=False)

nodes_file = 'output/node_statistics.csv'
node_stats.to_csv(nodes_file)
print(f"  ✓ 已生成 {nodes_file}")

print(f"\n  节点统计:")
print(f"    总节点数: {len(node_stats)}")
print(f"    平均度数: {node_stats['total_degree'].mean():.2f}")
print(f"    最高度数: {node_stats['total_degree'].max()}")

print("\n  度数最高的节点（前10）:")
for node, row in node_stats.head(10).iterrows():
    print(f"    {node:40s}: 出度={int(row['out_degree']):2d}, 入度={int(row['in_degree']):2d}, 总度数={int(row['total_degree']):2d}")

# ============================================================================
# 4. 生成质量检查报告
# ============================================================================
print("\n" + "="*80)
print("4. 生成质量检查报告")
print("="*80)

quality_file = 'output/quality_report.txt'
with open(quality_file, 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("知识图谱质量检查报告\n")
    f.write("="*80 + "\n\n")
    
    f.write(f"生成时间: {datetime.now().isoformat()}\n\n")
    
    # 基本统计
    f.write("【基本统计】\n")
    f.write(f"  总三元组数: {len(df)}\n")
    f.write(f"  唯一节点数: {len(node_stats)}\n")
    f.write(f"  关系类型数: {df['relationship'].nunique()}\n\n")
    
    # 关系类型分布
    f.write("【关系类型分布】\n")
    for rel, count in df['relationship'].value_counts().items():
        pct = count / len(df) * 100
        f.write(f"  {rel:30s}: {count:3d} ({pct:5.1f}%)\n")
    f.write("\n")
    
    # 权重分布
    f.write("【权重分布】\n")
    f.write(f"  最小权重: {df['weight'].min():.6f}\n")
    f.write(f"  最大权重: {df['weight'].max():.6f}\n")
    f.write(f"  平均权重: {df['weight'].mean():.6f}\n")
    f.write(f"  中位权重: {df['weight'].median():.6f}\n")
    f.write(f"  标准差: {df['weight'].std():.6f}\n\n")
    
    # 数据质量检查
    f.write("【数据质量检查】\n")
    
    # 检查中文
    chinese_rels = df[df['relationship'].str.contains('[\u4e00-\u9fa5]', regex=True)]['relationship'].nunique()
    chinese_nodes_1 = df[df['node_1'].str.contains('[\u4e00-\u9fa5]', regex=True)].shape[0]
    chinese_nodes_2 = df[df['node_2'].str.contains('[\u4e00-\u9fa5]', regex=True)].shape[0]
    
    f.write(f"  中文关系类型: {chinese_rels} 个 {'✅' if chinese_rels == 0 else '❌'}\n")
    f.write(f"  中文节点: {chinese_nodes_1 + chinese_nodes_2} 个 {'✅' if chinese_nodes_1 + chinese_nodes_2 == 0 else '❌'}\n")
    
    # 检查重复
    duplicates = df.duplicated(subset=['node_1', 'relationship', 'node_2']).sum()
    f.write(f"  重复三元组: {duplicates} 个 {'✅' if duplicates == 0 else '❌'}\n")
    
    # 检查孤立节点
    isolated = len([n for n in node_stats.index if node_stats.loc[n, 'total_degree'] == 0])
    f.write(f"  孤立节点: {isolated} 个 {'✅' if isolated == 0 else '❌'}\n")
    
    # 检查自环
    self_loops = ((df['node_1'] == df['node_2']).sum())
    f.write(f"  自环关系: {self_loops} 个 {'✅' if self_loops == 0 else '❌'}\n\n")
    
    # 节点度数分析
    f.write("【节点度数分析】\n")
    f.write(f"  平均出度: {node_stats['out_degree'].mean():.2f}\n")
    f.write(f"  平均入度: {node_stats['in_degree'].mean():.2f}\n")
    f.write(f"  最高出度: {node_stats['out_degree'].max()}\n")
    f.write(f"  最高入度: {node_stats['in_degree'].max()}\n\n")
    
    # 高度数节点
    f.write("【度数最高的节点（前20）】\n")
    for node, row in node_stats.head(20).iterrows():
        f.write(f"  {node:40s}: 出度={int(row['out_degree']):2d}, 入度={int(row['in_degree']):2d}, 总度数={int(row['total_degree']):2d}\n")
    f.write("\n")
    
    # 关系类型详细统计
    f.write("【关系类型详细统计】\n")
    for rel in df['relationship'].unique():
        rel_df = df[df['relationship'] == rel]
        f.write(f"  {rel}:\n")
        f.write(f"    数量: {len(rel_df)}\n")
        f.write(f"    平均权重: {rel_df['weight'].mean():.6f}\n")
        f.write(f"    权重范围: [{rel_df['weight'].min():.6f}, {rel_df['weight'].max():.6f}]\n")

print(f"  ✓ 已生成 {quality_file}")

# ============================================================================
# 5. 生成可视化友好的格式
# ============================================================================
print("\n" + "="*80)
print("5. 生成可视化友好的格式")
print("="*80)

# 生成按权重排序的审查表
sorted_file = 'output/triples_sorted_by_weight.csv'
df_sorted = df.sort_values('weight', ascending=False)
df_sorted.to_csv(sorted_file, index=False)
print(f"  ✓ 已生成 {sorted_file}")

# 生成高权重三元组
high_weight_file = 'output/high_weight_triples.csv'
high_weight_df = df[df['weight'] >= 0.5].sort_values('weight', ascending=False)
high_weight_df.to_csv(high_weight_file, index=False)
print(f"  ✓ 已生成 {high_weight_file} ({len(high_weight_df)} 条)")

# 生成低权重三元组
low_weight_file = 'output/low_weight_triples.csv'
low_weight_df = df[df['weight'] < 0.2].sort_values('weight', ascending=False)
low_weight_df.to_csv(low_weight_file, index=False)
print(f"  ✓ 已生成 {low_weight_file} ({len(low_weight_df)} 条)")

# ============================================================================
# 6. 生成审查清单
# ============================================================================
print("\n" + "="*80)
print("6. 生成审查清单")
print("="*80)

checklist_file = 'output/review_checklist.txt'
with open(checklist_file, 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("知识图谱人工审查清单\n")
    f.write("="*80 + "\n\n")
    
    f.write("【审查指南】\n\n")
    
    f.write("1. 关系类型审查\n")
    f.write("   - 检查是否所有关系类型都是英文\n")
    f.write("   - 检查是否存在拼写错误或不一致\n")
    f.write("   - 检查是否存在同义关系未合并\n")
    f.write("   文件: relationship_statistics.csv\n\n")
    
    f.write("2. 节点审查\n")
    f.write("   - 检查是否所有节点都是英文\n")
    f.write("   - 检查是否存在拼写错误或不一致\n")
    f.write("   - 检查度数异常的节点\n")
    f.write("   文件: node_statistics.csv\n\n")
    
    f.write("3. 三元组逻辑审查\n")
    f.write("   - 检查是否存在逻辑错误（如疾病寄生于病原体）\n")
    f.write("   - 检查是否存在不合理的关系\n")
    f.write("   - 检查权重是否合理\n")
    f.write("   文件: triples_by_relationship.csv\n\n")
    
    f.write("4. 权重审查\n")
    f.write("   - 检查高权重三元组是否合理\n")
    f.write("   - 检查低权重三元组是否应该删除\n")
    f.write("   文件: high_weight_triples.csv, low_weight_triples.csv\n\n")
    
    f.write("【数据质量指标】\n\n")
    f.write(f"✓ 总三元组数: {len(df)}\n")
    f.write(f"✓ 唯一节点数: {len(node_stats)}\n")
    f.write(f"✓ 关系类型数: {df['relationship'].nunique()}\n")
    f.write(f"✓ 中文关系: {chinese_rels} 个\n")
    f.write(f"✓ 中文节点: {chinese_nodes_1 + chinese_nodes_2} 个\n")
    f.write(f"✓ 重复三元组: {duplicates} 个\n")
    f.write(f"✓ 孤立节点: {isolated} 个\n")
    f.write(f"✓ 自环关系: {self_loops} 个\n\n")
    
    f.write("【建议的审查顺序】\n\n")
    f.write("1. 首先查看 quality_report.txt 了解整体数据质量\n")
    f.write("2. 查看 relationship_statistics.csv 审查关系类型\n")
    f.write("3. 查看 node_statistics.csv 审查节点\n")
    f.write("4. 查看 triples_by_relationship.csv 按关系类型审查三元组\n")
    f.write("5. 查看 high_weight_triples.csv 审查高权重三元组\n")
    f.write("6. 查看 low_weight_triples.csv 决定是否删除低权重三元组\n")

print(f"  ✓ 已生成 {checklist_file}")

# ============================================================================
# 总结
# ============================================================================
print("\n" + "="*80)
print("✓ 导出完成！")
print("="*80)

print("\n📁 生成的文件:")
print(f"  1. triples_export.csv - 原始三元组（标准格式）")
print(f"  2. triples_by_relationship.csv - 按关系类型分类的三元组")
print(f"  3. relationship_statistics.csv - 关系类型统计")
print(f"  4. node_statistics.csv - 节点统计")
print(f"  5. quality_report.txt - 质量检查报告")
print(f"  6. triples_sorted_by_weight.csv - 按权重排序的三元组")
print(f"  7. high_weight_triples.csv - 高权重三元组（权重≥0.5）")
print(f"  8. low_weight_triples.csv - 低权重三元组（权重<0.2）")
print(f"  9. review_checklist.txt - 人工审查清单")

print("\n📌 建议的审查流程:")
print("  1. 阅读 review_checklist.txt 了解审查指南")
print("  2. 查看 quality_report.txt 了解整体质量")
print("  3. 按照清单中的建议逐个审查各个文件")
print("  4. 根据审查结果进行必要的修正")

print("\n所有文件已保存到 output/ 目录")
