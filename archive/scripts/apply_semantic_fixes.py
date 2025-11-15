#!/usr/bin/env python3
"""
应用语义修复
"""
from neo4j import GraphDatabase
import json

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("应用语义修复")
print("="*80)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    
    # ========================================================================
    # 修复1: 删除所有"疾病寄生于X"的错误关系
    # ========================================================================
    print("\n修复1: 删除'疾病寄生于X'的错误关系...")
    result = session.run("""
        MATCH (disease {name: 'pine wilt disease'})-[r:寄生于]->()
        DELETE r
        RETURN count(*) as deleted
    """).single()
    
    print(f"  ✓ 删除了 {result['deleted']} 个错误关系")
    
    # ========================================================================
    # 修复2: 反转"寄主寄生于病原体"为"病原体寄生于寄主"
    # ========================================================================
    print("\n修复2: 反转'寄主寄生于病原体'...")
    
    # 获取所有错误的关系
    result = session.run("""
        MATCH (host)-[r:寄生于]->(pathogen {name: 'bursaphelenchus xylophilus'})
        WHERE host.entity_type = 'Host'
        RETURN host.name as host, r.weight as weight
    """)
    
    wrong_rels = list(result)
    print(f"  发现 {len(wrong_rels)} 个需要反转的关系")
    
    for rel in wrong_rels:
        host = rel['host']
        weight = rel['weight'] if rel['weight'] else 0.8
        
        # 删除错误关系
        session.run("""
            MATCH (host {name: $host})-[r:寄生于]->(pathogen {name: 'bursaphelenchus xylophilus'})
            DELETE r
        """, host=host)
        
        # 创建正确关系
        session.run("""
            MATCH (pathogen {name: 'bursaphelenchus xylophilus'})
            MATCH (host {name: $host})
            MERGE (pathogen)-[r:寄生于]->(host)
            SET r.weight = $weight, r.type = '寄生于'
        """, host=host, weight=weight)
        
        print(f"  ✓ 反转: {host} <- bursaphelenchus xylophilus")
    
    # ========================================================================
    # 修复3: 将"媒介寄生于寄主"改为"媒介取食寄主"
    # ========================================================================
    print("\n修复3: 将'媒介寄生于寄主'改为'取食'...")
    
    result = session.run("""
        MATCH (vector)-[r:寄生于]->(host)
        WHERE vector.entity_type = 'Vector' AND host.entity_type = 'Host'
        RETURN vector.name as vector, host.name as host, r.weight as weight
    """)
    
    vector_host_rels = list(result)
    print(f"  发现 {len(vector_host_rels)} 个需要修改的关系")
    
    for rel in vector_host_rels:
        vector = rel['vector']
        host = rel['host']
        weight = rel['weight'] if rel['weight'] else 0.7
        
        # 删除错误关系
        session.run("""
            MATCH (vector {name: $vector})-[r:寄生于]->(host {name: $host})
            DELETE r
        """, vector=vector, host=host)
        
        # 创建正确关系
        session.run("""
            MATCH (vector {name: $vector})
            MATCH (host {name: $host})
            MERGE (vector)-[r:取食]->(host)
            SET r.weight = $weight, r.type = '取食'
        """, vector=vector, host=host, weight=weight)
        
        print(f"  ✓ 修改: {vector} --[取食]--> {host}")
    
    # ========================================================================
    # 修复4: 反转"疾病引起病原体"
    # ========================================================================
    print("\n修复4: 反转'疾病引起病原体'...")
    
    result = session.run("""
        MATCH (disease {name: 'pine wilt disease'})-[r:引起]->(pathogen)
        WHERE pathogen.entity_type = 'Pathogen'
        RETURN pathogen.name as pathogen, r.weight as weight
    """)
    
    disease_cause_pathogen = list(result)
    
    for rel in disease_cause_pathogen:
        pathogen = rel['pathogen']
        weight = rel['weight'] if rel['weight'] else 0.9
        
        # 删除错误关系
        session.run("""
            MATCH (disease {name: 'pine wilt disease'})-[r:引起]->(pathogen {name: $pathogen})
            DELETE r
        """, pathogen=pathogen)
        
        # 创建正确关系
        session.run("""
            MATCH (pathogen {name: $pathogen})
            MATCH (disease {name: 'pine wilt disease'})
            MERGE (pathogen)-[r:引起]->(disease)
            SET r.weight = $weight, r.type = '引起'
        """, pathogen=pathogen, weight=weight)
        
        print(f"  ✓ 反转: {pathogen} --[引起]--> pine wilt disease")
    
    # ========================================================================
    # 修复5: 添加缺失的实体类型
    # ========================================================================
    print("\n修复5: 添加缺失的实体类型...")
    
    entity_types = {
        'sentinel-2': 'Technology',
        'red-edge band': 'Technology',
        'β-月桂烯': 'Chemical',
        '三脂酰甘油': 'Chemical',
        '华北植物区系': 'Location',
        '单木尺度': 'Concept',
        '有害生物风险分析': 'Method',
        '气象因子': 'Environment',
        '波段选择算法': 'Technology',
        '红光波段': 'Technology',
        '一阶导数光谱': 'Technology',
    }
    
    for entity, entity_type in entity_types.items():
        result = session.run("""
            MATCH (n {name: $name})
            SET n.entity_type = $type
            RETURN count(n) as updated
        """, name=entity, type=entity_type).single()
        
        if result and result['updated'] > 0:
            print(f"  ✓ {entity}: {entity_type}")
    
    # ========================================================================
    # 验证修复结果
    # ========================================================================
    print("\n" + "="*80)
    print("验证修复结果")
    print("="*80)
    
    # 检查1: 疾病寄生于X
    result = session.run("""
        MATCH (disease {name: 'pine wilt disease'})-[r:寄生于]->()
        RETURN count(r) as count
    """).single()['count']
    print(f"\n  疾病寄生于X: {result} {'✅' if result == 0 else '❌'}")
    
    # 检查2: 寄主寄生于病原体
    result = session.run("""
        MATCH (host)-[r:寄生于]->(pathogen {name: 'bursaphelenchus xylophilus'})
        WHERE host.entity_type = 'Host'
        RETURN count(r) as count
    """).single()['count']
    print(f"  寄主寄生于病原体: {result} {'✅' if result == 0 else '❌'}")
    
    # 检查3: 病原体寄生于寄主（正确）
    result = session.run("""
        MATCH (pathogen {name: 'bursaphelenchus xylophilus'})-[r:寄生于]->(host)
        WHERE host.entity_type = 'Host'
        RETURN count(r) as count
    """).single()['count']
    print(f"  病原体寄生于寄主（正确）: {result} {'✅' if result > 0 else '⚠️'}")
    
    # 检查4: 媒介寄生于寄主
    result = session.run("""
        MATCH (vector)-[r:寄生于]->(host)
        WHERE vector.entity_type = 'Vector' AND host.entity_type = 'Host'
        RETURN count(r) as count
    """).single()['count']
    print(f"  媒介寄生于寄主: {result} {'✅' if result == 0 else '❌'}")
    
    # 检查5: 疾病引起病原体
    result = session.run("""
        MATCH (disease {name: 'pine wilt disease'})-[r:引起]->(pathogen)
        WHERE pathogen.entity_type = 'Pathogen'
        RETURN count(r) as count
    """).single()['count']
    print(f"  疾病引起病原体: {result} {'✅' if result == 0 else '❌'}")
    
    # 统计
    print(f"\n最终统计:")
    node_count = session.run("MATCH (n) RETURN count(n) as count").single()['count']
    rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']
    print(f"  节点数: {node_count}")
    print(f"  关系数: {rel_count}")
    
    # 关系类型分布
    print(f"\n  关系类型分布（前10）:")
    result = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) as rel_type, count(*) as count
        ORDER BY count DESC
        LIMIT 10
    """)
    
    for record in result:
        print(f"    {record['rel_type']:25s}: {record['count']:3d}")

driver.close()

print("\n" + "="*80)
print("✓ 语义修复完成！")
print("="*80)

print("\n📌 下一步:")
print("  1. 导出验证: python3 export_triples.py")
print("  2. 重新分析: python3 deep_semantic_analysis.py")
print("  3. 在Neo4j Browser中验证: http://localhost:7474")
