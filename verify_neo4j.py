#!/usr/bin/env python3
"""
验证Neo4j导入结果
"""
from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("="*80)
print("Neo4j 知识图谱验证")
print("="*80)

with driver.session() as session:
    # 1. 统计节点数
    result = session.run("MATCH (n) RETURN count(n) as count")
    node_count = result.single()['count']
    print(f"\n📊 节点总数: {node_count}")
    
    # 2. 统计关系数
    result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
    rel_count = result.single()['count']
    print(f"🔗 关系总数: {rel_count}")
    
    # 3. 节点类型分布
    print(f"\n📁 节点标签分布:")
    result = session.run("""
        MATCH (n)
        RETURN labels(n)[0] as label, count(*) as count
        ORDER BY count DESC
    """)
    for record in result:
        print(f"  {record['label']:20s}: {record['count']:3d}")
    
    # 4. 关系类型分布（前10）
    print(f"\n🔗 关系类型分布（前10）:")
    result = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) as type, count(*) as count
        ORDER BY count DESC
        LIMIT 10
    """)
    for record in result:
        rel_type = record['type']
        if len(rel_type) > 40:
            rel_type = rel_type[:37] + "..."
        print(f"  {rel_type:42s}: {record['count']:3d}")
    
    # 5. 核心节点（连接度最高）
    print(f"\n🌟 核心节点（连接度前10）:")
    result = session.run("""
        MATCH (n)
        WITH n, COUNT {(n)--()}  as degree
        RETURN n.name as name, degree
        ORDER BY degree DESC
        LIMIT 10
    """)
    for record in result:
        name = record['name'] or 'unnamed'
        if len(name) > 30:
            name = name[:27] + "..."
        print(f"  {name:32s}: {record['degree']:3d} 个连接")
    
    # 6. 示例路径：松材线虫 -> 松褐天牛 -> 马尾松
    print(f"\n🛤️  示例传播路径:")
    result = session.run("""
        MATCH path = (n1:Concept {name: '松材线虫'})-[*1..2]-(n2:Concept {name: '马尾松'})
        RETURN path
        LIMIT 1
    """)
    for record in result:
        path = record['path']
        nodes = [node['name'] for node in path.nodes]
        print(f"  {' -> '.join(nodes)}")
    
    # 7. 核心三元组
    print(f"\n🔺 核心三元组示例:")
    result = session.run("""
        MATCH (n1)-[r1]->(n2)-[r2]->(n3)
        WHERE n1.name IN ['松材线虫', '松材线虫病害', '松褐天牛']
        RETURN n1.name as node1, type(r1) as rel1, 
               n2.name as node2, type(r2) as rel2, 
               n3.name as node3
        LIMIT 5
    """)
    for record in result:
        n1 = record['node1'][:15] if record['node1'] else 'N/A'
        r1 = record['rel1'][:20] if record['rel1'] else 'N/A'
        n2 = record['node2'][:15] if record['node2'] else 'N/A'
        r2 = record['rel2'][:20] if record['rel2'] else 'N/A'
        n3 = record['node3'][:15] if record['node3'] else 'N/A'
        print(f"  {n1} -[{r1}]-> {n2} -[{r2}]-> {n3}")

driver.close()

print("\n" + "="*80)
print("✓ 验证完成")
print("="*80)
print("\n💡 在Neo4j Browser中尝试以下查询:")
print("  1. 查看所有节点: MATCH (n) RETURN n LIMIT 25")
print("  2. 查看核心子图: MATCH (n)-[r]-(m) WHERE n.name IN ['松材线虫', '松褐天牛', '马尾松'] RETURN n, r, m")
print("  3. 查找传播路径: MATCH path = (n1 {name: '松材线虫'})-[*1..3]-(n2 {name: '黑松'}) RETURN path LIMIT 5")
print("\n🌐 Neo4j Browser: http://localhost:7474")
