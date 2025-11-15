#!/usr/bin/env python3
"""
检测Neo4j数据库中的潜在问题
"""
from neo4j import GraphDatabase
from collections import defaultdict

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("Neo4j 数据库问题检测")
print("="*80)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

issues = []
warnings = []

with driver.session() as session:
    
    # ========================================================================
    # 1. 检查孤立节点
    # ========================================================================
    print("\n🔍 检查1: 孤立节点")
    print("-"*80)
    
    result = session.run("""
        MATCH (n:Concept)
        WHERE NOT (n)--()
        RETURN n.name as name, n.category as category
    """)
    
    isolated_nodes = list(result)
    if isolated_nodes:
        issues.append(f"发现 {len(isolated_nodes)} 个孤立节点（无任何连接）")
        print(f"  ❌ 发现 {len(isolated_nodes)} 个孤立节点:")
        for node in isolated_nodes:
            print(f"     • {node['name']} ({node['category']})")
    else:
        print(f"  ✅ 无孤立节点")
    
    # ========================================================================
    # 2. 检查低连接度节点
    # ========================================================================
    print("\n🔍 检查2: 低连接度节点（≤2个连接）")
    print("-"*80)
    
    result = session.run("""
        MATCH (n:Concept)
        WITH n, COUNT {(n)--()} as degree
        WHERE degree <= 2
        RETURN n.name as name, n.category as category, degree
        ORDER BY degree, n.name
    """)
    
    low_degree_nodes = list(result)
    if low_degree_nodes:
        warnings.append(f"发现 {len(low_degree_nodes)} 个低连接度节点")
        print(f"  ⚠️  发现 {len(low_degree_nodes)} 个低连接度节点:")
        for node in low_degree_nodes[:10]:
            print(f"     • {node['name']:30s} ({node['category']:10s}) - {node['degree']} 个连接")
        if len(low_degree_nodes) > 10:
            print(f"     ... 还有 {len(low_degree_nodes) - 10} 个")
    else:
        print(f"  ✅ 所有节点连接度 > 2")
    
    # ========================================================================
    # 3. 检查重复关系
    # ========================================================================
    print("\n🔍 检查3: 重复关系")
    print("-"*80)
    
    result = session.run("""
        MATCH (n1)-[r]->(n2)
        WITH n1, n2, type(r) as rel_type, count(*) as count
        WHERE count > 1
        RETURN n1.name as node1, rel_type, n2.name as node2, count
        ORDER BY count DESC
        LIMIT 10
    """)
    
    duplicates = list(result)
    if duplicates:
        issues.append(f"发现 {len(duplicates)} 组重复关系")
        print(f"  ❌ 发现重复关系:")
        for dup in duplicates:
            print(f"     • {dup['node1']} --[{dup['rel_type']}]--> {dup['node2']} (×{dup['count']})")
    else:
        print(f"  ✅ 无重复关系")
    
    # ========================================================================
    # 4. 检查自环关系
    # ========================================================================
    print("\n🔍 检查4: 自环关系（节点指向自己）")
    print("-"*80)
    
    result = session.run("""
        MATCH (n)-[r]->(n)
        RETURN n.name as name, type(r) as rel_type, n.category as category
    """)
    
    self_loops = list(result)
    if self_loops:
        warnings.append(f"发现 {len(self_loops)} 个自环关系")
        print(f"  ⚠️  发现 {len(self_loops)} 个自环关系:")
        for loop in self_loops:
            print(f"     • {loop['name']} --[{loop['rel_type']}]--> {loop['name']} ({loop['category']})")
    else:
        print(f"  ✅ 无自环关系")
    
    # ========================================================================
    # 5. 检查异常权重
    # ========================================================================
    print("\n🔍 检查5: 异常权重值")
    print("-"*80)
    
    # 权重为0或负数
    result = session.run("""
        MATCH (n1)-[r]->(n2)
        WHERE r.weight IS NOT NULL AND r.weight <= 0
        RETURN n1.name as node1, type(r) as rel_type, n2.name as node2, r.weight as weight
        LIMIT 10
    """)
    
    zero_weights = list(result)
    if zero_weights:
        warnings.append(f"发现 {len(zero_weights)} 个零/负权重关系")
        print(f"  ⚠️  发现零/负权重关系:")
        for rel in zero_weights:
            print(f"     • {rel['node1']} --[{rel['rel_type']}]--> {rel['node2']} (权重:{rel['weight']})")
    else:
        print(f"  ✅ 所有权重值正常")
    
    # 权重异常高（>1.5）
    result = session.run("""
        MATCH (n1)-[r]->(n2)
        WHERE r.weight IS NOT NULL AND r.weight > 1.5
        RETURN n1.name as node1, type(r) as rel_type, n2.name as node2, r.weight as weight
        ORDER BY r.weight DESC
        LIMIT 5
    """)
    
    high_weights = list(result)
    if high_weights:
        warnings.append(f"发现 {len(high_weights)} 个异常高权重关系（>1.5）")
        print(f"  ⚠️  发现异常高权重关系:")
        for rel in high_weights:
            print(f"     • {rel['node1']} --[{rel['rel_type']}]--> {rel['node2']} (权重:{rel['weight']:.3f})")
    
    # ========================================================================
    # 6. 检查类别一致性
    # ========================================================================
    print("\n🔍 检查6: 类别一致性")
    print("-"*80)
    
    # 检查是否有节点缺少类别
    result = session.run("""
        MATCH (n:Concept)
        WHERE n.category IS NULL OR n.category = ''
        RETURN n.name as name
    """)
    
    no_category = list(result)
    if no_category:
        issues.append(f"发现 {len(no_category)} 个节点缺少类别")
        print(f"  ❌ 发现节点缺少类别:")
        for node in no_category:
            print(f"     • {node['name']}")
    else:
        print(f"  ✅ 所有节点都有类别")
    
    # 检查类别分布是否合理
    result = session.run("""
        MATCH (n:Concept)
        RETURN n.category as category, count(*) as count
        ORDER BY count DESC
    """)
    
    categories = list(result)
    total_nodes = sum(c['count'] for c in categories)
    
    print(f"\n  类别分布:")
    for cat in categories:
        pct = cat['count'] / total_nodes * 100
        status = "⚠️" if cat['category'] == '其他' and pct > 40 else "✅"
        print(f"    {status} {cat['category']:15s}: {cat['count']:3d} ({pct:5.1f}%)")
    
    other_pct = next((c['count']/total_nodes*100 for c in categories if c['category'] == '其他'), 0)
    if other_pct > 40:
        warnings.append(f"'其他'类别占比过高 ({other_pct:.1f}%)")
    
    # ========================================================================
    # 7. 检查关系类型合理性
    # ========================================================================
    print("\n🔍 检查7: 关系类型合理性")
    print("-"*80)
    
    # 检查是否有过长的关系类型
    result = session.run("""
        MATCH ()-[r]->()
        WITH type(r) as rel_type, count(*) as count
        WHERE size(rel_type) > 50
        RETURN rel_type, count
        ORDER BY count DESC
        LIMIT 5
    """)
    
    long_rel_types = list(result)
    if long_rel_types:
        warnings.append(f"发现 {len(long_rel_types)} 个过长的关系类型")
        print(f"  ⚠️  发现过长的关系类型:")
        for rel in long_rel_types:
            rel_display = rel['rel_type'][:60] + "..." if len(rel['rel_type']) > 60 else rel['rel_type']
            print(f"     • {rel_display} (×{rel['count']})")
    else:
        print(f"  ✅ 关系类型长度正常")
    
    # 检查co-occurs关系占比
    result = session.run("""
        MATCH ()-[r]->()
        WITH type(r) as rel_type, count(*) as count
        RETURN rel_type, count
        ORDER BY count DESC
    """)
    
    rel_types = list(result)
    total_rels = sum(r['count'] for r in rel_types)
    co_occurs_count = sum(r['count'] for r in rel_types if 'co_occurs' in r['rel_type'].lower())
    co_occurs_pct = co_occurs_count / total_rels * 100 if total_rels > 0 else 0
    
    print(f"\n  关系类型分布:")
    print(f"    co-occurs关系: {co_occurs_count} ({co_occurs_pct:.1f}%)")
    print(f"    语义关系: {total_rels - co_occurs_count} ({100-co_occurs_pct:.1f}%)")
    
    if co_occurs_pct > 80:
        warnings.append(f"co-occurs关系占比过高 ({co_occurs_pct:.1f}%)")
        print(f"    ⚠️  co-occurs关系占比过高")
    
    # ========================================================================
    # 8. 检查关键节点缺失
    # ========================================================================
    print("\n🔍 检查8: 关键节点检查")
    print("-"*80)
    
    key_entities = [
        ('bursaphelenchus xylophilus', '病原体'),
        ('pine wilt disease', '疾病'),
        ('monochamus alternatus', '媒介'),
        ('pinus thunbergii', '寄主'),
        ('马尾松', '寄主'),
    ]
    
    missing_key = []
    for entity, expected_cat in key_entities:
        result = session.run("""
            MATCH (n:Concept {name: $name})
            RETURN n.name as name, n.category as category
        """, name=entity)
        
        node = result.single()
        if not node:
            missing_key.append(entity)
            print(f"  ❌ 缺少关键节点: {entity} ({expected_cat})")
        else:
            if node['category'] != expected_cat:
                print(f"  ⚠️  {entity}: 类别不匹配 (期望:{expected_cat}, 实际:{node['category']})")
            else:
                print(f"  ✅ {entity} ({expected_cat})")
    
    if missing_key:
        issues.append(f"缺少 {len(missing_key)} 个关键节点")
    
    # ========================================================================
    # 9. 检查关键路径
    # ========================================================================
    print("\n🔍 检查9: 关键传播路径完整性")
    print("-"*80)
    
    # 病原体 -> 媒介
    result = session.run("""
        MATCH (pathogen:Concept)-[r]-(vector:Concept)
        WHERE pathogen.category = '病原体' AND vector.category = '媒介'
        RETURN count(*) as count
    """)
    pathogen_vector = result.single()['count']
    
    # 媒介 -> 寄主
    result = session.run("""
        MATCH (vector:Concept)-[r]-(host:Concept)
        WHERE vector.category = '媒介' AND host.category = '寄主'
        RETURN count(*) as count
    """)
    vector_host = result.single()['count']
    
    # 疾病 -> 症状
    result = session.run("""
        MATCH (disease:Concept)-[r]-(symptom:Concept)
        WHERE disease.category = '疾病' AND symptom.category = '症状'
        RETURN count(*) as count
    """)
    disease_symptom = result.single()['count']
    
    print(f"  病原体 <-> 媒介: {pathogen_vector} 个关系 {'✅' if pathogen_vector > 0 else '❌'}")
    print(f"  媒介 <-> 寄主: {vector_host} 个关系 {'✅' if vector_host > 0 else '❌'}")
    print(f"  疾病 <-> 症状: {disease_symptom} 个关系 {'✅' if disease_symptom > 0 else '❌'}")
    
    if pathogen_vector == 0 or vector_host == 0:
        issues.append("关键传播路径不完整")
    
    # ========================================================================
    # 10. 检查数据完整性
    # ========================================================================
    print("\n🔍 检查10: 数据完整性")
    print("-"*80)
    
    # 检查重要性字段
    result = session.run("""
        MATCH (n:Concept)
        WHERE n.importance IS NULL
        RETURN count(n) as count
    """)
    no_importance = result.single()['count']
    
    if no_importance > 0:
        warnings.append(f"{no_importance} 个节点缺少重要性值")
        print(f"  ⚠️  {no_importance} 个节点缺少重要性值")
    else:
        print(f"  ✅ 所有节点都有重要性值")
    
    # 检查权重字段
    result = session.run("""
        MATCH ()-[r]->()
        WHERE r.weight IS NULL
        RETURN count(r) as count
    """)
    no_weight = result.single()['count']
    
    if no_weight > 0:
        warnings.append(f"{no_weight} 个关系缺少权重值")
        print(f"  ⚠️  {no_weight} 个关系缺少权重值")
    else:
        print(f"  ✅ 所有关系都有权重值")

