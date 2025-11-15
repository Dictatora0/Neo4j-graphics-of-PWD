#!/usr/bin/env python3
"""
最终完善脚本：解决剩余的实体同义词、关系标准化和生物学错误
"""
from neo4j import GraphDatabase
import re

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("知识图谱最终完善")
print("="*80)

# ============================================================================
# 扩展的同义词映射
# ============================================================================

ADDITIONAL_SYNONYMS = {
    # 美国白蛾
    "hyphantria cunea": "美国白蛾",
    
    # 其他可能的同义词
    "小灰长角天牛": "arhopalus rusticus",
}

# ============================================================================
# 标准化关系类型映射（减少到核心类型）
# ============================================================================

STANDARD_RELATIONS = {
    # 统一为标准英文关系类型
    "寄生于": "PARASITIZES",
    "引起": "CAUSES",
    "传播": "TRANSMITS",
    "携带": "CARRIES",
    "感染": "INFECTS",
    "影响": "AFFECTS",
    "取食": "FEEDS_ON",
    "分布于": "DISTRIBUTED_IN",
    "发生于": "OCCURS_IN",
    "监测": "MONITORS",
    "防治": "CONTROLS",
    "适应于": "ADAPTS_TO",
    "共现": "CO_OCCURS_WITH",
    "co-occurs in": "CO_OCCURS_WITH",
    "co_occurs_in": "CO_OCCURS_WITH",
}

# ============================================================================
# 需要修正的特定错误关系
# ============================================================================

