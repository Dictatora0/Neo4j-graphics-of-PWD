#!/usr/bin/env python3
"""
全面修复知识图谱中的逻辑错误、实体冗余、关系混乱和噪音数据
"""
from neo4j import GraphDatabase
import re

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("知识图谱全面修复")
print("="*80)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# ============================================================================
# 定义同义词词典和乱码模式
# ============================================================================

# 同义词映射 (统一使用拉丁名/英文名作为标准名称)
ENTITY_SYNONYMS = {
    "pine wood nematode": "bursaphelenchus xylophilus",
    "松材线虫": "bursaphelenchus xylophilus",
    "m．alternatus": "monochamus alternatus",  # 全角句点
    "松墨天牛": "monochamus alternatus",
    "sentinal-2": "sentinel-2",  # 拼写错误
    "sentinel-2 卫星遥感影像": "sentinel-2",
}

# 乱码模式 (需要删除的节点)
GARBAGE_PATTERNS = [
    "兴丿程量",
    "张法的程叀",
    "痢夬海程量",
    "欛超生輖生统帉送一个都断前",
    "王叫-带-统帉送一个都断前",
    "马父-2生輖生统帉送友公四都断前",
    "郹貉带-子金去結的是四都断前",
]

# 关系规范化映射
RELATION_NORMALIZATION = {
    "co-occurs in": "共现",
    "co_occurs_in": "共现",
    "causes": "引起",
    "parasitizes": "寄生于",
    "transmits": "传播",
    "infects": "感染",
}