driver.close()

# ============================================================================
# 总结
# ============================================================================
print("\n" + "="*80)
print("检测总结")
print("="*80)

if not issues and not warnings:
    print("\n✅ 未发现严重问题！数据库状态良好。")
else:
    if issues:
        print(f"\n❌ 发现 {len(issues)} 个严重问题:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    
    if warnings:
        print(f"\n⚠️  发现 {len(warnings)} 个警告:")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")

print("\n" + "="*80)
print("建议操作")
print("="*80)

if issues or warnings:
    print("\n根据检测结果，建议:")
    
    if any('孤立节点' in i for i in issues):
        print("  • 删除孤立节点或为其添加关系")
    
    if any('重复关系' in i for i in issues):
        print("  • 运行去重脚本合并重复关系")
    
    if any('其他' in w for w in warnings):
        print("  • 重新审查'其他'类别的实体，进行更精确的分类")
    
    if any('co-occurs' in w for w in warnings):
        print("  • 考虑增加更多语义关系，减少共现关系占比")
    
    if any('低连接度' in w for w in warnings):
        print("  • 审查低连接度节点，考虑删除或补充关系")

print("\n📌 可用工具:")
print("  • 交互式审查: python3 interactive_kg_review.py")
print("  • 自动消歧: python3 auto_disambiguate.py")
print("  • 查看详情: python3 inspect_database.py")
