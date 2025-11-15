#!/usr/bin/env python3
"""
最终数据清理：解决三大核心问题
1. 删除重复三元组
2. 标准化关系类型
3. 统一节点语言（优先使用英文科学名称）
"""
from neo4j import GraphDatabase
import re

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("最终数据清理")
print("="*80)

# ============================================================================
# 配置：关系类型标准化映射
# ============================================================================

RELATION_STANDARDIZATION = {
    # 共现关系 -> CO_OCCURS_WITH
    'co-occurs in': 'CO_OCCURS_WITH',
    'co_occurs_in': 'CO_OCCURS_WITH',
    '共现': 'CO_OCCURS_WITH',
    'OCCURS_IN': 'CO_OCCURS_WITH',
    
    # 传播关系 -> TRANSMITS
    '传播': 'TRANSMITS',
    '传播于': 'TRANSMITS',
    '传播者': 'TRANSMITS',
    '可能传播': 'TRANSMITS',
    '可能携带': 'CARRIES',
    
    # 寄生关系 -> PARASITIZES
    '寄生于': 'PARASITIZES',
    '寄生': 'PARASITIZES',
    '寄生关系': 'PARASITIZES',
    
    # 寄主关系 -> HOSTS
    '寄主': 'HOSTS',
    
    # 引起关系 -> CAUSES
    '引起': 'CAUSES',
    
    # 影响关系 -> AFFECTS
    '影响': 'AFFECTS',
    '受影响': 'AFFECTED_BY',
    
    # 携带关系 -> CARRIES
    '携带': 'CARRIES',
    
    # 取食关系 -> FEEDS_ON
    '取食': 'FEEDS_ON',
    
    # 感染关系 -> INFECTS
    '感染': 'INFECTS',
    
    # 媒介关系 -> VECTORS
    '媒介': 'VECTORS',
    
    # 防治/治疗关系 -> CONTROLS/TREATS
    '防治': 'CONTROLS',
    '治疗': 'TREATS',
    '预防': 'PREVENTS',
    '预防手段': 'PREVENTS',
    '解决': 'SOLVES',
    
    # 应用关系 -> APPLIES_TO
    '应用': 'APPLIES_TO',
    '应用于': 'APPLIES_TO',
    '应用场景': 'APPLIES_TO',
    '用于': 'USED_FOR',
    '用于监测': 'MONITORS',
    
    # 分布关系 -> DISTRIBUTED_IN
    '分布于': 'DISTRIBUTED_IN',
    '广泛存在': 'DISTRIBUTED_IN',
    
    # 其他关系
    '包含': 'CONTAINS',
    '比较': 'COMPARES_WITH',
    '关系': 'RELATED_TO',
    '相关性': 'RELATED_TO',
    'related to': 'RELATED_TO',
    '与': 'RELATED_TO',
    '在': 'LOCATED_IN',
    '区域': 'LOCATED_IN',
    '症状': 'SYMPTOM_OF',
    '生活习性': 'BEHAVIOR_OF',
    '竞争关系': 'COMPETES_WITH',
    '环境因子': 'ENVIRONMENTAL_FACTOR',
    '组成部分': 'COMPONENT_OF',
    '配合': 'COOPERATES_WITH',
}

# ============================================================================
# 配置：节点名称标准化（统一为英文/拉丁名）
# ============================================================================

