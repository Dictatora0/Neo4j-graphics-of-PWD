#!/usr/bin/env python3
"""
优化 Neo4j 中节点的 label（类型标签）
根据生物学语义和知识图谱最佳实践进行细化
"""

from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 80)
print("优化 Neo4j 节点标签（Label）")
print("=" * 80)

# 定义所有要修正的标签映射
# 格式: (节点名称列表, 旧标签, 新标签, 描述)
label_fixes = [
    # 1.1 病原菌相关
    (
        ['pine wood nematode associated bacteria'],
        'Host',
        'Pathogen',
        "伴生病原菌：从 Host 改为 Pathogen"
    ),
    
    # 1.2 症状相关
    (
        ['leaf'],
        'Other',
        'Symptom',
        "叶片症状：从 Other 改为 Symptom"
    ),
    
    # 1.3 环境因子
    (
        ['meteorological factors', 'cold stress'],
        'Other',
        'EnvironmentalFactor',
        "环境因子：从 Other 改为 EnvironmentalFactor"
    ),
    
    # 1.4 地点/景点
    (
        ['dexing city', 'quannan county', 'nantian gate', 'taohua valley', 'zhulin temple', 'yuquan temple'],
        'Other',
        'Location',
        "地名/景点：从 Other 改为 Location"
    ),
    
    # 1.5 技术/方法
    (
        ['early detection of pwd', 'red band', 'red-edge band', 'first derivative spectrum', 'pest risk analysis'],
        'Other',
        'Technology',
        "技术/方法：从 Other 改为 Technology"
    ),
]

with driver.session() as session:
    total_updated = 0
    
    for node_names, old_label, new_label, description in label_fixes:
        print(f"\n{description}")
        print(f"  节点数: {len(node_names)}")
        
        for node_name in node_names:
            # 检查节点是否存在且有旧标签
            check_query = f"""
            MATCH (n:{old_label})
            WHERE n.name = $name
            RETURN n.name as name, labels(n) as labels
            """
            
            result = session.run(check_query, name=node_name)
            record = result.single()
            
            if record:
                # 执行标签修正
                update_query = f"""
                MATCH (n:{old_label})
                WHERE n.name = $name
                REMOVE n:{old_label}
                SET n:{new_label}
                RETURN n.name as name, labels(n) as labels
                """
                
                result = session.run(update_query, name=node_name)
                updated = result.single()
                
                if updated:
                    print(f"    已更新: {node_name}")
                    print(f"      标签: {updated['labels']}")
                    total_updated += 1
                else:
                    print(f"    ✗ {node_name} - 更新失败")
            else:
                print(f"    ⚠ {node_name} - 未找到或已有新标签")
    
    # 验证修正结果
    print(f"\n{'='*80}")
    print("验证修正结果")
    print(f"{'='*80}")
    
    # 统计各标签类型的节点数
    verify_query = """
    MATCH (n)
    RETURN labels(n)[0] as label, count(n) as count
    ORDER BY count DESC
    """
    
    result = session.run(verify_query)
    records = list(result)
    
    print("\n修正后的节点类型分布:")
    for record in records:
        print(f"  {record['label']:20s}: {record['count']:3d}")
    
    # 检查是否还有 Other 类型的节点
    other_query = """
    MATCH (n:Other)
    RETURN n.name as name, n.total_degree as degree
    ORDER BY degree DESC
    """
    
    result = session.run(other_query)
    other_nodes = list(result)
    
    if other_nodes:
        print(f"\n仍然是 'Other' 类型的节点（共 {len(other_nodes)} 个）:")
        for record in other_nodes[:10]:
            print(f"  - {record['name']} (度数: {record['degree']})")
        if len(other_nodes) > 10:
            print(f"  ... 还有 {len(other_nodes) - 10} 个")
    else:
        print("\n没有 'Other' 类型的节点了！")
    
    # 检查关键节点的新标签
    print(f"\n{'='*80}")
    print("关键节点标签验证")
    print(f"{'='*80}")
    
    key_nodes = [
        'pine wood nematode associated bacteria',
        'leaf',
        'meteorological factors',
        'cold stress',
        'dexing city',
        'early detection of pwd',
        'red band'
    ]
    
    for node_name in key_nodes:
        query = """
        MATCH (n)
        WHERE n.name = $name
        RETURN n.name as name, labels(n)[0] as label, n.total_degree as degree
        """
        
        result = session.run(query, name=node_name)
        record = result.single()
        
        if record:
            print(f"  {record['name']:40s}: {record['label']:20s} (度数: {record['degree']})")
        else:
            print(f"  ✗ {node_name:40s}: 未找到")

print(f"\n{'='*80}")
print("节点标签优化完成。")
print(f"{'='*80}")

driver.close()
