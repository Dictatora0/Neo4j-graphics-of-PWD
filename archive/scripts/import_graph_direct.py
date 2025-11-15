#!/usr/bin/env python3
"""
直接使用Python驱动导入知识图谱到Neo4j
"""
from neo4j import GraphDatabase
import pandas as pd

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("导入知识图谱到 Neo4j")
print("="*80)

# 读取数据
print("\n📖 读取CSV文件...")
nodes_df = pd.read_csv('output/neo4j_import/nodes.csv')
relations_df = pd.read_csv('output/neo4j_import/relations.csv')

print(f"  节点数: {len(nodes_df)}")
print(f"  关系数: {len(relations_df)}")

# 连接Neo4j
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    # 1. 清空数据库
    print("\n🗑️  清空现有数据...")
    session.run("MATCH (n) DETACH DELETE n")
    print("  ✓ 完成")
    
    # 2. 创建节点
    print(f"\n📦 创建 {len(nodes_df)} 个节点...")
    created_count = 0
    for idx, row in nodes_df.iterrows():
        name = str(row['name']) if pd.notna(row['name']) else ''
        label = str(row['label']) if pd.notna(row['label']) else 'Concept'
        
        # 跳过空节点
        if not name or name == 'nan':
            continue
        
        # 创建节点
        session.run("""
            CREATE (n:Concept {
                name: $name,
                label: $label
            })
        """, name=name, label=label)
        created_count += 1
        
        if (created_count % 20 == 0):
            print(f"  进度: {created_count}/{len(nodes_df)}")
    
    print(f"  ✓ 创建了 {created_count} 个节点")
    
    # 3. 创建索引
    print("\n🔍 创建索引...")
    session.run("CREATE INDEX concept_name IF NOT EXISTS FOR (n:Concept) ON (n.name)")
    print("  ✓ 完成")
    
    # 4. 创建关系
    print(f"\n🔗 创建 {len(relations_df)} 个关系...")
    created_rel_count = 0
    failed_count = 0
    
    for idx, row in relations_df.iterrows():
        node1 = str(row['start_id']) if pd.notna(row['start_id']) else ''
        node2 = str(row['end_id']) if pd.notna(row['end_id']) else ''
        edge = str(row['relation']) if pd.notna(row['relation']) else 'RELATED_TO'
        weight = float(row['confidence']) if pd.notna(row['confidence']) else 0.5
        
        # 跳过空节点
        if not node1 or not node2 or node1 == 'nan' or node2 == 'nan':
            failed_count += 1
            continue
        
        # 清理关系类型（Neo4j不允许某些字符）
        edge_clean = edge.replace(' ', '_').replace('|', '_').replace('-', '_')
        edge_clean = ''.join(c if c.isalnum() or c == '_' else '_' for c in edge_clean)
        if not edge_clean or edge_clean[0].isdigit():
            edge_clean = 'RELATED_TO'
        
        try:
            # 使用MERGE避免重复
            session.run(f"""
                MATCH (n1:Concept {{name: $node1}})
                MATCH (n2:Concept {{name: $node2}})
                MERGE (n1)-[r:{edge_clean}]->(n2)
                SET r.weight = $weight,
                    r.original_type = $edge
            """, node1=node1, node2=node2, weight=weight, edge=edge)
            created_rel_count += 1
        except Exception as e:
            # 如果关系类型有问题，使用默认类型
            try:
                session.run("""
                    MATCH (n1:Concept {name: $node1})
                    MATCH (n2:Concept {name: $node2})
                    MERGE (n1)-[r:RELATED_TO]->(n2)
                    SET r.weight = $weight,
                        r.original_type = $edge
                """, node1=node1, node2=node2, weight=weight, edge=edge)
                created_rel_count += 1
            except:
                failed_count += 1
        
        if (created_rel_count % 100 == 0):
            print(f"  进度: {created_rel_count}/{len(relations_df)}")
    
    print(f"  ✓ 创建了 {created_rel_count} 个关系")
    if failed_count > 0:
        print(f"  ⚠️  失败: {failed_count} 个关系")
    
    # 5. 验证结果
    print("\n✅ 验证导入结果...")
    result = session.run("MATCH (n) RETURN count(n) as count")
    node_count = result.single()['count']
    
    result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
    rel_count = result.single()['count']
    
    print(f"  节点总数: {node_count}")
    print(f"  关系总数: {rel_count}")

driver.close()

print("\n" + "="*80)
print("✓ 导入完成！")
print("="*80)
print("\n💡 在Neo4j Browser中查看:")
print("  URL: http://localhost:7474")
print("  查询示例: MATCH (n)-[r]-(m) RETURN n, r, m LIMIT 50")
