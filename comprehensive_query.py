#!/usr/bin/env python3
"""
全面查询Neo4j数据库
"""
from neo4j import GraphDatabase
import pandas as pd

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("知识图谱全面查询")
print("="*80)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    
    # ========================================================================
    # 1. 基本统计
    # ========================================================================
    print("\n" + "="*80)
    print("1. 基本统计")
    print("="*80)
    
    result = session.run("MATCH (n) RETURN count(n) as count").single()
    print(f"\n  节点总数: {result['count']}")
    
    result = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()
    print(f"  关系总数: {result['count']}")
    
    result = session.run("MATCH ()-[r]->() RETURN DISTINCT type(r) as rel_type").data()
    print(f"  关系类型数: {len(result)}")
    
    # ========================================================================
    # 2. 节点类型分析
    # ========================================================================
    print("\n" + "="*80)
    print("2. 节点类型分析")
    print("="*80)
    
    result = session.run("""
        MATCH (n)
        RETURN n.type as type, count(*) as count
        ORDER BY count DESC
    """).data()
    
    print(f"\n  节点类型分布:")
    for record in result:
        print(f"    {record['type']:20s}: {record['count']:2d}")
    
    # ========================================================================
    # 3. 关系类型分析
    # ========================================================================
    print("\n" + "="*80)
    print("3. 关系类型分析")
    print("="*80)
    
    result = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) as rel_type, count(*) as count, avg(r.weight) as avg_weight
        ORDER BY count DESC
    """).data()
    
    print(f"\n  关系类型分布:")
    for record in result:
        print(f"    {record['rel_type']:25s}: {record['count']:3d} (平均权重: {record['avg_weight']:.4f})")
    
    # ========================================================================
    # 4. 度数分析
    # ========================================================================
    print("\n" + "="*80)
    print("4. 度数分析")
    print("="*80)
    
    result = session.run("""
        MATCH (n)
        RETURN n.name as name, n.type as type, n.total_degree as degree
        ORDER BY degree DESC
        LIMIT 15
    """).data()
    
    print(f"\n  度数最高的节点（前15）:")
    for i, record in enumerate(result, 1):
        print(f"    {i:2d}. {record['name']:40s} ({record['type']:12s}): {record['degree']}")
    
    # ========================================================================
    # 5. 权重分析
    # ========================================================================
    print("\n" + "="*80)
    print("5. 权重分析")
    print("="*80)
    
    result = session.run("""
        MATCH ()-[r]->()
        RETURN min(r.weight) as min_weight, 
               max(r.weight) as max_weight,
               avg(r.weight) as avg_weight,
               count(*) as count
    """).single()
    
    print(f"\n  权重统计:")
    print(f"    最小权重: {result['min_weight']:.6f}")
    print(f"    最大权重: {result['max_weight']:.6f}")
    print(f"    平均权重: {result['avg_weight']:.6f}")
    
    # 权重分布
    result = session.run("""
        MATCH ()-[r]->()
        RETURN CASE 
                 WHEN r.weight >= 0.5 THEN '高 (≥0.5)'
                 WHEN r.weight >= 0.2 THEN '中 (0.2-0.5)'
                 ELSE '低 (<0.2)'
               END as weight_level,
               count(*) as count
        ORDER BY weight_level DESC
    """).data()
    
    print(f"\n  权重分布:")
    for record in result:
        print(f"    {record['weight_level']:15s}: {record['count']:3d}")
    
    # ========================================================================
    # 6. 核心实体分析
    # ========================================================================
    print("\n" + "="*80)
    print("6. 核心实体分析")
    print("="*80)
    
    # 病原体
    result = session.run("""
        MATCH (n:Pathogen)
        RETURN n.name as name, n.total_degree as degree
        ORDER BY degree DESC
    """).data()
    
    print(f"\n  病原体:")
    for record in result:
        print(f"    - {record['name']}: 度数 {record['degree']}")
    
    # 疾病
    result = session.run("""
        MATCH (n:Disease)
        RETURN n.name as name, n.total_degree as degree
        ORDER BY degree DESC
    """).data()
    
    print(f"\n  疾病:")
    for record in result:
        print(f"    - {record['name']}: 度数 {record['degree']}")
    
    # 媒介
    result = session.run("""
        MATCH (n:Vector)
        RETURN n.name as name, n.total_degree as degree
        ORDER BY degree DESC
    """).data()
    
    print(f"\n  媒介（前5）:")
    for record in result[:5]:
        print(f"    - {record['name']}: 度数 {record['degree']}")
    
    # 寄主
    result = session.run("""
        MATCH (n:Host)
        RETURN n.name as name, n.total_degree as degree
        ORDER BY degree DESC
    """).data()
    
    print(f"\n  寄主（前5）:")
    for record in result[:5]:
        print(f"    - {record['name']}: 度数 {record['degree']}")
    
    # ========================================================================
    # 7. 关键关系分析
    # ========================================================================
    print("\n" + "="*80)
    print("7. 关键关系分析")
    print("="*80)
    
    # 寄生关系
    result = session.run("""
        MATCH (s)-[r:PARASITIZES]->(t)
        RETURN s.name as source, t.name as target, r.weight as weight
        ORDER BY r.weight DESC
        LIMIT 5
    """).data()
    
    print(f"\n  寄生关系（前5）:")
    for record in result:
        print(f"    {record['source']:30s} --[寄生]--> {record['target']:30s} (权重: {record['weight']:.4f})")
    
    # 传播关系
    result = session.run("""
        MATCH (s)-[r:TRANSMITS]->(t)
        RETURN s.name as source, t.name as target, r.weight as weight
        ORDER BY r.weight DESC
        LIMIT 5
    """).data()
    
    print(f"\n  传播关系（前5）:")
    for record in result:
        print(f"    {record['source']:30s} --[传播]--> {record['target']:30s} (权重: {record['weight']:.4f})")
    
    # 引起关系
    result = session.run("""
        MATCH (s)-[r:CAUSES]->(t)
        RETURN s.name as source, t.name as target, r.weight as weight
        ORDER BY r.weight DESC
    """).data()
    
    print(f"\n  引起关系:")
    for record in result:
        print(f"    {record['source']:30s} --[引起]--> {record['target']:30s} (权重: {record['weight']:.4f})")
    
    # ========================================================================
    # 8. 路径分析
    # ========================================================================
    print("\n" + "="*80)
    print("8. 路径分析")
    print("="*80)
    
    # 从松材线虫病到松树的路径
    result = session.run("""
        MATCH p = (disease:Disease {name: 'pine wilt disease'})-[*1..3]-(host:Host)
        RETURN p
        LIMIT 5
    """).data()
    
    print(f"\n  松材线虫病 -> 松树的路径（前5）:")
    for i, record in enumerate(result, 1):
        path = record['p']
        print(f"    路径{i}: {path}")
    
    # ========================================================================
    # 9. 共现网络分析
    # ========================================================================
    print("\n" + "="*80)
    print("9. 共现网络分析")
    print("="*80)
    
    result = session.run("""
        MATCH (a)-[r:CO_OCCURS_WITH]-(b)
        WHERE a.name IN ['pine wilt disease', 'bursaphelenchus xylophilus', 'monochamus alternatus']
        RETURN a.name as node_a, b.name as node_b, count(*) as count
        ORDER BY count DESC
        LIMIT 10
    """).data()
    
    print(f"\n  核心实体的共现关系（前10）:")
    for record in result:
        print(f"    {record['node_a']:30s} <--> {record['node_b']:30s}")
    
    # ========================================================================
    # 10. 孤立和弱连接分析
    # ========================================================================
    print("\n" + "="*80)
    print("10. 孤立和弱连接分析")
    print("="*80)
    
    # 孤立节点
    result = session.run("""
        MATCH (n)
        WHERE n.total_degree = 0
        RETURN n.name as name, n.type as type
    """).data()
    
    print(f"\n  孤立节点: {len(result)} 个")
    for record in result:
        print(f"    - {record['name']} ({record['type']})")
    
    # 低连接度节点
    result = session.run("""
        MATCH (n)
        WHERE n.total_degree <= 2
        RETURN n.name as name, n.type as type, n.total_degree as degree
        ORDER BY degree
    """).data()
    
    print(f"\n  低连接度节点（度数≤2）: {len(result)} 个")
    for record in result[:10]:
        print(f"    - {record['name']:40s} ({record['type']:12s}): 度数 {record['degree']}")
    
    # ========================================================================
    # 11. 关系密度分析
    # ========================================================================
    print("\n" + "="*80)
    print("11. 关系密度分析")
    print("="*80)
    
    result = session.run("""
        MATCH (n)
        WITH count(n) as node_count
        MATCH ()-[r]->()
        WITH node_count, count(r) as rel_count
        RETURN node_count, rel_count, 
               ROUND(TOFLOAT(rel_count) / (node_count * (node_count - 1)) * 100, 2) as density_percent
    """).single()
    
    print(f"\n  图谱密度:")
    print(f"    节点数: {result['node_count']}")
    print(f"    关系数: {result['rel_count']}")
    print(f"    密度: {result['density_percent']}%")
    
    # ========================================================================
    # 12. 数据质量总结
    # ========================================================================
    print("\n" + "="*80)
    print("12. 数据质量总结")
    print("="*80)
    
    # 检查中文
    result = session.run("""
        MATCH ()-[r]->()
        WHERE type(r) =~ '.*[\u4e00-\u9fa5].*'
        RETURN count(r) as count
    """).single()
    
    print(f"\n  ✅ 中文关系: {result['count']} 个")
    
    result = session.run("""
        MATCH (n)
        WHERE n.name =~ '.*[\u4e00-\u9fa5].*'
        RETURN count(n) as count
    """).single()
    
    print(f"  ✅ 中文节点: {result['count']} 个")
    
    # 检查重复
    result = session.run("""
        MATCH (a)-[r]->(b)
        WITH a, b, type(r) as rel_type, collect(r) as rels
        WHERE size(rels) > 1
        RETURN count(*) as duplicate_count
    """).single()
    
    print(f"  ✅ 重复关系: {result['duplicate_count']} 个")
    
    # 检查自环
    result = session.run("""
        MATCH (n)-[r]->(n)
        RETURN count(r) as count
    """).single()
    
    print(f"  ✅ 自环关系: {result['count']} 个")
    
    # 检查样式
    result = session.run("""
        MATCH (n)
        WHERE n.color IS NOT NULL
        RETURN count(n) as count
    """).single()
    
    print(f"  ✅ 带样式的节点: {result['count']} 个")

driver.close()

print("\n" + "="*80)
print("✓ 查询完成！")
print("="*80)

print("\n💡 建议:")
print("  1. 在Neo4j Browser中运行更复杂的查询")
print("  2. 使用 EXPLAIN 分析查询性能")
print("  3. 导出查询结果为CSV进行进一步分析")
print("  4. 根据需要调整样式和权重")
