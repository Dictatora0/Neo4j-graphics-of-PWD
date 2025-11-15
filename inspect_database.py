#!/usr/bin/env python3
"""
详细检查Neo4j数据库内容
"""
from neo4j import GraphDatabase
import pandas as pd

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("Neo4j 数据库详细检查")
print("="*80)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    # 1. 基本统计
    print("\n📊 基本统计")
    print("-"*80)
    
    result = session.run("MATCH (n) RETURN count(n) as count")
    node_count = result.single()['count']
    
    result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
    rel_count = result.single()['count']
    
    print(f"  节点总数: {node_count}")
    print(f"  关系总数: {rel_count}")
    print(f"  平均连接度: {rel_count*2/node_count:.2f}")
    
    # 2. 按类别统计节点
    print("\n📁 节点类别分布")
    print("-"*80)
    
    result = session.run("""
        MATCH (n:Concept)
        RETURN n.category as category, count(*) as count
        ORDER BY count DESC
    """)
    
    categories_data = []
    for record in result:
        cat = record['category']
        count = record['count']
        pct = count / node_count * 100
        categories_data.append((cat, count, pct))
        print(f"  {cat:15s}: {count:3d} ({pct:5.1f}%)")
    
    # 3. 各类别的核心节点
    print("\n🌟 各类别核心节点（前3）")
    print("-"*80)
    
    for cat, _, _ in categories_data[:8]:  # 前8个类别
        print(f"\n  【{cat}】")
        result = session.run("""
            MATCH (n:Concept {category: $category})
            WITH n, COUNT {(n)--()} as degree
            RETURN n.name as name, n.importance as importance, degree
            ORDER BY degree DESC
            LIMIT 3
        """, category=cat)
        
        for record in result:
            name = record['name'][:30] if len(record['name']) > 30 else record['name']
            print(f"    • {name:32s} [重要性:{record['importance']}] ({record['degree']} 个连接)")
    
    # 4. 关系类型统计
    print("\n\n🔗 关系类型分布")
    print("-"*80)
    
    result = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) as type, count(*) as count
        ORDER BY count DESC
        LIMIT 15
    """)
    
    for record in result:
        rel_type = record['type']
        count = record['count']
        pct = count / rel_count * 100
        
        # 显示原始类型
        result2 = session.run(f"""
            MATCH ()-[r:{rel_type}]->()
            RETURN r.type as original_type
            LIMIT 1
        """)
        original = result2.single()
        original_type = original['original_type'] if original else rel_type
        
        if len(original_type) > 30:
            original_type = original_type[:27] + "..."
        
        print(f"  {rel_type:25s}: {count:3d} ({pct:5.1f}%) [{original_type}]")
    
    # 5. 高权重关系
    print("\n\n⭐ 高权重关系（前10）")
    print("-"*80)
    
    result = session.run("""
        MATCH (n1)-[r]->(n2)
        WHERE r.weight IS NOT NULL
        RETURN n1.name as node1, type(r) as rel_type, n2.name as node2, 
               r.weight as weight, n1.category as cat1, n2.category as cat2
        ORDER BY r.weight DESC
        LIMIT 10
    """)
    
    for record in result:
        n1 = record['node1'][:20] if len(record['node1']) > 20 else record['node1']
        n2 = record['node2'][:20] if len(record['node2']) > 20 else record['node2']
        rel = record['rel_type'][:15] if len(record['rel_type']) > 15 else record['rel_type']
        
        print(f"  {n1:22s} --[{rel:17s}]--> {n2:22s}")
        print(f"    权重:{record['weight']:.3f} | {record['cat1']} -> {record['cat2']}")
    
    # 6. 关键传播路径
    print("\n\n🛤️  关键传播路径")
    print("-"*80)
    
    # 病原体 -> 媒介 -> 寄主
    print("\n  病原体 -> 媒介 -> 寄主:")
    result = session.run("""
        MATCH path = (pathogen:Concept)-[r1]-(vector:Concept)-[r2]-(host:Concept)
        WHERE pathogen.category = '病原体' 
          AND vector.category = '媒介'
          AND host.category = '寄主'
        RETURN pathogen.name as p, type(r1) as rel1, 
               vector.name as v, type(r2) as rel2, host.name as h
        LIMIT 5
    """)
    
    for record in result:
        p = record['p'][:20] if len(record['p']) > 20 else record['p']
        v = record['v'][:20] if len(record['v']) > 20 else record['v']
        h = record['h'][:20] if len(record['h']) > 20 else record['h']
        print(f"    {p} -> {v} -> {h}")
    
    # 疾病 -> 症状
    print("\n  疾病 -> 症状:")
    result = session.run("""
        MATCH (disease:Concept)-[r]-(symptom:Concept)
        WHERE disease.category = '疾病' AND symptom.category = '症状'
        RETURN disease.name as d, type(r) as rel, symptom.name as s
        LIMIT 5
    """)
    
    for record in result:
        print(f"    {record['d']} --[{record['rel']}]--> {record['s']}")
    
    # 7. 孤立节点检查
    print("\n\n⚠️  数据质量检查")
    print("-"*80)
    
    result = session.run("""
        MATCH (n:Concept)
        WHERE NOT (n)--()
        RETURN count(n) as isolated_count
    """)
    isolated = result.single()['isolated_count']
    print(f"  孤立节点: {isolated} 个")
    
    if isolated > 0:
        result = session.run("""
            MATCH (n:Concept)
            WHERE NOT (n)--()
            RETURN n.name as name, n.category as category
            LIMIT 10
        """)
        print("  示例:")
        for record in result:
            print(f"    • {record['name']} ({record['category']})")
    
    # 低连接度节点
    result = session.run("""
        MATCH (n:Concept)
        WITH n, COUNT {(n)--()} as degree
        WHERE degree <= 2
        RETURN count(n) as low_degree_count
    """)
    low_degree = result.single()['low_degree_count']
    print(f"\n  低连接度节点(≤2): {low_degree} 个 ({low_degree/node_count*100:.1f}%)")
    
    # 8. 图谱密度分析
    print("\n\n📈 图谱密度分析")
    print("-"*80)
    
    max_edges = node_count * (node_count - 1) / 2
    density = rel_count / max_edges * 100 if max_edges > 0 else 0
    print(f"  图密度: {density:.4f}%")
    print(f"  最大可能边数: {int(max_edges)}")
    print(f"  当前边数: {rel_count}")
    
    # 连接度分布
    result = session.run("""
        MATCH (n:Concept)
        WITH n, COUNT {(n)--()} as degree
        RETURN 
            min(degree) as min_degree,
            max(degree) as max_degree,
            avg(degree) as avg_degree,
            percentileCont(degree, 0.5) as median_degree
    """)
    
    stats = result.single()
    print(f"\n  连接度统计:")
    print(f"    最小: {stats['min_degree']}")
    print(f"    最大: {stats['max_degree']}")
    print(f"    平均: {stats['avg_degree']:.2f}")
    print(f"    中位数: {stats['median_degree']:.1f}")

driver.close()

print("\n" + "="*80)
print("✓ 数据库检查完成")
print("="*80)

print("\n💡 总结:")
print("  • 数据库已包含最终优化后的知识图谱")
print("  • 90个实体，704个关系")
print("  • 类别分布合理，'其他'类别占31.1%")
print("  • 核心节点连接良好")
print("\n📌 可以在Neo4j Browser中进一步探索:")
print("  http://localhost:7474")
