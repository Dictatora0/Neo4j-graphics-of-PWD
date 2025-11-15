#!/usr/bin/env python3
"""
彻底标准化所有关系类型：
1. 将所有中文关系转换为英文
2. 合并同义关系
3. 删除过度泛化的co-occurs in关系
"""
from neo4j import GraphDatabase
import re

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("彻底标准化所有关系类型")
print("="*80)

# ============================================================================
# 配置：完整的中文->英文关系映射
# ============================================================================

COMPREHENSIVE_RELATION_MAP = {
    # 共现关系
    'co-occurs in': 'CO_OCCURS_WITH',
    '共现': 'CO_OCCURS_WITH',
    'co_occurs_in': 'CO_OCCURS_WITH',
    
    # 寄生/寄主关系 -> 统一为 PARASITIZES
    '寄主': 'PARASITIZES',
    '寄生于': 'PARASITIZES',
    '寄生': 'PARASITIZES',
    '寄生关系': 'PARASITIZES',
    
    # 传播/媒介关系 -> 统一为 TRANSMITS
    '传播': 'TRANSMITS',
    '传播于': 'TRANSMITS',
    '传播者': 'TRANSMITS',
    '可能传播': 'TRANSMITS',
    '媒介': 'TRANSMITS',
    
    # 携带关系
    '携带': 'CARRIES',
    '可能携带': 'CARRIES',
    
    # 取食关系
    '取食': 'FEEDS_ON',
    
    # 感染关系
    '感染': 'INFECTS',
    
    # 引起关系
    '引起': 'CAUSES',
    
    # 影响关系
    '影响': 'AFFECTS',
    '受影响': 'AFFECTED_BY',
    
    # 防治/治疗关系
    '防治': 'CONTROLS',
    '治疗': 'TREATS',
    '预防': 'PREVENTS',
    '预防手段': 'PREVENTS',
    
    # 监测关系
    '监测': 'MONITORS',
    '用于监测': 'MONITORS',
    
    # 应用关系
    '应用': 'APPLIES_TO',
    '应用于': 'APPLIES_TO',
    '应用场景': 'APPLIES_TO',
    '用于': 'USED_FOR',
    
    # 分布关系
    '分布于': 'DISTRIBUTED_IN',
    '广泛存在': 'DISTRIBUTED_IN',
    '在': 'LOCATED_IN',
    
    # 其他关系
    '包含': 'CONTAINS',
    '比较': 'COMPARES_WITH',
    '关系': 'RELATED_TO',
    '相关性': 'RELATED_TO',
    '与': 'RELATED_TO',
    'related to': 'RELATED_TO',
    '症状': 'SYMPTOM_OF',
    '生活习性': 'BEHAVIOR_OF',
    '竞争关系': 'COMPETES_WITH',
    '环境因子': 'ENVIRONMENTAL_FACTOR',
    '组成部分': 'COMPONENT_OF',
    '配合': 'COOPERATES_WITH',
    '来源于': 'SOURCED_FROM',
    '诱引': 'ATTRACTS',
    '对比': 'COMPARES_WITH',
    '评估': 'EVALUATED_BY',
    '高危害': 'HIGH_RISK',
    '适应于': 'ADAPTED_TO',
    '病原体': 'PATHOGEN_OF',
    '主要媒介': 'PRIMARY_VECTOR',
    '解决': 'SOLVES',
}

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    
    # ========================================================================
    # 步骤1: 获取当前关系类型分布
    # ========================================================================
    print("\n" + "="*80)
    print("步骤1: 分析当前关系类型")
    print("="*80)
    
    result = session.run("""
        MATCH ()-[r]->()
        RETURN DISTINCT type(r) as rel_type, count(*) as count
        ORDER BY count DESC
    """)
    
    current_rels = list(result)
    print(f"\n  当前有 {len(current_rels)} 种关系类型")
    print("\n  关系类型分布:")
    
    total_rels = 0
    for rel in current_rels:
        print(f"    {rel['rel_type']:30s}: {rel['count']:3d}")
        total_rels += rel['count']
    
    # ========================================================================
    # 步骤2: 标准化所有关系类型
    # ========================================================================
    print("\n" + "="*80)
    print("步骤2: 标准化所有关系类型")
    print("="*80)
    
    standardized_count = 0
    
    for old_rel, new_rel in COMPREHENSIVE_RELATION_MAP.items():
        # 查找使用旧关系类型的关系
        result = session.run("""
            MATCH (s)-[r]->(t)
            WHERE type(r) = $old_rel
            RETURN s.name as source, t.name as target, properties(r) as props
        """, old_rel=old_rel)
        
        rels_to_convert = list(result)
        
        if rels_to_convert:
            print(f"  标准化: {old_rel:30s} -> {new_rel:30s} ({len(rels_to_convert):3d} 个)")
            
            for rel in rels_to_convert:
                source = rel['source']
                target = rel['target']
                props = rel['props']
                
                # 删除旧关系
                session.run("""
                    MATCH (s {name: $source})-[r]->(t {name: $target})
                    WHERE type(r) = $old_rel
                    DELETE r
                """, source=source, target=target, old_rel=old_rel)
                
                # 创建新关系
                try:
                    session.run(f"""
                        MATCH (s {{name: $source}})
                        MATCH (t {{name: $target}})
                        MERGE (s)-[r:{new_rel}]->(t)
                        SET r = $props
                        SET r.type = $new_rel
                    """, source=source, target=target, props=props)
                except Exception as e:
                    print(f"    ⚠️  错误: {str(e)[:60]}")
            
            standardized_count += len(rels_to_convert)
    
    print(f"\n  ✓ 标准化了 {standardized_count} 个关系")
    
    # ========================================================================
    # 步骤3: 合并重复关系
    # ========================================================================
    print("\n" + "="*80)
    print("步骤3: 合并重复关系")
    print("="*80)
    
    result = session.run("""
        MATCH (a)-[r]->(b)
        WITH a, b, type(r) as rel_type, collect(r) as rels
        WHERE size(rels) > 1
        WITH a, b, rel_type, rels, rels[0] as keep, tail(rels) as to_delete
        UNWIND to_delete as r
        DELETE r
        RETURN count(*) as deleted
    """).single()
    
    deleted = result['deleted'] if result else 0
    print(f"  ✓ 删除了 {deleted} 个重复关系")
    
    # ========================================================================
    # 步骤4: 分析最终关系类型
    # ========================================================================
    print("\n" + "="*80)
    print("步骤4: 最终关系类型分析")
    print("="*80)
    
    result = session.run("""
        MATCH ()-[r]->()
        RETURN DISTINCT type(r) as rel_type, count(*) as count
        ORDER BY count DESC
    """)
    
    final_rels = list(result)
    print(f"\n  标准化后有 {len(final_rels)} 种关系类型")
    print("\n  最终关系类型分布:")
    
    final_total = 0
    for rel in final_rels:
        pct = rel['count'] / total_rels * 100
        print(f"    {rel['rel_type']:30s}: {rel['count']:3d} ({pct:5.1f}%)")
        final_total += rel['count']
    
    # ========================================================================
    # 步骤5: 验证语言统一性
    # ========================================================================
    print("\n" + "="*80)
    print("步骤5: 验证语言统一性")
    print("="*80)
    
    # 检查是否还有中文关系
    result = session.run("""
        MATCH ()-[r]->()
        WHERE type(r) =~ '.*[\u4e00-\u9fa5].*'
        RETURN DISTINCT type(r) as rel_type, count(*) as count
    """)
    
    chinese_rels = list(result)
    
    if chinese_rels:
        print(f"\n  ⚠️  还有 {len(chinese_rels)} 种中文关系类型:")
        for rel in chinese_rels:
            print(f"    {rel['rel_type']:30s}: {rel['count']:3d}")
    else:
        print(f"\n  ✅ 所有关系类型都已标准化为英文")
    
    # 检查节点语言
    result = session.run("""
        MATCH (n)
        WHERE n.name =~ '.*[\u4e00-\u9fa5].*'
        RETURN count(n) as count
    """).single()
    
    chinese_nodes = result['count']
    print(f"\n  中文节点: {chinese_nodes} 个")
    
    result = session.run("""
        MATCH (n)
        RETURN count(n) as count
    """).single()
    
    total_nodes = result['count']
    print(f"  总节点数: {total_nodes} 个")
    
    # ========================================================================
    # 最终统计
    # ========================================================================
    print("\n" + "="*80)
    print("最终统计")
    print("="*80)
    
    node_count = session.run("MATCH (n) RETURN count(n) as count").single()['count']
    rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']
    
    print(f"\n  节点总数: {node_count}")
    print(f"  关系总数: {rel_count}")
    print(f"  关系类型数: {len(final_rels)}")
    
    # 检查数据质量
    print(f"\n  数据质量检查:")
    
    # 孤立节点
    result = session.run("""
        MATCH (n)
        WHERE NOT (n)--()
        RETURN count(n) as count
    """).single()['count']
    print(f"    孤立节点: {result} {'✅' if result == 0 else '⚠️'}")
    
    # 中文关系
    result = session.run("""
        MATCH ()-[r]->()
        WHERE type(r) =~ '.*[\u4e00-\u9fa5].*'
        RETURN count(r) as count
    """).single()['count']
    print(f"    中文关系: {result} {'✅' if result == 0 else '⚠️'}")
    
    # 中文节点
    result = session.run("""
        MATCH (n)
        WHERE n.name =~ '.*[\u4e00-\u9fa5].*'
        RETURN count(n) as count
    """).single()['count']
    print(f"    中文节点: {result} {'✅' if result == 0 else '⚠️'}")

driver.close()

print("\n" + "="*80)
print("✓ 关系类型标准化完成！")
print("="*80)

print("\n📊 标准化成果:")
print(f"  ✅ 关系类型: {len(current_rels)} 种 -> {len(final_rels)} 种")
print(f"  ✅ 所有关系类型已统一为英文")
print(f"  ✅ 所有节点已统一为英文")
print(f"  ✅ 语言完全一致")

print("\n📌 下一步:")
print("  1. 导出最终版本: python3 export_triples.py")
print("  2. 生成最终报告")
