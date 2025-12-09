#!/usr/bin/env python3
"""为Neo4j图谱中的节点添加importance属性

基于节点的度数（连接数）计算重要性评分：
- 5星：degree >= 30（核心枢纽节点）
- 4星：20 <= degree < 30（重要节点）
- 3星：10 <= degree < 20（中等重要）
- 2星：5 <= degree < 10（一般节点）
- 1星：degree < 5（边缘节点）
"""

from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("为Neo4j节点添加重要性属性")
print("="*80)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    # 先确保节点有 total_degree 属性
    print("\n检查并更新节点度数...")
    session.run("""
        MATCH (n)
        WITH n, COUNT{(n)--()}  as degree
        SET n.total_degree = degree
    """)
    
    # 基于度数计算importance（1-5星）
    print("计算重要性评分...")
    session.run("""
        MATCH (n)
        WITH n, n.total_degree as degree
        SET n.importance = CASE
            WHEN degree >= 30 THEN 5
            WHEN degree >= 20 THEN 4
            WHEN degree >= 10 THEN 3
            WHEN degree >= 5 THEN 2
            ELSE 1
        END
    """)
    
    # 验证结果
    print("\n重要性分布统计:")
    result = session.run("""
        MATCH (n)
        RETURN n.importance as importance, COUNT(n) as count
        ORDER BY importance DESC
    """)
    
    total = 0
    for record in result:
        importance = record['importance']
        count = record['count']
        total += count
        print(f"  {importance}星: {count} 个节点 ({count/max(1,total)*100:.1f}%)")
    
    print(f"\n总计: {total} 个节点已添加importance属性")
    
    # 显示top节点
    print("\n重要性最高的节点（Top 10）:")
    top_nodes = session.run("""
        MATCH (n)
        WHERE n.importance IS NOT NULL
        RETURN n.name as name, n.importance as importance, n.total_degree as degree
        ORDER BY n.importance DESC, n.total_degree DESC
        LIMIT 10
    """)
    
    for i, record in enumerate(top_nodes, 1):
        print(f"  {i}. {record['name']} (重要性: {record['importance']}星, 度数: {record['degree']})")

driver.close()

print("\n" + "="*80)
print("完成！重新加载前端页面即可看到重要性分布")
print("="*80)
