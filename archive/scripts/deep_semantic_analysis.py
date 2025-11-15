#!/usr/bin/env python3
"""
深入语义分析：检测并修复所有语义错误
"""
from neo4j import GraphDatabase
import pandas as pd
from collections import defaultdict

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("深入语义分析")
print("="*80)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

issues = []
fixes = []

with driver.session() as session:
    
    # ========================================================================
    # 分析1: 生物学逻辑错误
    # ========================================================================
    print("\n" + "="*80)
    print("分析1: 生物学逻辑错误")
    print("="*80)
    
    # 1.1 检查"寄生于"关系的方向
    print("\n  1.1 检查'寄生于'关系...")
    result = session.run("""
        MATCH (n1)-[r:寄生于]->(n2)
        RETURN n1.name as source, n1.entity_type as source_type,
               n2.name as target, n2.entity_type as target_type,
               r.weight as weight
    """)
    
    parasitism_rels = list(result)
    print(f"  发现 {len(parasitism_rels)} 个'寄生于'关系")
    
    for rel in parasitism_rels:
        source = rel['source']
        target = rel['target']
        source_type = rel['source_type']
        target_type = rel['target_type']
        
        # 检查逻辑错误
        # 病原体应该寄生于寄主，不应该反过来
        if source_type == 'Host' and target_type == 'Pathogen':
            issues.append(f"错误: 寄主寄生于病原体 - {source} -> {target}")
            fixes.append(('reverse_parasitism', source, target, rel['weight']))
            print(f"  ❌ {source} ({source_type}) --[寄生于]--> {target} ({target_type})")
        
        # 疾病不应该寄生于任何东西
        elif source_type == 'Disease':
            issues.append(f"错误: 疾病寄生于X - {source} -> {target}")
            fixes.append(('delete_disease_parasitism', source, target, None))
            print(f"  ❌ {source} (Disease) --[寄生于]--> {target}")
        
        # 媒介不应该寄生于寄主（应该是"取食"或"携带"）
        elif source_type == 'Vector' and target_type == 'Host':
            issues.append(f"错误: 媒介寄生于寄主 - {source} -> {target}")
            fixes.append(('change_vector_host', source, target, rel['weight']))
            print(f"  ⚠️  {source} (Vector) --[寄生于]--> {target} (Host) [应改为'取食']")
    
    # 1.2 检查"引起"关系的方向
    print("\n  1.2 检查'引起'关系...")
    result = session.run("""
        MATCH (n1)-[r:引起]->(n2)
        RETURN n1.name as source, n1.entity_type as source_type,
               n2.name as target, n2.entity_type as target_type
    """)
    
    causation_rels = list(result)
    print(f"  发现 {len(causation_rels)} 个'引起'关系")
    
    for rel in causation_rels:
        source = rel['source']
        target = rel['target']
        source_type = rel['source_type']
        target_type = rel['target_type']
        
        # 疾病不能引起病原体
        if source_type == 'Disease' and target_type == 'Pathogen':
            issues.append(f"错误: 疾病引起病原体 - {source} -> {target}")
            fixes.append(('reverse_causation', source, target, None))
            print(f"  ❌ {source} (Disease) --[引起]--> {target} (Pathogen)")
        
        # 症状不能引起疾病
        elif source_type == 'Symptom' and target_type == 'Disease':
            issues.append(f"错误: 症状引起疾病 - {source} -> {target}")
            fixes.append(('reverse_causation', source, target, None))
            print(f"  ❌ {source} (Symptom) --[引起]--> {target} (Disease)")
    
    # 1.3 检查"传播"关系
    print("\n  1.3 检查'传播'关系...")
    result = session.run("""
        MATCH (n1)-[r:传播]->(n2)
        RETURN n1.name as source, n1.entity_type as source_type,
               n2.name as target, n2.entity_type as target_type
    """)
    
    transmission_rels = list(result)
    print(f"  发现 {len(transmission_rels)} 个'传播'关系")
    
    for rel in transmission_rels:
        source = rel['source']
        target = rel['target']
        source_type = rel['source_type']
        target_type = rel['target_type']
        
        # 疾病不能主动传播
        if source_type == 'Disease':
            issues.append(f"错误: 疾病主动传播 - {source} -> {target}")
            fixes.append(('delete_disease_transmission', source, target, None))
            print(f"  ❌ {source} (Disease) --[传播]--> {target}")
        
        # 寄主不能传播
        elif source_type == 'Host':
            issues.append(f"错误: 寄主传播 - {source} -> {target}")
            fixes.append(('delete_host_transmission', source, target, None))
            print(f"  ❌ {source} (Host) --[传播]--> {target}")
    
    # ========================================================================
    # 分析2: 关系语义不当
    # ========================================================================
    print("\n" + "="*80)
    print("分析2: 关系语义不当")
    print("="*80)
    
    # 2.1 技术/方法不应该"影响"疾病，应该是"监测"
    print("\n  2.1 检查技术关系...")
    result = session.run("""
        MATCH (tech)-[r:影响]->(disease)
        WHERE tech.entity_type = 'Technology' AND disease.entity_type = 'Disease'
        RETURN tech.name as tech, disease.name as disease
    """)
    
    tech_affects = list(result)
    if tech_affects:
        print(f"  发现 {len(tech_affects)} 个'技术影响疾病'的错误")
        for rel in tech_affects:
            issues.append(f"错误: 技术影响疾病 - {rel['tech']} -> {rel['disease']}")
            fixes.append(('change_tech_affects', rel['tech'], rel['disease'], None))
            print(f"  ⚠️  {rel['tech']} --[影响]--> {rel['disease']} [应改为'监测']")
    
    # 2.2 环境因素应该"影响"而非"寄生于"
    print("\n  2.2 检查环境关系...")
    result = session.run("""
        MATCH (env)-[r:寄生于]->(n)
        WHERE env.entity_type = 'Environment'
        RETURN env.name as env, n.name as target
    """)
    
    env_parasitism = list(result)
    if env_parasitism:
        print(f"  发现 {len(env_parasitism)} 个'环境寄生'的错误")
        for rel in env_parasitism:
            issues.append(f"错误: 环境寄生 - {rel['env']} -> {rel['target']}")
            fixes.append(('delete_env_parasitism', rel['env'], rel['target'], None))
            print(f"  ❌ {rel['env']} (Environment) --[寄生于]--> {rel['target']}")
    
    # ========================================================================
    # 分析3: 实体类型缺失或错误
    # ========================================================================
    print("\n" + "="*80)
    print("分析3: 实体类型缺失或错误")
    print("="*80)
    
    # 3.1 检查缺少类型标签的节点
    print("\n  3.1 检查缺少类型标签的节点...")
    result = session.run("""
        MATCH (n)
        WHERE n.entity_type IS NULL
        RETURN n.name as name, labels(n) as labels
        LIMIT 20
    """)
    
    no_type_nodes = list(result)
    if no_type_nodes:
        print(f"  发现 {len(no_type_nodes)} 个缺少类型的节点:")
        for node in no_type_nodes[:10]:
            print(f"    • {node['name']} (标签: {node['labels']})")
            issues.append(f"缺少类型: {node['name']}")
    
    # 3.2 检查类型标签与名称不匹配的节点
    print("\n  3.2 检查类型标签一致性...")
    
    # 已知的实体应该有正确的类型
    known_entities = {
        'bursaphelenchus xylophilus': 'Pathogen',
        'pine wilt disease': 'Disease',
        'monochamus alternatus': 'Vector',
        'pinus thunbergii': 'Host',
        '马尾松': 'Host',
        '湿地松': 'Host',
        'sentinel-2': 'Technology',
    }
    
    for entity, expected_type in known_entities.items():
        result = session.run("""
            MATCH (n {name: $name})
            RETURN n.entity_type as actual_type
        """, name=entity).single()
        
        if result:
            actual_type = result['actual_type']
            if actual_type != expected_type:
                issues.append(f"类型错误: {entity} 应该是 {expected_type}，实际是 {actual_type}")
                fixes.append(('fix_entity_type', entity, expected_type, None))
                print(f"  ⚠️  {entity}: {actual_type} -> {expected_type}")
    
    # ========================================================================
    # 分析4: 冗余和低质量关系
    # ========================================================================
    print("\n" + "="*80)
    print("分析4: 冗余和低质量关系")
    print("="*80)
    
    # 4.1 检查权重过低的关系
    print("\n  4.1 检查低权重关系...")
    result = session.run("""
        MATCH ()-[r]->()
        WHERE r.weight < 0.1
        RETURN count(r) as count
    """).single()
    
    low_weight_count = result['count']
    if low_weight_count > 0:
        print(f"  发现 {low_weight_count} 个权重<0.1的关系")
        issues.append(f"低权重关系: {low_weight_count} 个")
    
    # 4.2 检查过度使用co-occurs关系
    print("\n  4.2 检查关系类型分布...")
    result = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) as rel_type, count(*) as count
        ORDER BY count DESC
        LIMIT 10
    """)
    
    rel_distribution = list(result)
    total_rels = sum(r['count'] for r in rel_distribution)
    co_occurs_count = sum(r['count'] for r in rel_distribution if 'co_occurs' in r['rel_type'].lower())
    co_occurs_pct = co_occurs_count / total_rels * 100 if total_rels > 0 else 0
    
    print(f"\n  关系类型分布:")
    for rel in rel_distribution:
        pct = rel['count'] / total_rels * 100
        print(f"    {rel['rel_type']:30s}: {rel['count']:3d} ({pct:5.1f}%)")
    
    if co_occurs_pct > 70:
        issues.append(f"co-occurs关系占比过高: {co_occurs_pct:.1f}%")
        print(f"\n  ⚠️  co-occurs关系占比过高: {co_occurs_pct:.1f}%")
    
    # ========================================================================
    # 分析5: 孤立和弱连接节点
    # ========================================================================
    print("\n" + "="*80)
    print("分析5: 孤立和弱连接节点")
    print("="*80)
    
    # 5.1 孤立节点
    print("\n  5.1 检查孤立节点...")
    result = session.run("""
        MATCH (n)
        WHERE NOT (n)--()
        RETURN n.name as name, n.entity_type as type
    """)
    
    isolated_nodes = list(result)
    if isolated_nodes:
        print(f"  发现 {len(isolated_nodes)} 个孤立节点:")
        for node in isolated_nodes:
            print(f"    • {node['name']} ({node['type']})")
            issues.append(f"孤立节点: {node['name']}")
            fixes.append(('delete_isolated', node['name'], None, None))
    else:
        print("  ✅ 无孤立节点")
    
    # 5.2 低连接度节点
    print("\n  5.2 检查低连接度节点...")
    result = session.run("""
        MATCH (n)
        WITH n, COUNT {(n)--()} as degree
        WHERE degree <= 2
        RETURN n.name as name, n.entity_type as type, degree
        ORDER BY degree
        LIMIT 10
    """)
    
    low_degree_nodes = list(result)
    if low_degree_nodes:
        print(f"  发现 {len(low_degree_nodes)} 个低连接度节点:")
        for node in low_degree_nodes:
            print(f"    • {node['name']} ({node['type']}): {node['degree']} 个连接")

driver.close()

# ============================================================================
# 生成修复报告
# ============================================================================
print("\n" + "="*80)
print("语义分析总结")
print("="*80)

print(f"\n发现 {len(issues)} 个语义问题:")
for i, issue in enumerate(issues[:20], 1):
    print(f"  {i}. {issue}")

if len(issues) > 20:
    print(f"  ... 还有 {len(issues) - 20} 个问题")

print(f"\n需要执行 {len(fixes)} 个修复操作")

# 保存修复计划
import json
with open('output/semantic_fixes.json', 'w', encoding='utf-8') as f:
    json.dump({
        'issues': issues,
        'fixes': [{'type': f[0], 'source': f[1], 'target': f[2], 'weight': f[3]} for f in fixes]
    }, f, ensure_ascii=False, indent=2)

print("\n✓ 分析完成，修复计划已保存到 output/semantic_fixes.json")
print("\n📌 下一步: 运行 python3 apply_semantic_fixes.py 来应用修复")
