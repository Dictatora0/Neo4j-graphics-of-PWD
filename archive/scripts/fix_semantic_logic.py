#!/usr/bin/env python3
"""
修复语义逻辑问题：
1. 清理TRANSMITS关系中的逻辑错误
2. 清理PARASITIZES关系中的逻辑错误
3. 分析CO_OCCURS_WITH关系的质量
"""
from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("修复语义逻辑问题")
print("="*80)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    
    # ========================================================================
    # 问题1: 清理TRANSMITS关系中的逻辑错误
    # ========================================================================
    print("\n" + "="*80)
    print("问题1: 清理TRANSMITS关系中的逻辑错误")
    print("="*80)
    
    print("\n【标准】TRANSMITS应该是: (Vector) --[TRANSMITS]--> (Pathogen)")
    
    # 查找所有TRANSMITS关系
    result = session.run("""
        MATCH (s)-[r:TRANSMITS]->(t)
        RETURN s.name as source, s.type as source_type,
               t.name as target, t.type as target_type,
               r.weight as weight
    """).data()
    
    print(f"\n【当前TRANSMITS关系】({len(result)} 条)")
    
    invalid_count = 0
    for rel in result:
        source_type = rel['source_type']
        target_type = rel['target_type']
        
        # 检查是否符合标准
        is_valid = source_type == 'Vector' and target_type == 'Pathogen'
        
        if is_valid:
            print(f"  ✅ {rel['source']:30s} ({source_type:10s}) -> {rel['target']:30s} ({target_type:10s})")
        else:
            print(f"  ❌ {rel['source']:30s} ({source_type:10s}) -> {rel['target']:30s} ({target_type:10s})")
            
            # 删除错误关系
            session.run("""
                MATCH (s {name: $source})-[r:TRANSMITS]->(t {name: $target})
                DELETE r
            """, source=rel['source'], target=rel['target'])
            
            invalid_count += 1
    
    print(f"\n  ✓ 删除了 {invalid_count} 个不符合标准的TRANSMITS关系")
    
    # ========================================================================
    # 问题2: 清理PARASITIZES关系中的逻辑错误
    # ========================================================================
    print("\n" + "="*80)
    print("问题2: 清理PARASITIZES关系中的逻辑错误")
    print("="*80)
    
    print("\n【标准】PARASITIZES应该是: (Pathogen) --[PARASITIZES]--> (Host)")
    
    # 查找所有PARASITIZES关系
    result = session.run("""
        MATCH (s)-[r:PARASITIZES]->(t)
        RETURN s.name as source, s.type as source_type,
               t.name as target, t.type as target_type,
               r.weight as weight
    """).data()
    
    print(f"\n【当前PARASITIZES关系】({len(result)} 条)")
    
    invalid_count = 0
    for rel in result:
        source_type = rel['source_type']
        target_type = rel['target_type']
        
        # 检查是否符合标准
        is_valid = source_type == 'Pathogen' and target_type == 'Host'
        
        if is_valid:
            print(f"  ✅ {rel['source']:30s} ({source_type:10s}) -> {rel['target']:30s} ({target_type:10s})")
        else:
            print(f"  ❌ {rel['source']:30s} ({source_type:10s}) -> {rel['target']:30s} ({target_type:10s})")
            
            # 删除错误关系
            session.run("""
                MATCH (s {name: $source})-[r:PARASITIZES]->(t {name: $target})
                DELETE r
            """, source=rel['source'], target=rel['target'])
            
            invalid_count += 1
    
    print(f"\n  ✓ 删除了 {invalid_count} 个不符合标准的PARASITIZES关系")
    
    # ========================================================================
    # 问题3: 分析CO_OCCURS_WITH关系的质量
    # ========================================================================
    print("\n" + "="*80)
    print("问题3: 分析CO_OCCURS_WITH关系的质量")
    print("="*80)
    
    print("\n【分析】CO_OCCURS_WITH关系可能隐含了其他更具体的关系")
    
    # 查找可能应该是PARASITIZES的CO_OCCURS_WITH
    result = session.run("""
        MATCH (p:Pathogen)-[r:CO_OCCURS_WITH]->(h:Host)
        RETURN p.name as pathogen, h.name as host, r.weight as weight
        LIMIT 10
    """).data()
    
    print(f"\n【病原体-寄主的CO_OCCURS_WITH】({len(result)} 条)")
    print("  这些可能应该是PARASITIZES关系:")
    
    for rel in result[:5]:
        print(f"    {rel['pathogen']:30s} <--> {rel['host']:30s}")
    
    # 查找可能应该是DISTRIBUTED_IN的CO_OCCURS_WITH
    result = session.run("""
        MATCH (d:Disease)-[r:CO_OCCURS_WITH]->(l:Location)
        RETURN d.name as disease, l.name as location, r.weight as weight
        LIMIT 10
    """).data()
    
    print(f"\n【疾病-地点的CO_OCCURS_WITH】({len(result)} 条)")
    print("  这些可能应该是DISTRIBUTED_IN关系:")
    
    for rel in result[:5]:
        print(f"    {rel['disease']:30s} <--> {rel['location']:30s}")
    
    # ========================================================================
    # 最终验证
    # ========================================================================
    print("\n" + "="*80)
    print("最终验证")
    print("="*80)
    
    # 统计
    result = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()
    print(f"\n  关系总数: {result['count']}")
    
    # TRANSMITS关系验证
    result = session.run("""
        MATCH (s:Vector)-[r:TRANSMITS]->(t:Pathogen)
        RETURN count(*) as valid_count
    """).single()
    
    result2 = session.run("""
        MATCH (s)-[r:TRANSMITS]->(t)
        WHERE NOT (s:Vector AND t:Pathogen)
        RETURN count(*) as invalid_count
    """).single()
    
    print(f"\n  TRANSMITS关系:")
    print(f"    ✅ 正确 (Vector->Pathogen): {result['valid_count']}")
    print(f"    ❌ 错误: {result2['invalid_count']}")
    
    # PARASITIZES关系验证
    result = session.run("""
        MATCH (s:Pathogen)-[r:PARASITIZES]->(t:Host)
        RETURN count(*) as valid_count
    """).single()
    
    result2 = session.run("""
        MATCH (s)-[r:PARASITIZES]->(t)
        WHERE NOT (s:Pathogen AND t:Host)
        RETURN count(*) as invalid_count
    """).single()
    
    print(f"\n  PARASITIZES关系:")
    print(f"    ✅ 正确 (Pathogen->Host): {result['valid_count']}")
    print(f"    ❌ 错误: {result2['invalid_count']}")
    
    # 关系类型分布
    result = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) as rel_type, count(*) as count
        ORDER BY count DESC
        LIMIT 10
    """).data()
    
    print(f"\n  关系类型分布（前10）:")
    total = sum(r['count'] for r in result)
    for rel in result:
        pct = rel['count'] / total * 100
        print(f"    {rel['rel_type']:25s}: {rel['count']:3d} ({pct:5.1f}%)")

driver.close()

print("\n" + "="*80)
print("✓ 语义逻辑修复完成！")
print("="*80)

print("\n📊 修复总结:")
print("  ✅ 清理了TRANSMITS关系中的逻辑错误")
print("  ✅ 清理了PARASITIZES关系中的逻辑错误")
print("  ✅ 分析了CO_OCCURS_WITH关系的质量")

print("\n📌 后续建议:")
print("  1. 考虑将病原体-寄主的CO_OCCURS_WITH转换为PARASITIZES")
print("  2. 考虑将疾病-地点的CO_OCCURS_WITH转换为DISTRIBUTED_IN")
print("  3. 从数据源重新提取，改进关系提取规则")
print("  4. 建立明确的关系定义和验证规则")