with driver.session() as session:
    
    # ========================================================================
    # 步骤1: 删除乱码节点
    # ========================================================================
    print("\n🗑️  步骤1: 删除乱码节点")
    print("-"*80)
    
    total_deleted = 0
    for pattern in GARBAGE_PATTERNS:
        result = session.run("""
            MATCH (n)
            WHERE n.name CONTAINS $pattern
            DETACH DELETE n
            RETURN count(*) as deleted
        """, pattern=pattern)
        
        deleted = result.single()['deleted']
        if deleted > 0:
            print(f"   ✓ 删除包含 '{pattern}' 的节点: {deleted} 个")
            total_deleted += deleted
    
    print(f"   总计删除: {total_deleted} 个乱码节点")
    
    # ========================================================================
    # 步骤2: 修正严重的逻辑错误 (因果倒置)
    # ========================================================================
    print("\n🔧 步骤2: 修正因果倒置的逻辑错误")
    print("-"*80)
    
    # 2.1 修正 "疾病 -> 病原体" 的错误关系
    print("\n   2.1 修正 '疾病 寄生于/引起 病原体' 的错误...")
    
    # 查找所有错误的关系
    result = session.run("""
        MATCH (disease:疾病)-[r]->(pathogen:病原体)
        WHERE type(r) IN ['寄生于', '引起', '感染']
        RETURN disease.name as disease, type(r) as rel_type, pathogen.name as pathogen, 
               r.weight as weight, id(r) as rel_id
    """)
    
    wrong_relations = list(result)
    
    if wrong_relations:
        print(f"   发现 {len(wrong_relations)} 个错误的关系:")
        
        for rel in wrong_relations:
            disease = rel['disease']
            pathogen = rel['pathogen']
            rel_type = rel['rel_type']
            weight = rel['weight']
            
            print(f"     ❌ {disease} --[{rel_type}]--> {pathogen}")
            
            # 删除错误的关系
            session.run("""
                MATCH (disease:疾病 {name: $disease})-[r]->(pathogen:病原体 {name: $pathogen})
                WHERE type(r) = $rel_type
                DELETE r
            """, disease=disease, pathogen=pathogen, rel_type=rel_type)
            
            # 创建正确的关系: 病原体 -> 疾病
            session.run("""
                MATCH (pathogen:病原体 {name: $pathogen})
                MATCH (disease:疾病 {name: $disease})
                MERGE (pathogen)-[r:引起]->(disease)
                SET r.weight = $weight, r.type = '引起'
            """, pathogen=pathogen, disease=disease, weight=weight if weight else 0.8)
            
            print(f"     ✓ 修正为: {pathogen} --[引起]--> {disease}")
    else:
        print("   ✅ 未发现因果倒置的关系")
    
    # 2.2 修正其他可能的逻辑错误
    print("\n   2.2 检查其他逻辑错误...")
    
    # 疾病不应该"传播"任何东西 (应该是媒介传播疾病)
    result = session.run("""
        MATCH (disease:疾病)-[r:传播]->(n)
        RETURN disease.name as disease, n.name as target, id(r) as rel_id
    """)
    
    disease_transmit = list(result)
    if disease_transmit:
        print(f"   发现 {len(disease_transmit)} 个'疾病传播X'的错误:")
        for rel in disease_transmit:
            print(f"     ❌ {rel['disease']} --[传播]--> {rel['target']}")
            session.run("""
                MATCH (disease:疾病 {name: $disease})-[r:传播]->(n {name: $target})
                DELETE r
            """, disease=rel['disease'], target=rel['target'])
            print(f"     ✓ 已删除")
    
    # ========================================================================
    # 步骤3: 实体规范化 (合并同义词)
    # ========================================================================
    print("\n🔄 步骤3: 实体规范化 (合并同义词)")
    print("-"*80)
    
    merged_count = 0
    for synonym, canonical in ENTITY_SYNONYMS.items():
        # 检查两个实体是否都存在
        result = session.run("""
            MATCH (n1 {name: $synonym})
            MATCH (n2 {name: $canonical})
            RETURN count(*) as count
        """, synonym=synonym, canonical=canonical)
        
        if result.single()['count'] == 2:
            print(f"   合并: {synonym} -> {canonical}")
            
            # 将所有指向synonym的关系重定向到canonical
            session.run("""
                MATCH (n1 {name: $synonym})
                MATCH (n2 {name: $canonical})
                MATCH (n1)-[r]->(target)
                MERGE (n2)-[r2:RELATED_TO]->(target)
                SET r2 = properties(r)
                DELETE r
            """, synonym=synonym, canonical=canonical)
            
            session.run("""
                MATCH (n1 {name: $synonym})
                MATCH (n2 {name: $canonical})
                MATCH (source)-[r]->(n1)
                MERGE (source)-[r2:RELATED_TO]->(n2)
                SET r2 = properties(r)
                DELETE r
            """, synonym=synonym, canonical=canonical)
            
            # 删除synonym节点
            session.run("""
                MATCH (n {name: $synonym})
                DETACH DELETE n
            """, synonym=synonym)
            
            merged_count += 1
    
    print(f"   总计合并: {merged_count} 对同义词")
    
    # ========================================================================
    # 步骤4: 关系规范化 (拆分多重关系)
    # ========================================================================
    print("\n🔗 步骤4: 关系规范化 (拆分多重关系)")
    print("-"*80)
    
    # 查找所有包含 | 的关系
    result = session.run("""
        MATCH (n1)-[r]->(n2)
        WHERE r.type CONTAINS '|'
        RETURN n1.name as node1, r.type as rel_type, n2.name as node2, 
               r.weight as weight, type(r) as db_rel_type
    """)
    
    multi_relations = list(result)
    
    if multi_relations:
        print(f"   发现 {len(multi_relations)} 个多重关系需要拆分:")
        
        split_count = 0
        for rel in multi_relations[:20]:  # 限制处理数量，避免过长输出
            node1 = rel['node1']
            node2 = rel['node2']
            rel_type = rel['rel_type']
            weight = rel['weight']
            db_rel_type = rel['db_rel_type']
            
            # 拆分关系类型
            relations = [r.strip() for r in rel_type.split('|')]
            
            if len(relations) > 1:
                print(f"   拆分: {node1} --[{rel_type}]--> {node2}")
                print(f"     -> {len(relations)} 个独立关系")
                
                # 删除原关系
                session.run(f"""
                    MATCH (n1 {{name: $node1}})-[r:{db_rel_type}]->(n2 {{name: $node2}})
                    WHERE r.type = $rel_type
                    DELETE r
                """, node1=node1, node2=node2, rel_type=rel_type)
                
                # 创建拆分后的关系
                for single_rel in relations:
                    # 规范化关系名称
                    normalized_rel = RELATION_NORMALIZATION.get(single_rel, single_rel)
                    
                    # 创建Cypher安全的关系类型名称
                    safe_rel_type = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]', '_', normalized_rel)
                    
                    session.run(f"""
                        MATCH (n1 {{name: $node1}})
                        MATCH (n2 {{name: $node2}})
                        MERGE (n1)-[r:{safe_rel_type}]->(n2)
                        SET r.weight = $weight, r.type = $rel_type
                    """, node1=node1, node2=node2, weight=weight, rel_type=normalized_rel)
                
                split_count += 1
        
        print(f"   总计拆分: {split_count} 个多重关系")
    else:
        print("   ✅ 未发现需要拆分的多重关系")
    
    # ========================================================================
    # 步骤5: 最终验证
    # ========================================================================
    print("\n" + "="*80)
    print("最终验证")
    print("="*80)
    
    # 统计
    node_count = session.run("MATCH (n) RETURN count(n) as count").single()['count']
    rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']
    
    print(f"\n  节点总数: {node_count}")
    print(f"  关系总数: {rel_count}")
    
    # 检查是否还有因果倒置
    result = session.run("""
        MATCH (disease:疾病)-[r]->(pathogen:病原体)
        WHERE type(r) IN ['寄生于', '引起', '感染']
        RETURN count(*) as count
    """).single()['count']
    print(f"  因果倒置关系: {result} {'✅' if result == 0 else '❌'}")
    
    # 检查是否还有乱码
    garbage_count = 0
    for pattern in GARBAGE_PATTERNS[:3]:  # 检查前3个模式
        result = session.run("""
            MATCH (n)
            WHERE n.name CONTAINS $pattern
            RETURN count(*) as count
        """, pattern=pattern).single()['count']
        garbage_count += result
    print(f"  乱码节点: {garbage_count} {'✅' if garbage_count == 0 else '❌'}")

driver.close()

print("\n" + "="*80)
print("✓ 全面修复完成！")
print("="*80)

print("\n📌 建议:")
print("  1. 重新导出三元组: python3 export_triples.py")
print("  2. 在Neo4j Browser中验证: http://localhost:7474")
print("  3. 运行完整检查: python3 detect_issues.py")