SPECIFIC_FIXES = [
    # (源节点, 错误关系, 目标节点, 正确关系)
    ("monochamus alternatus", "寄生于", "pinus thunbergii", "FEEDS_ON"),
    ("pine wilt disease", "寄生于", "泰山风景区", "OCCURS_IN"),
    ("pine wilt disease", "寄生于", "小灰长角天牛", None),  # None表示删除
    ("美国白蛾", "传播", "云杉花墨天牛", None),  # 删除错误关联
    ("sentinel-2", "影响", "pine wilt disease", "MONITORS"),
]

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    
    # ========================================================================
    # 步骤1: 合并剩余同义词
    # ========================================================================
    print("\n" + "="*80)
    print("步骤1: 合并剩余同义词")
    print("="*80)
    
    for synonym, canonical in ADDITIONAL_SYNONYMS.items():
        # 检查是否存在
        syn_exists = session.run("MATCH (n {name: $name}) RETURN count(n) as count", 
                                name=synonym).single()['count'] > 0
        can_exists = session.run("MATCH (n {name: $name}) RETURN count(n) as count", 
                                name=canonical).single()['count'] > 0
        
        if syn_exists and can_exists:
            print(f"\n  合并: {synonym} -> {canonical}")
            
            # 获取所有出边信息
            out_rels = session.run("""
                MATCH (old {name: $synonym})-[r]->(target)
                WHERE target.name <> $canonical
                RETURN target.name as target, type(r) as rel_type, properties(r) as props
            """, synonym=synonym, canonical=canonical)
            
            # 重建出边
            for rel in out_rels:
                safe_type = re.sub(r'[^a-zA-Z0-9_]', '_', rel['rel_type'])
                session.run(f"""
                    MATCH (new {{name: $canonical}})
                    MATCH (target {{name: $target}})
                    MERGE (new)-[r:{safe_type}]->(target)
                    SET r = $props
                """, canonical=canonical, target=rel['target'], props=rel['props'])
            
            # 获取所有入边信息
            in_rels = session.run("""
                MATCH (source)-[r]->(old {name: $synonym})
                WHERE source.name <> $canonical
                RETURN source.name as source, type(r) as rel_type, properties(r) as props
            """, synonym=synonym, canonical=canonical)
            
            # 重建入边
            for rel in in_rels:
                safe_type = re.sub(r'[^a-zA-Z0-9_]', '_', rel['rel_type'])
                session.run(f"""
                    MATCH (source {{name: $source}})
                    MATCH (new {{name: $canonical}})
                    MERGE (source)-[r:{safe_type}]->(new)
                    SET r = $props
                """, source=rel['source'], canonical=canonical, props=rel['props'])
            
            # 删除旧节点
            session.run("MATCH (n {name: $synonym}) DETACH DELETE n", synonym=synonym)
            print(f"  ✓ 完成")
        elif syn_exists:
            print(f"  ⚠️  {synonym} 存在但 {canonical} 不存在，重命名")
            session.run("MATCH (n {name: $synonym}) SET n.name = $canonical", 
                       synonym=synonym, canonical=canonical)
    
    # ========================================================================
    # 步骤2: 修正特定的错误关系
    # ========================================================================
    print("\n" + "="*80)
    print("步骤2: 修正特定错误关系")
    print("="*80)
    
    for source, old_rel, target, new_rel in SPECIFIC_FIXES:
        # 查找关系
        result = session.run("""
            MATCH (s {name: $source})-[r]->(t {name: $target})
            WHERE type(r) = $old_rel OR r.type = $old_rel
            RETURN count(r) as count, r.weight as weight
        """, source=source, old_rel=old_rel, target=target).single()
        
        if result and result['count'] > 0:
            weight = result['weight']
            
            if new_rel is None:
                # 删除关系
                print(f"\n  删除: {source} --[{old_rel}]--> {target}")
                session.run("""
                    MATCH (s {name: $source})-[r]->(t {name: $target})
                    WHERE type(r) = $old_rel OR r.type = $old_rel
                    DELETE r
                """, source=source, old_rel=old_rel, target=target)
            else:
                # 修正关系
                print(f"\n  修正: {source} --[{old_rel}]--> {target}")
                print(f"    -> {source} --[{new_rel}]--> {target}")
                
                # 删除旧关系
                session.run("""
                    MATCH (s {name: $source})-[r]->(t {name: $target})
                    WHERE type(r) = $old_rel OR r.type = $old_rel
                    DELETE r
                """, source=source, old_rel=old_rel, target=target)
                
                # 创建新关系
                session.run(f"""
                    MATCH (s {{name: $source}})
                    MATCH (t {{name: $target}})
                    MERGE (s)-[r:{new_rel}]->(t)
                    SET r.weight = $weight, r.type = $rel_type
                """, source=source, target=target, weight=weight if weight else 0.5, rel_type=new_rel)
    
    # ========================================================================
    # 步骤3: 标准化所有关系类型
    # ========================================================================
    print("\n" + "="*80)
    print("步骤3: 标准化关系类型")
    print("="*80)
    
    print("\n  统计当前关系类型...")
    result = session.run("""
        MATCH ()-[r]->()
        RETURN DISTINCT type(r) as rel_type, count(*) as count
        ORDER BY count DESC
    """)
    
    current_rels = list(result)
    print(f"  当前有 {len(current_rels)} 种关系类型")
    
    # 显示前20种
    print("\n  前20种关系类型:")
    for i, rel in enumerate(current_rels[:20], 1):
        print(f"    {i:2d}. {rel['rel_type']:30s}: {rel['count']:3d}")
    
    print("\n  开始标准化...")
    standardized = 0
    
    for old_rel, new_rel in STANDARD_RELATIONS.items():
        # 查找使用旧关系类型的关系
        result = session.run("""
            MATCH (s)-[r]->(t)
            WHERE type(r) = $old_rel OR r.type = $old_rel
            RETURN count(r) as count
        """, old_rel=old_rel).single()
        
        if result and result['count'] > 0:
            count = result['count']
            print(f"  标准化: {old_rel} -> {new_rel} ({count} 个)")
            
            # 获取所有需要转换的关系
            result = session.run("""
                MATCH (s)-[r]->(t)
                WHERE type(r) = $old_rel OR r.type = $old_rel
                RETURN s.name as source, t.name as target, properties(r) as props
            """, old_rel=old_rel)
            
            relations_to_convert = list(result)
            
            # 删除旧关系并创建新关系
            for rel in relations_to_convert:
                source = rel['source']
                target = rel['target']
                props = rel['props']
                
                # 删除旧关系
                session.run("""
                    MATCH (s {name: $source})-[r]->(t {name: $target})
                    WHERE type(r) = $old_rel OR r.type = $old_rel
                    DELETE r
                """, source=source, target=target, old_rel=old_rel)
                
                # 创建新关系
                session.run(f"""
                    MATCH (s {{name: $source}})
                    MATCH (t {{name: $target}})
                    MERGE (s)-[r:{new_rel}]->(t)
                    SET r = $props
                    SET r.type = $new_rel
                """, source=source, target=target, props=props)
            
            standardized += count
    
    print(f"\n  ✓ 标准化了 {standardized} 个关系")
    
    # ========================================================================
    # 步骤4: 处理复合关系（包含管道符）
    # ========================================================================
    print("\n" + "="*80)
    print("步骤4: 拆分复合关系")
    print("="*80)
    
    # 查找所有包含管道符的关系
    result = session.run("""
        MATCH (s)-[r]->(t)
        WHERE r.type CONTAINS '|'
        RETURN s.name as source, r.type as rel_type, t.name as target, 
               r.weight as weight, type(r) as db_type
        LIMIT 50
    """)
    
    compound_rels = list(result)
    
    if compound_rels:
        print(f"  发现 {len(compound_rels)} 个复合关系")
        
        for rel in compound_rels:
            source = rel['source']
            target = rel['target']
            rel_type = rel['rel_type']
            weight = rel['weight']
            db_type = rel['db_type']
            
            # 拆分关系
            parts = [p.strip() for p in rel_type.split('|')]
            unique_parts = list(set(parts))  # 去重
            
            if len(unique_parts) > 1:
                print(f"\n  拆分: {source} --[{rel_type}]--> {target}")
                print(f"    -> {len(unique_parts)} 个独立关系")
                
                # 删除原关系
                session.run(f"""
                    MATCH (s {{name: $source}})-[r:{db_type}]->(t {{name: $target}})
                    WHERE r.type = $rel_type
                    DELETE r
                """, source=source, target=target, rel_type=rel_type)
                
                # 创建拆分后的关系
                for part in unique_parts:
                    # 标准化关系名
                    std_rel = STANDARD_RELATIONS.get(part, part)
                    safe_rel = re.sub(r'[^a-zA-Z0-9_]', '_', std_rel)
                    
                    session.run(f"""
                        MATCH (s {{name: $source}})
                        MATCH (t {{name: $target}})
                        MERGE (s)-[r:{safe_rel}]->(t)
                        SET r.weight = $weight, r.type = $std_rel
                    """, source=source, target=target, weight=weight if weight else 0.5)
    else:
        print("  ✅ 无复合关系需要拆分")
    
    # ========================================================================
    # 步骤5: 权重规范化
    # ========================================================================
    print("\n" + "="*80)
    print("步骤5: 权重规范化")
    print("="*80)
    
    # 统计权重分布
    result = session.run("""
        MATCH ()-[r]->()
        RETURN r.weight as weight, count(*) as count
        ORDER BY count DESC
        LIMIT 10
    """)
    
    print("\n  当前权重分布（前10）:")
    for record in result:
        weight = record['weight']
        count = record['count']
        print(f"    {weight:6.3f}: {count:3d} 个关系")
    
    # 移除过低权重的关系（<0.1）
    result = session.run("""
        MATCH ()-[r]->()
        WHERE r.weight < 0.1
        DELETE r
        RETURN count(*) as deleted
    """).single()
    
    if result and result['deleted'] > 0:
        print(f"\n  ✓ 删除了 {result['deleted']} 个低权重关系（<0.1）")
    
    # ========================================================================
    # 步骤6: 删除美国白蛾的所有错误关联
    # ========================================================================
    print("\n" + "="*80)
    print("步骤6: 清理美国白蛾错误关联")
    print("="*80)
    
    # 美国白蛾与PWD无关，删除所有相关关系
    result = session.run("""
        MATCH (n {name: '美国白蛾'})-[r]-()
        DELETE r
        RETURN count(*) as deleted
    """).single()
    
    if result and result['deleted'] > 0:
        print(f"  ✓ 删除了 {result['deleted']} 个美国白蛾的关系")
    
    # 删除美国白蛾节点（如果成为孤立节点）
    result = session.run("""
        MATCH (n {name: '美国白蛾'})
        WHERE NOT (n)--()
        DELETE n
        RETURN count(*) as deleted
    """).single()
    
    if result and result['deleted'] > 0:
        print(f"  ✓ 删除了美国白蛾孤立节点")
    
    # ========================================================================
    # 最终验证
    # ========================================================================
    print("\n" + "="*80)
    print("最终验证")
    print("="*80)
    
    # 统计
    node_count = session.run("MATCH (n) RETURN count(n) as count").single()['count']
    rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']
    
    print(f"\n  节点总数: {node_count}")
    print(f"  关系总数: {rel_count}")
    
    # 关系类型统计
    result = session.run("""
        MATCH ()-[r]->()
        RETURN DISTINCT type(r) as rel_type, count(*) as count
        ORDER BY count DESC
        LIMIT 15
    """)
    
    print(f"\n  标准化后的关系类型（前15）:")
    for record in result:
        print(f"    {record['rel_type']:25s}: {record['count']:3d}")
    
    # 检查数据质量
    print(f"\n  数据质量检查:")
    
    # 孤立节点
    result = session.run("""
        MATCH (n)
        WHERE NOT (n)--()
        RETURN count(n) as count
    """).single()['count']
    print(f"    孤立节点: {result} {'✅' if result == 0 else '⚠️'}")
    
    # 复合关系
    result = session.run("""
        MATCH ()-[r]->()
        WHERE r.type CONTAINS '|'
        RETURN count(r) as count
    """).single()['count']
    print(f"    复合关系: {result} {'✅' if result == 0 else '⚠️'}")
    
    # 低权重关系
    result = session.run("""
        MATCH ()-[r]->()
        WHERE r.weight < 0.1
        RETURN count(r) as count
    """).single()['count']
    print(f"    低权重关系: {result} {'✅' if result == 0 else '⚠️'}")

driver.close()

print("\n" + "="*80)
print("✓ 最终完善完成！")
print("="*80)

print("\n📊 改进总结:")
print("  ✅ 合并剩余同义词")
print("  ✅ 修正特定生物学错误")
print("  ✅ 标准化关系类型到核心集合")
print("  ✅ 拆分复合关系")
print("  ✅ 规范化权重值")
print("  ✅ 清理无关实体")

print("\n📌 下一步:")
print("  1. 导出最终版本: python3 export_triples.py")
print("  2. 在Neo4j Browser验证: http://localhost:7474")
print("  3. 生成完整报告")
