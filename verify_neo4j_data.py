#!/usr/bin/env python3
"""
验证 Neo4j 中导入的三元组数据是否有明显错误
运行一系列检查查询
"""

from neo4j import GraphDatabase
import json

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def run_query(session, query, description=""):
    """运行查询并打印结果"""
    if description:
        print(f"\n{'='*80}")
        print(f"检查: {description}")
        print(f"{'='*80}")
    
    try:
        result = session.run(query)
        records = list(result)
        print(f"结果数: {len(records)}")
        for i, record in enumerate(records[:20], 1):  # 最多显示20条
            print(f"  {i}. {dict(record)}")
        if len(records) > 20:
            print(f"  ... 还有 {len(records) - 20} 条")
        return records
    except Exception as e:
        print(f"[错误] {e}")
        return []

with driver.session() as session:
    print("="*80)
    print("Neo4j 数据验证")
    print("="*80)
    
    # 1. 基本统计
    run_query(session, 
        "MATCH (n) RETURN count(n) as node_count, "
        "count(distinct labels(n)[0]) as label_types",
        "1. 基本统计 - 节点总数和标签类型")
    
    # 2. 节点类型分布
    run_query(session,
        "MATCH (n) RETURN labels(n)[0] as label, count(n) as count "
        "ORDER BY count DESC",
        "2. 节点类型分布")
    
    # 3. 关系类型分布
    run_query(session,
        "MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count "
        "ORDER BY count DESC",
        "3. 关系类型分布")
    
    # 4. 检查是否有孤立节点（度数为0）
    run_query(session,
        "MATCH (n) WHERE (n.total_degree IS NULL OR n.total_degree = 0) "
        "RETURN n.name as node_name, labels(n)[0] as label",
        "4. 孤立节点检查（度数为0）")
    
    # 5. 检查是否有自环关系（同一节点的自连接）
    run_query(session,
        "MATCH (n)-[r]->(n) RETURN n.name as node_name, type(r) as rel_type, r.weight as weight",
        "5. 自环关系检查")
    
    # 6. 检查重复关系（同一对节点之间的多条相同关系）
    run_query(session,
        "MATCH (a)-[r1]->(b) WITH a, b, type(r1) as rel_type, count(r1) as cnt "
        "WHERE cnt > 1 RETURN a.name as node1, rel_type, b.name as node2, cnt",
        "6. 重复关系检查")
    
    # 7. 检查关键关系的方向是否正确
    print(f"\n{'='*80}")
    print("检查: 7. 关键关系的方向和类型")
    print(f"{'='*80}")
    
    # 7a. INFECTS 关系：应该是 Pathogen -> Host
    run_query(session,
        "MATCH (s)-[r:INFECTS]->(t) "
        "RETURN labels(s)[0] as s_type, s.name as s_name, "
        "labels(t)[0] as t_type, t.name as t_name, r.weight as weight",
        "7a. INFECTS 关系（应为 Pathogen -> Host）")
    
    # 7b. CAUSES 关系：应该是 Pathogen -> Disease
    run_query(session,
        "MATCH (s)-[r:CAUSES]->(t) "
        "RETURN labels(s)[0] as s_type, s.name as s_name, "
        "labels(t)[0] as t_type, t.name as t_name, r.weight as weight",
        "7b. CAUSES 关系（应为 Pathogen -> Disease）")
    
    # 7c. TRANSMITS 关系：应该是 Vector -> Pathogen 或 Vector -> Disease
    run_query(session,
        "MATCH (s)-[r:TRANSMITS]->(t) "
        "RETURN labels(s)[0] as s_type, s.name as s_name, "
        "labels(t)[0] as t_type, t.name as t_name, r.weight as weight",
        "7c. TRANSMITS 关系（应为 Vector -> Pathogen/Disease）")
    
    # 7d. FEEDS_ON 关系：应该是 Vector -> Host
    run_query(session,
        "MATCH (s)-[r:FEEDS_ON]->(t) "
        "RETURN labels(s)[0] as s_type, s.name as s_name, "
        "labels(t)[0] as t_type, t.name as t_name, r.weight as weight",
        "7d. FEEDS_ON 关系（应为 Vector -> Host）")
    
    # 7e. TREATS/CONTROLS 关系：应该是 ControlMeasure -> Disease/Pathogen/Vector
    run_query(session,
        "MATCH (s)-[r:TREATS|CONTROLS]->(t) "
        "RETURN type(r) as rel_type, labels(s)[0] as s_type, s.name as s_name, "
        "labels(t)[0] as t_type, t.name as t_name, r.weight as weight",
        "7e. TREATS/CONTROLS 关系（应为 ControlMeasure -> Disease/Pathogen/Vector）")
    
    # 7f. DISTRIBUTED_IN 关系：应该是 Disease/Host/Vector -> Location
    run_query(session,
        "MATCH (s)-[r:DISTRIBUTED_IN]->(t) "
        "RETURN labels(s)[0] as s_type, s.name as s_name, "
        "labels(t)[0] as t_type, t.name as t_name, r.weight as weight",
        "7f. DISTRIBUTED_IN 关系（应为 Disease/Host/Vector -> Location）")
    
    # 7g. SYMPTOM_OF 关系：应该是 Symptom -> Disease/Pathogen
    run_query(session,
        "MATCH (s)-[r:SYMPTOM_OF]->(t) "
        "RETURN labels(s)[0] as s_type, s.name as s_name, "
        "labels(t)[0] as t_type, t.name as t_name, r.weight as weight",
        "7g. SYMPTOM_OF 关系（应为 Symptom -> Disease/Pathogen）")
    
    # 8. 检查权重分布
    run_query(session,
        "MATCH ()-[r]->() "
        "RETURN "
        "  min(r.weight) as min_weight, "
        "  max(r.weight) as max_weight, "
        "  avg(r.weight) as avg_weight, "
        "  count(r) as total_rels",
        "8. 权重统计")
    
    # 9. 检查异常权重（权重为0或>1）
    run_query(session,
        "MATCH (s)-[r]->(t) "
        "WHERE r.weight IS NOT NULL AND (r.weight < 0 OR r.weight > 1) "
        "RETURN s.name as node1, type(r) as rel_type, t.name as node2, r.weight as weight",
        "9. 异常权重检查（<0 或 >1）")
    
    # 10. 度数最高的节点
    run_query(session,
        "MATCH (n) "
        "RETURN n.name as node_name, labels(n)[0] as label, "
        "n.total_degree as degree "
        "ORDER BY degree DESC LIMIT 15",
        "10. 度数最高的节点（前15）")
    
    # 11. 检查是否有"Other"类型的节点（可能是分类失败）
    run_query(session,
        "MATCH (n:Other) "
        "RETURN n.name as node_name, n.total_degree as degree "
        "ORDER BY degree DESC",
        "11. 'Other' 类型节点检查（可能分类失败）")
    
    # 12. 检查关键节点是否存在
    print(f"\n{'='*80}")
    print("检查: 12. 关键节点是否存在")
    print(f"{'='*80}")
    
    key_nodes = [
        "pine wilt disease",
        "bursaphelenchus xylophilus",
        "monochamus alternatus",
        "pinus massoniana",
        "biological control"
    ]
    
    for node_name in key_nodes:
        result = session.run(
            "MATCH (n) WHERE n.name = $name "
            "RETURN n.name as name, labels(n)[0] as label, n.total_degree as degree",
            name=node_name
        )
        records = list(result)
        if records:
            rec = records[0]
            print(f"  ✓ {node_name}: {dict(rec)}")
        else:
            print(f"  ✗ {node_name}: 不存在")
    
    print(f"\n{'='*80}")
    print("验证完成")
    print(f"{'='*80}")

driver.close()
