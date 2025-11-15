#!/usr/bin/env python3
"""
修复检测到的数据库问题
"""
from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("修复数据库问题")
print("="*80)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    
    # ========================================================================
    # 1. 删除自环关系
    # ========================================================================
    print("\n🔧 修复1: 删除自环关系")
    print("-"*80)
    
    result = session.run("""
        MATCH (n)-[r]->(n)
        RETURN count(r) as count
    """)
    self_loop_count = result.single()['count']
    
    if self_loop_count > 0:
        print(f"  发现 {self_loop_count} 个自环关系")
        
        # 显示将要删除的自环
        result = session.run("""
            MATCH (n)-[r]->(n)
            RETURN n.name as name, type(r) as rel_type
            LIMIT 10
        """)
        
        print(f"  将删除的自环示例:")
        for record in result:
            print(f"    • {record['name']} --[{record['rel_type']}]--> {record['name']}")
        
        # 删除自环
        result = session.run("""
            MATCH (n)-[r]->(n)
            DELETE r
            RETURN count(*) as deleted
        """)
        
        deleted = result.single()['deleted']
        print(f"  ✅ 已删除 {deleted} 个自环关系")
    else:
        print(f"  ✅ 无自环关系需要删除")
    
    # ========================================================================
    # 2. 处理低连接度节点
    # ========================================================================
    print("\n🔧 修复2: 处理低连接度节点")
    print("-"*80)
    
    result = session.run("""
        MATCH (n:Concept)
        WITH n, COUNT {(n)--()} as degree
        WHERE degree <= 2
        RETURN n.name as name, n.category as category, degree
        ORDER BY degree
    """)
    
    low_degree_nodes = list(result)
    
    if low_degree_nodes:
        print(f"  发现 {len(low_degree_nodes)} 个低连接度节点:")
        for node in low_degree_nodes:
            print(f"    • {node['name']} ({node['category']}) - {node['degree']} 个连接")
        
        print(f"\n  选项:")
        print(f"    1. 保留所有节点")
        print(f"    2. 删除连接度=2的节点")
        print(f"    3. 手动选择")
        
        choice = input("\n  选择 (1-3, 默认1): ").strip()
        
        if choice == '2':
            result = session.run("""
                MATCH (n:Concept)
                WITH n, COUNT {(n)--()} as degree
                WHERE degree = 2
                DETACH DELETE n
                RETURN count(*) as deleted
            """)
            deleted = result.single()['deleted']
            print(f"  ✅ 已删除 {deleted} 个节点")
        elif choice == '3':
            for node in low_degree_nodes:
                delete = input(f"  删除 '{node['name']}'? (y/n): ").strip().lower()
                if delete == 'y':
                    session.run("""
                        MATCH (n:Concept {name: $name})
                        DETACH DELETE n
                    """, name=node['name'])
                    print(f"    ✓ 已删除")
        else:
            print(f"  ✅ 保留所有节点")
    else:
        print(f"  ✅ 无低连接度节点")
    
    # ========================================================================
    # 3. 验证修复结果
    # ========================================================================
    print("\n✅ 验证修复结果")
    print("-"*80)
    
    # 统计节点和关系
    result = session.run("MATCH (n) RETURN count(n) as count")
    node_count = result.single()['count']
    
    result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
    rel_count = result.single()['count']
    
    print(f"  当前节点数: {node_count}")
    print(f"  当前关系数: {rel_count}")
    
    # 检查自环
    result = session.run("""
        MATCH (n)-[r]->(n)
        RETURN count(r) as count
    """)
    remaining_loops = result.single()['count']
    print(f"  剩余自环: {remaining_loops} 个 {'✅' if remaining_loops == 0 else '⚠️'}")
    
    # 检查低连接度
    result = session.run("""
        MATCH (n:Concept)
        WITH n, COUNT {(n)--()} as degree
        WHERE degree <= 2
        RETURN count(n) as count
    """)
    remaining_low = result.single()['count']
    print(f"  低连接度节点: {remaining_low} 个")
    
    # 关系类型分布
    result = session.run("""
        MATCH ()-[r]->()
        WITH type(r) as rel_type, count(*) as count
        RETURN rel_type, count
        ORDER BY count DESC
        LIMIT 5
    """)
    
    print(f"\n  关系类型分布（前5）:")
    for record in result:
        rel_type = record['rel_type'][:30] if len(record['rel_type']) > 30 else record['rel_type']
        pct = record['count'] / rel_count * 100 if rel_count > 0 else 0
        print(f"    • {rel_type:32s}: {record['count']:3d} ({pct:5.1f}%)")

driver.close()

print("\n" + "="*80)
print("✓ 修复完成")
print("="*80)

print("\n📌 下一步:")
print("  1. 重新检测: python3 detect_issues.py")
print("  2. 查看详情: python3 inspect_database.py")
print("  3. 在Neo4j Browser中验证: http://localhost:7474")
