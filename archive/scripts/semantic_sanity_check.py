#!/usr/bin/env python3
"""
对数据库进行语义和逻辑一致性检查
"""
from neo4j import GraphDatabase
from collections import defaultdict

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("数据库语义和逻辑一致性检查")
print("="*80)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

issues = []

with driver.session() as session:
    
    # ========================================================================
    # 1. 关系-类别逻辑检查
    # ========================================================================
    print("\n🔍 检查1: 关系-类别逻辑")
    print("-"*80)
    
    # 定义不合理的模式: (类别1)-[关系]->(类别2)
    invalid_patterns = [
        "MATCH (n1:地点)-[r:寄生于|引起|传播]->(n2) RETURN n1, r, n2",
        "MATCH (n1:技术)-[r:寄生于|感染]->(n2) RETURN n1, r, n2",
        "MATCH (n1:病原体)-[r:防治]->(n2) RETURN n1, r, n2", # 病原体不应是防治措施的主体
        "MATCH (n1:症状)-[r:传播]->(n2) RETURN n1, r, n2", # 症状本身不传播
        "MATCH (n1:寄主)-[r:媒介]->(n2) RETURN n1, r, n2", # 寄主不是媒介
    ]
    
    found_invalid_patterns = False
    for i, query in enumerate(invalid_patterns, 1):
        result = session.run(query)
        records = list(result)
        if records:
            found_invalid_patterns = True
            issue_desc = f"发现 {len(records)} 个不合逻辑的关系模式: {query.split(' ')[1]}"
            issues.append(issue_desc)
            print(f"  ❌ {issue_desc}")
            for record in records[:3]:
                n1 = record['n1']['name']
                n2 = record['n2']['name']
                r_type = record['r'].type
                print(f"     • {n1} --[{r_type}]--> {n2}")
    
    if not found_invalid_patterns:
        print("  ✅ 关系-类别逻辑一致")
    
    # ========================================================================
    # 2. 类别内孤立点分析
    # ========================================================================
    print("\n🔍 检查2: 类别内孤立点")
    print("-"*80)
    
    # 寄主应该连接到病原体或媒介
    result = session.run("""
        MATCH (h:寄主)
        WHERE NOT (h)--(:病原体) AND NOT (h)--(:媒介)
        RETURN h.name as name
    """)
    isolated_hosts = list(result)
    if isolated_hosts:
        issues.append(f"发现 {len(isolated_hosts)} 个未连接到病原体/媒介的寄主")
        print(f"  ❌ 发现 {len(isolated_hosts)} 个孤立寄主:")
        for node in isolated_hosts:
            print(f"     • {node['name']}")
    else:
        print("  ✅ 寄主连接完整")
    
    # 媒介应该连接到病原体或寄主
    result = session.run("""
        MATCH (v:媒介)
        WHERE NOT (v)--(:病原体) AND NOT (v)--(:寄主)
        RETURN v.name as name
    """)
    isolated_vectors = list(result)
    if isolated_vectors:
        issues.append(f"发现 {len(isolated_vectors)} 个未连接到病原体/寄主的媒介")
        print(f"  ❌ 发现 {len(isolated_vectors)} 个孤立媒介:")
        for node in isolated_vectors:
            print(f"     • {node['name']}")
    else:
        print("  ✅ 媒介连接完整")
    
    # ========================================================================
    # 3. “其他”类别深度审查
    # ========================================================================
    print("\n🔍 检查3: “其他”类别深度审查")
    print("-"*80)
    
    result = session.run("""
        MATCH (n:其他)
        RETURN n.name as name, n.importance as importance
        ORDER BY n.importance DESC
    """)
    
    other_nodes = list(result)
    if other_nodes:
        print(f"  发现 {len(other_nodes)} 个“其他”类别的实体，建议审查:")
        
        # 打印表格
        print("\n    {:<30s} | {:<10s} | {:<20s}".format("实体", "重要性", "建议类别"))
        print("    " + "-"*65)
        
        suggestions = []
        for node in other_nodes:
            name = node['name']
            name_lower = name.lower()
            suggestion = ""
            
            if any(kw in name_lower for kw in ['防治', '诱捕', '天敌', '药剂']):
                suggestion = "防治"
            elif any(kw in name_lower for kw in ['林', '树', '阔叶']):
                suggestion = "寄主"
            elif any(kw in name_lower for kw in ['温度', '湿度', '气候', '降水']):
                suggestion = "环境"
            elif any(kw in name_lower for kw in ['光谱', '遥感', '监测', '数据', '影像']):
                suggestion = "技术"
            
            if suggestion:
                suggestions.append((name, node['importance'], suggestion))
                print("    {:<30s} | {:<10d} | {:<20s}".format(name[:28], node['importance'], suggestion))
        
        if not suggestions:
            print("    未找到明显的重新分类建议")
    else:
        print("  ✅ 无“其他”类别的实体")
    
    # ========================================================================
    # 4. 检查对称/反对称关系
    # ========================================================================
    print("\n🔍 检查4: 关系逻辑一致性")
    print("-"*80)
    
    # A->B and B->A for asymmetric relations like '引起'
    result = session.run("""
        MATCH (a)-[r1:引起]->(b), (b)-[r2:引起]->(a)
        RETURN a.name as n1, b.name as n2
    """)
    
    reciprocal_causation = list(result)
    if reciprocal_causation:
        issues.append(f"发现 {len(reciprocal_causation)} 组相互“引起”关系")
        print(f"  ❌ 发现 {len(reciprocal_causation)} 组相互“引起”关系:")
        for rel in reciprocal_causation:
            print(f"     • {rel['n1']} <--> {rel['n2']}")
    else:
        print("  ✅ 无明显逻辑冲突关系")

driver.close()

# ============================================================================
# 总结
# ============================================================================
print("\n" + "="*80)
print("检测总结")
print("="*80)

if not issues:
    print("\n✅ 未发现明显的语义或逻辑错误！")
else:
    print(f"\n❌ 发现 {len(issues)} 个潜在问题:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")

print("\n" + "="*80)
print("建议操作")
print("="*80)

if issues:
    print("\n建议:")
    if any('不合逻辑' in i for i in issues):
        print("  • 手动审查并删除不合逻辑的关系")
    if any('孤立' in i for i in issues):
        print("  • 为孤立的类别节点补充必要的连接")
    if any('其他' in i for i in issues):
        print("  • 运行脚本批量修正“其他”类别的实体")

print("\n📌 可用工具:")
print("  • 交互式审查: python3 interactive_kg_review.py")
print("  • 在Neo4j Browser中手动修正: http://localhost:7474")
