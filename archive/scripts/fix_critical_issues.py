#!/usr/bin/env python3
"""
修复关键问题：
1. 修正传播关系的方向
2. 修正寄生关系的逻辑
3. 修正引起关系的事实错误
4. 完善节点分类
5. 消除关系冗余
"""
from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("修复关键问题")
print("="*80)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    
    # ========================================================================
    # 问题1: 修正传播关系的方向
    # ========================================================================
    print("\n" + "="*80)
    print("问题1: 修正传播关系的方向")
    print("="*80)
    
    print("\n【分析】")
    print("  传播关系应该是: 媒介 -> 病原体 或 媒介 -> 寄主")
    print("  错误的关系: 病原体 -> 媒介 或 病原体 -> 寄主")
    
    # 查找所有传播关系
    result = session.run("""
        MATCH (s)-[r:TRANSMITS]->(t)
        RETURN s.name as source, s.type as source_type,
               t.name as target, t.type as target_type,
               r.weight as weight
    """).data()
    
    print(f"\n【当前传播关系】({len(result)} 条)")
    
    reversed_count = 0
    for rel in result:
        source_type = rel['source_type']
        target_type = rel['target_type']
        
        # 检查是否需要反转
        should_reverse = False
        if source_type == 'Pathogen' and target_type == 'Vector':
            should_reverse = True
            print(f"  ❌ 需要反转: {rel['source']} ({source_type}) -> {rel['target']} ({target_type})")
        elif source_type == 'Disease' and target_type in ['Vector', 'Host', 'Pathogen']:
            should_reverse = True
            print(f"  ❌ 需要反转: {rel['source']} ({source_type}) -> {rel['target']} ({target_type})")
        else:
            print(f"  ✅ 正确: {rel['source']} ({source_type}) -> {rel['target']} ({target_type})")
        
        if should_reverse:
            # 删除旧关系
            session.run("""
                MATCH (s {name: $source})-[r:TRANSMITS]->(t {name: $target})
                DELETE r
            """, source=rel['source'], target=rel['target'])
            
            # 创建反向关系
            session.run("""
                MATCH (s {name: $target})
                MATCH (t {name: $source})
                MERGE (s)-[r:TRANSMITS]->(t)
                SET r.weight = $weight
            """, source=rel['source'], target=rel['target'], weight=rel['weight'])
            
            reversed_count += 1
    
    print(f"\n  ✓ 反转了 {reversed_count} 个传播关系")
    
    # ========================================================================
    # 问题2: 修正寄生关系中的植物-植物关系
    # ========================================================================
    print("\n" + "="*80)
    print("问题2: 修正寄生关系中的植物-植物关系")
    print("="*80)
    
    print("\n【分析】")
    print("  植物不应该寄生于植物")
    print("  应该是: 病原体 -> 寄生 -> 寄主")
    
    # 查找植物-植物的寄生关系
    result = session.run("""
        MATCH (s:Host)-[r:PARASITIZES]->(t:Host)
        RETURN s.name as source, t.name as target, r.weight as weight
    """).data()
    
    print(f"\n【植物-植物寄生关系】({len(result)} 条)")
    
    deleted_count = 0
    for rel in result:
        print(f"  ❌ 删除: {rel['source']} --[寄生]--> {rel['target']}")
        
        # 删除这个关系
        session.run("""
            MATCH (s {name: $source})-[r:PARASITIZES]->(t {name: $target})
            DELETE r
        """, source=rel['source'], target=rel['target'])
        
        deleted_count += 1
    
    print(f"\n  ✓ 删除了 {deleted_count} 个不合理的植物-植物寄生关系")
    
    # ========================================================================
    # 问题3: 修正引起关系中的事实错误
    # ========================================================================
    print("\n" + "="*80)
    print("问题3: 修正引起关系中的事实错误")
    print("="*80)
    
    print("\n【分析】")
    print("  细菌不引起线虫，应该是共生或伴生关系")
    print("  正确的关系: 病原体 -> 引起 -> 疾病")
    
    # 查找细菌-线虫的引起关系
    result = session.run("""
        MATCH (s)-[r:CAUSES]->(t)
        WHERE s.name CONTAINS 'bacteria' AND t.name CONTAINS 'nematode'
        RETURN s.name as source, t.name as target, r.weight as weight
    """).data()
    
    print(f"\n【细菌-线虫引起关系】({len(result)} 条)")
    
    fixed_count = 0
    for rel in result:
        print(f"  ❌ 错误: {rel['source']} --[引起]--> {rel['target']}")
        print(f"     应改为: 共生或伴生关系")
        
        # 删除错误关系
        session.run("""
            MATCH (s {name: $source})-[r:CAUSES]->(t {name: $target})
            DELETE r
        """, source=rel['source'], target=rel['target'])
        
        # 创建正确的关系（使用CO_OCCURS_WITH表示伴生）
        session.run("""
            MATCH (s {name: $source})
            MATCH (t {name: $target})
            MERGE (s)-[r:CO_OCCURS_WITH]->(t)
            SET r.weight = $weight
        """, source=rel['source'], target=rel['target'], weight=rel['weight'])
        
        fixed_count += 1
    
    print(f"\n  ✓ 修正了 {fixed_count} 个事实错误")
    
    # ========================================================================
    # 问题4: 完善节点分类
    # ========================================================================
    print("\n" + "="*80)
    print("问题4: 完善节点分类")
    print("="*80)
    
    print("\n【分析】")
    print("  将高度数的Other节点重新分类")
    
    # 重新分类leaf相关节点
    reclassifications = {
        'leaf': 'Host_Part',
        'leaf hyperspectral data': 'Technology',
        'red band': 'Technology',
        'first derivative spectrum': 'Technology',
        'hyperspectral imaging': 'Technology',
        'band selection algorithm': 'Technology',
    }
    
    print(f"\n【重新分类】")
    
    for node_name, new_type in reclassifications.items():
        result = session.run("""
            MATCH (n {name: $name})
            SET n.type = $new_type
            RETURN n.name as name, n.type as type
        """, name=node_name, new_type=new_type).single()
        
        if result:
            print(f"  ✓ {node_name:40s}: Other -> {new_type}")
    
    # ========================================================================
    # 问题5: 消除关系冗余
    # ========================================================================
    print("\n" + "="*80)
    print("问题5: 消除关系冗余")
    print("="*80)
    
    print("\n【分析】")
    print("  删除AFFECTED_BY关系，保留AFFECTS")
    print("  删除反向的CO_OCCURS_WITH关系")
    
    # 删除AFFECTED_BY关系
    result = session.run("""
        MATCH (s)-[r:AFFECTED_BY]->(t)
        DELETE r
        RETURN count(*) as deleted
    """).single()
    
    print(f"\n  ✓ 删除了 {result['deleted']} 个AFFECTED_BY关系")
    
    # 删除对称的CO_OCCURS_WITH关系（保留一个方向）
    result = session.run("""
        MATCH (a)-[r1:CO_OCCURS_WITH]->(b), (b)-[r2:CO_OCCURS_WITH]->(a)
        WHERE id(a) < id(b)
        DELETE r2
        RETURN count(*) as deleted
    """).single()
    
    print(f"  ✓ 删除了 {result['deleted']} 个对称的CO_OCCURS_WITH关系")
    
    # ========================================================================
    # 最终验证
    # ========================================================================
    print("\n" + "="*80)
    print("最终验证")
    print("="*80)
    
    # 统计
    result = session.run("MATCH (n) RETURN count(n) as count").single()
    print(f"\n  节点数: {result['count']}")
    
    result = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()
    print(f"  关系数: {result['count']}")
    
    # 关系类型分布
    result = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) as rel_type, count(*) as count
        ORDER BY count DESC
        LIMIT 10
    """).data()
    
    print(f"\n  关系类型分布（前10）:")
    for rel in result:
        print(f"    {rel['rel_type']:25s}: {rel['count']:3d}")
    
    # 检查传播关系
    result = session.run("""
        MATCH (s:Vector)-[r:TRANSMITS]->(t)
        RETURN count(*) as count
    """).single()
    
    print(f"\n  ✅ 正确方向的传播关系: {result['count']}")
    
    # 检查植物-植物寄生
    result = session.run("""
        MATCH (s:Host)-[r:PARASITIZES]->(t:Host)
        RETURN count(*) as count
    """).single()
    
    print(f"  ✅ 植物-植物寄生关系: {result['count']} {'✅' if result['count'] == 0 else '❌'}")
    
    # 检查节点分类
    result = session.run("""
        MATCH (n)
        WHERE n.type = 'Other'
        RETURN count(*) as count
    """).single()
    
    print(f"  ✅ Other类型节点: {result['count']}")

driver.close()

print("\n" + "="*80)
print("✓ 关键问题修复完成！")
print("="*80)

print("\n📊 修复总结:")
print("  ✅ 修正了传播关系的方向")
print("  ✅ 删除了不合理的植物-植物寄生关系")
print("  ✅ 修正了事实错误的引起关系")
print("  ✅ 完善了节点分类")
print("  ✅ 消除了关系冗余")

print("\n📌 后续建议:")
print("  1. 重新导出三元组进行审查")
print("  2. 在Neo4j Browser中验证修复")
print("  3. 考虑降低CO_OCCURS_WITH关系的权重")
print("  4. 从数据源中提炼更多有意义的关系")
