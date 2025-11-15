#!/usr/bin/env python3
"""
终极清理脚本：彻底解决三大核心语义问题
1. 逻辑矛盾（因果倒置）
2. 关系定义混乱（管道符拆分）
3. 实体冗余（同义词合并）
"""
from neo4j import GraphDatabase
import re

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("知识图谱终极清理")
print("="*80)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    
    # ========================================================================
    # 问题1: 删除逻辑矛盾关系
    # ========================================================================
    print("\n" + "="*80)
    print("问题1: 删除逻辑矛盾关系")
    print("="*80)
    
    print("\n  检查并删除 'pine wilt disease' --[引起]--> 'bursaphelenchus xylophilus'...")
    
    # 删除错误的因果关系
    result = session.run("""
        MATCH (disease {name: 'pine wilt disease'})-[r]->(pathogen {name: 'bursaphelenchus xylophilus'})
        WHERE r.type CONTAINS '引起'
        DELETE r
        RETURN count(*) as deleted
    """).single()
    
    if result and result['deleted'] > 0:
        print(f"  ✓ 删除了 {result['deleted']} 个错误的因果关系")
    else:
        print("  ✓ 未发现错误的因果关系")
    
    # 验证正确的关系是否存在
    result = session.run("""
        MATCH (pathogen {name: 'bursaphelenchus xylophilus'})-[r]->(disease {name: 'pine wilt disease'})
        WHERE r.type = '引起'
        RETURN count(*) as count
    """).single()
    
    if result and result['count'] > 0:
        print(f"  ✓ 正确的关系存在: bursaphelenchus xylophilus --[引起]--> pine wilt disease")
    else:
        print("  ⚠️  正确的关系不存在，需要创建")
        session.run("""
            MATCH (pathogen {name: 'bursaphelenchus xylophilus'})
            MATCH (disease {name: 'pine wilt disease'})
            MERGE (pathogen)-[r:引起]->(disease)
            SET r.weight = 0.9, r.type = '引起'
        """)
        print("  ✓ 已创建正确的关系")
    
    # ========================================================================
    # 问题2: 拆分所有包含管道符的关系
    # ========================================================================
    print("\n" + "="*80)
    print("问题2: 拆分包含管道符的关系")
    print("="*80)
    
    # 查找所有包含管道符的关系
    result = session.run("""
        MATCH (s)-[r]->(t)
        WHERE r.type CONTAINS '|'
        RETURN s.name as source, r.type as rel_type, t.name as target, 
               r.weight as weight, id(r) as rel_id
    """)
    
    compound_rels = list(result)
    
    if compound_rels:
        print(f"\n  发现 {len(compound_rels)} 个包含管道符的关系")
        print("  开始拆分...")
        
        split_count = 0
        for rel in compound_rels:
            source = rel['source']
            target = rel['target']
            rel_type = rel['rel_type']
            weight = rel['weight'] if rel['weight'] else 0.1
            
            # 拆分关系类型
            parts = [p.strip() for p in rel_type.split('|')]
            # 去重并过滤空字符串
            unique_parts = [p for p in set(parts) if p and p != 'co-occurs in']
            
            # 如果拆分后没有有意义的关系，保留co-occurs in
            if not unique_parts:
                unique_parts = ['co-occurs in']
            
            if len(unique_parts) > 0:
                # 删除原关系
                session.run("""
                    MATCH (s {name: $source})-[r]->(t {name: $target})
                    WHERE r.type = $rel_type
                    DELETE r
                """, source=source, target=target, rel_type=rel_type)
                
                # 创建拆分后的关系
                for part in unique_parts:
                    # 清理关系名称
                    clean_part = part.strip()
                    
                    # 创建安全的关系类型名（用于Cypher）
                    safe_type = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]', '_', clean_part)
                    
                    try:
                        session.run(f"""
                            MATCH (s {{name: $source}})
                            MATCH (t {{name: $target}})
                            MERGE (s)-[r:{safe_type}]->(t)
                            SET r.weight = $weight, r.type = $clean_part
                        """, source=source, target=target, weight=weight, clean_part=clean_part)
                    except:
                        # 如果关系类型名称有问题，使用通用关系
                        session.run("""
                            MATCH (s {name: $source})
                            MATCH (t {name: $target})
                            MERGE (s)-[r:RELATED_TO]->(t)
                            SET r.weight = $weight, r.type = $clean_part
                        """, source=source, target=target, weight=weight, clean_part=clean_part)
                
                split_count += 1
                
                if split_count % 10 == 0:
                    print(f"  进度: {split_count}/{len(compound_rels)}")
        
        print(f"  ✓ 拆分了 {split_count} 个复合关系")
    else:
        print("  ✓ 未发现包含管道符的关系")
    
    # ========================================================================
    # 问题3: 合并实体冗余（同义词）
    # ========================================================================
    print("\n" + "="*80)
    print("问题3: 合并实体冗余")
    print("="*80)
    
    # 定义同义词映射
    synonyms = {
        'sentinal-2': 'sentinel-2',  # 拼写错误
        'sentinel-2 卫星遥感影像': 'sentinel-2',  # 描述性文字
    }
    
    merged_count = 0
    for old_name, new_name in synonyms.items():
        # 检查是否存在
        old_exists = session.run("MATCH (n {name: $name}) RETURN count(n) as count", 
                                name=old_name).single()['count'] > 0
        new_exists = session.run("MATCH (n {name: $name}) RETURN count(n) as count", 
                                name=new_name).single()['count'] > 0
        
        if old_exists:
            if new_exists:
                print(f"\n  合并: {old_name} -> {new_name}")
                
                # 获取旧节点的所有出边
                out_rels = session.run("""
                    MATCH (old {name: $old_name})-[r]->(target)
                    WHERE target.name <> $new_name
                    RETURN target.name as target, type(r) as rel_type, properties(r) as props
                """, old_name=old_name, new_name=new_name)
                
                # 重建出边
                for rel in out_rels:
                    safe_type = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]', '_', rel['rel_type'])
                    try:
                        session.run(f"""
                            MATCH (new {{name: $new_name}})
                            MATCH (target {{name: $target}})
                            MERGE (new)-[r:{safe_type}]->(target)
                            SET r = $props
                        """, new_name=new_name, target=rel['target'], props=rel['props'])
                    except:
                        pass
                
                # 获取旧节点的所有入边
                in_rels = session.run("""
                    MATCH (source)-[r]->(old {name: $old_name})
                    WHERE source.name <> $new_name
                    RETURN source.name as source, type(r) as rel_type, properties(r) as props
                """, old_name=old_name, new_name=new_name)
                
                # 重建入边
                for rel in in_rels:
                    safe_type = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]', '_', rel['rel_type'])
                    try:
                        session.run(f"""
                            MATCH (source {{name: $source}})
                            MATCH (new {{name: $new_name}})
                            MERGE (source)-[r:{safe_type}]->(new)
                            SET r = $props
                        """, source=rel['source'], new_name=new_name, props=rel['props'])
                    except:
                        pass
                
                # 删除旧节点
                session.run("MATCH (n {name: $old_name}) DETACH DELETE n", old_name=old_name)
                merged_count += 1
                print(f"  ✓ 完成")
            else:
                # 只有旧节点存在，直接重命名
                print(f"\n  重命名: {old_name} -> {new_name}")
                session.run("MATCH (n {name: $old_name}) SET n.name = $new_name", 
                           old_name=old_name, new_name=new_name)
                merged_count += 1
    
    print(f"\n  ✓ 处理了 {merged_count} 对同义词")
    
    # ========================================================================
    # 额外清理: 去除重复关系
    # ========================================================================
    print("\n" + "="*80)
    print("额外清理: 去除重复关系")
    print("="*80)
    
    # 查找并删除完全重复的关系
    result = session.run("""
        MATCH (a)-[r]->(b)
        WITH a, b, type(r) as rel_type, collect(r) as rels
        WHERE size(rels) > 1
        WITH a, b, rel_type, rels, rels[0] as keep, tail(rels) as to_delete
        UNWIND to_delete as r
        DELETE r
        RETURN count(*) as deleted
    """).single()
    
    if result and result['deleted'] > 0:
        print(f"  ✓ 删除了 {result['deleted']} 个重复关系")
    else:
        print("  ✓ 未发现重复关系")
    
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
    
    # 检查问题1: 逻辑矛盾
    result = session.run("""
        MATCH (disease {name: 'pine wilt disease'})-[r]->(pathogen {name: 'bursaphelenchus xylophilus'})
        WHERE r.type CONTAINS '引起'
        RETURN count(*) as count
    """).single()['count']
    print(f"\n  【问题1】逻辑矛盾: {result} {'✅' if result == 0 else '❌'}")
    
    # 检查问题2: 管道符关系
    result = session.run("""
        MATCH ()-[r]->()
        WHERE r.type CONTAINS '|'
        RETURN count(r) as count
    """).single()['count']
    print(f"  【问题2】管道符关系: {result} {'✅' if result == 0 else '❌'}")
    
    # 检查问题3: 实体冗余
    result = session.run("""
        MATCH (n)
        WHERE n.name IN ['sentinal-2', 'sentinel-2 卫星遥感影像']
        RETURN count(n) as count
    """).single()['count']
    print(f"  【问题3】冗余实体: {result} {'✅' if result == 0 else '❌'}")
    
    # 关系类型统计
    print(f"\n  关系类型分布（前15）:")
    result = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) as rel_type, count(*) as count
        ORDER BY count DESC
        LIMIT 15
    """)
    
    for record in result:
        rel_type = record['rel_type'][:30] if len(record['rel_type']) > 30 else record['rel_type']
        print(f"    {rel_type:32s}: {record['count']:3d}")

driver.close()

print("\n" + "="*80)
print("✓ 终极清理完成！")
print("="*80)

print("\n📊 修复总结:")
print("  ✅ 问题1: 删除逻辑矛盾（因果倒置）")
print("  ✅ 问题2: 拆分所有管道符关系")
print("  ✅ 问题3: 合并实体冗余（同义词）")
print("  ✅ 额外: 去除重复关系")

print("\n📌 下一步:")
print("  1. 导出验证: python3 export_triples.py")
print("  2. 重新分析: 使用pandas检查导出的CSV")
print("  3. Neo4j查询: http://localhost:7474")