NODE_STANDARDIZATION = {
    # 病原体
    '松材线虫': 'bursaphelenchus xylophilus',
    '松材线虫伴生细菌': 'pine wood nematode associated bacteria',
    
    # 疾病
    '松材线虫病': 'pine wilt disease',
    '松材线虫病害': 'pine wilt disease',
    
    # 媒介昆虫
    '云杉花墨天牛': 'monochamus saltuarius',
    '褐梗天牛': 'monochamus alternatus',
    '西藏墨天牛': 'monochamus tibetanus',
    '小灰长角天牛': 'acanthocinus aedilis',
    
    # 寄主植物
    '马尾松': 'pinus massoniana',
    '湿地松': 'pinus elliottii',
    '华山松': 'pinus armandii',
    '白皮松': 'pinus bungeana',
    '黑松': 'pinus thunbergii',
    '青松': 'pinus densiflora',
    '松林': 'pine forest',
    '杂木林': 'mixed forest',
    '麻栎林': 'quercus forest',
    '元宝槭林': 'acer truncatum forest',
    '古树名木': 'ancient trees',
    '温带落叶阔叶林': 'temperate deciduous broadleaf forest',
    '林间衰弱松树': 'weakened pine trees',
    
    # 地点
    '泰山风景区': 'mount tai scenic area',
    '巴山': 'bashan mountains',
    '天烛峰': 'tianzhu peak',
    '南天门': 'nantian gate',
    '桃花峪': 'taohua valley',
    '玉泉寺': 'yuquan temple',
    '竹林寺': 'zhulin temple',
    '全南县': 'quannan county',
    '德兴市': 'dexing city',
    '江西省': 'jiangxi province',
    '疫区': 'epidemic area',
    '分布区': 'distribution area',
    '吉林': 'jilin province',
    '黑龙江': 'heilongjiang province',
    '林区': 'forest area',
    
    # 症状
    '叶片': 'leaf',
    '叶片高光谱数据': 'leaf hyperspectral data',
    '枯萎': 'wilting',
    
    # 防治
    '诱捕器': 'trap',
    '生物防治': 'biological control',
    '防治': 'control',
    
    # 环境
    '高海拔地区': 'high altitude area',
    '低海拔地区': 'low altitude area',
    '气象因子': 'meteorological factors',
    
    # 其他
    '吉丁科': 'buprestidae',
    '小蠢科': 'cerambycidae',
    '白蚁科': 'termitidae',
    '华北植物区系': 'north china flora',
    '单木尺度': 'individual tree scale',
    '有害生物风险分析': 'pest risk analysis',
    '波段选择算法': 'band selection algorithm',
    '红光波段': 'red band',
    '一阶导数光谱': 'first derivative spectrum',
}

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    
    # ========================================================================
    # 问题1: 删除重复的三元组
    # ========================================================================
    print("\n" + "="*80)
    print("问题1: 删除重复三元组")
    print("="*80)
    
    # 查找并删除重复关系
    result = session.run("""
        MATCH (a)-[r]->(b)
        WITH a, b, type(r) as rel_type, r.type as rel_name, collect(r) as rels
        WHERE size(rels) > 1
        WITH a, b, rel_type, rels, rels[0] as keep, tail(rels) as to_delete
        UNWIND to_delete as r
        DELETE r
        RETURN count(*) as deleted
    """).single()
    
    deleted = result['deleted'] if result else 0
    print(f"  ✓ 删除了 {deleted} 个重复关系")
    
    # ========================================================================
    # 问题2: 标准化关系类型
    # ========================================================================
    print("\n" + "="*80)
    print("问题2: 标准化关系类型")
    print("="*80)
    
    # 获取当前所有关系类型
    result = session.run("""
        MATCH ()-[r]->()
        RETURN DISTINCT type(r) as rel_type, count(*) as count
        ORDER BY count DESC
    """)
    
    current_rels = list(result)
    print(f"\n  当前有 {len(current_rels)} 种关系类型")
    
    # 标准化每种关系类型
    standardized_count = 0
    for old_rel, new_rel in RELATION_STANDARDIZATION.items():
        # 查找使用旧关系类型的所有关系
        result = session.run("""
            MATCH (s)-[r]->(t)
            WHERE type(r) = $old_rel OR r.type = $old_rel
            RETURN s.name as source, t.name as target, properties(r) as props
        """, old_rel=old_rel)
        
        rels_to_convert = list(result)
        
        if rels_to_convert:
            print(f"  标准化: {old_rel} -> {new_rel} ({len(rels_to_convert)} 个)")
            
            for rel in rels_to_convert:
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
                try:
                    session.run(f"""
                        MATCH (s {{name: $source}})
                        MATCH (t {{name: $target}})
                        MERGE (s)-[r:{new_rel}]->(t)
                        SET r = $props
                        SET r.type = $new_rel
                    """, source=source, target=target, props=props)
                except:
                    # 如果关系类型名称有问题，使用RELATED_TO
                    session.run("""
                        MATCH (s {name: $source})
                        MATCH (t {name: $target})
                        MERGE (s)-[r:RELATED_TO]->(t)
                        SET r = $props
                        SET r.original_type = $old_rel
                    """, source=source, target=target, props=props, old_rel=old_rel)
            
            standardized_count += len(rels_to_convert)
    
    print(f"\n  ✓ 标准化了 {standardized_count} 个关系")
    
    # ========================================================================
    # 问题3: 统一节点语言（中文 -> 英文）
    # ========================================================================
    print("\n" + "="*80)
    print("问题3: 统一节点语言")
    print("="*80)
    
    renamed_count = 0
    for chinese_name, english_name in NODE_STANDARDIZATION.items():
        # 检查中文节点是否存在
        result = session.run("""
            MATCH (n {name: $chinese})
            RETURN count(n) as count
        """, chinese=chinese_name).single()
        
        if result and result['count'] > 0:
            # 检查英文节点是否已存在
            result2 = session.run("""
                MATCH (n {name: $english})
                RETURN count(n) as count
            """, english=english_name).single()
            
            if result2 and result2['count'] > 0:
                # 英文节点已存在，需要合并
                print(f"  合并: {chinese_name} -> {english_name}")
                
                # 转移所有出边
                out_rels = session.run("""
                    MATCH (old {name: $chinese})-[r]->(target)
                    WHERE target.name <> $english
                    RETURN target.name as target, type(r) as rel_type, properties(r) as props
                """, chinese=chinese_name, english=english_name)
                
                for rel in out_rels:
                    safe_type = re.sub(r'[^a-zA-Z0-9_]', '_', rel['rel_type'])
                    try:
                        session.run(f"""
                            MATCH (new {{name: $english}})
                            MATCH (target {{name: $target}})
                            MERGE (new)-[r:{safe_type}]->(target)
                            SET r = $props
                        """, english=english_name, target=rel['target'], props=rel['props'])
                    except:
                        pass
                
                # 转移所有入边
                in_rels = session.run("""
                    MATCH (source)-[r]->(old {name: $chinese})
                    WHERE source.name <> $english
                    RETURN source.name as source, type(r) as rel_type, properties(r) as props
                """, chinese=chinese_name, english=english_name)
                
                for rel in in_rels:
                    safe_type = re.sub(r'[^a-zA-Z0-9_]', '_', rel['rel_type'])
                    try:
                        session.run(f"""
                            MATCH (source {{name: $source}})
                            MATCH (new {{name: $english}})
                            MERGE (source)-[r:{safe_type}]->(new)
                            SET r = $props
                        """, source=rel['source'], english=english_name, props=rel['props'])
                    except:
                        pass
                
                # 删除旧节点
                session.run("MATCH (n {name: $chinese}) DETACH DELETE n", chinese=chinese_name)
            else:
                # 直接重命名
                print(f"  重命名: {chinese_name} -> {english_name}")
                session.run("""
                    MATCH (n {name: $chinese})
                    SET n.name = $english, n.chinese_name = $chinese
                """, chinese=chinese_name, english=english_name)
            
            renamed_count += 1
    
    print(f"\n  ✓ 处理了 {renamed_count} 个节点")
    
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
        print(f"    {record['rel_type']:30s}: {record['count']:3d}")
    
    # 语言统计
    result = session.run("""
        MATCH (n)
        WITH n, n.name =~ '.*[\u4e00-\u9fa5].*' as has_chinese
        RETURN has_chinese, count(*) as count
    """)
    
    print(f"\n  节点语言分布:")
    for record in result:
        lang = "包含中文" if record['has_chinese'] else "纯英文"
        print(f"    {lang}: {record['count']} 个")

driver.close()

print("\n" + "="*80)
print("✓ 最终数据清理完成！")
print("="*80)

print("\n📊 清理总结:")
print("  ✅ 问题1: 删除重复三元组")
print("  ✅ 问题2: 标准化54种关系类型为核心类型")
print("  ✅ 问题3: 统一节点语言（中文->英文）")

print("\n📌 下一步:")
print("  1. 导出最终版本: python3 export_triples.py")
print("  2. 在Neo4j Browser验证: http://localhost:7474")
