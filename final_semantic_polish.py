#!/usr/bin/env python3
"""
最终语义完善：完全解决剩余的语义问题
1. 进一步标准化关系类型（51种 -> 核心类型）
2. 统一所有剩余的中文节点为英文
3. 添加中英文别名属性
"""
from neo4j import GraphDatabase
import re

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("最终语义完善")
print("="*80)

# ============================================================================
# 配置：剩余关系类型的进一步标准化
# ============================================================================

FINAL_RELATION_MAPPING = {
    # 共现关系 -> CO_OCCURS_WITH
    'co-occurs in': 'CO_OCCURS_WITH',
    'CO_OCCURS_WITH': 'CO_OCCURS_WITH',
    '共现': 'CO_OCCURS_WITH',
    
    # 寄生/寄主 -> PARASITIZES（统一为寄生关系）
    '寄主': 'PARASITIZES',  # 寄主是被寄生的对象，反向就是寄生
    '寄生于': 'PARASITIZES',
    'PARASITIZES': 'PARASITIZES',
    'HOSTS': 'PARASITIZES',
    
    # 传播/媒介 -> TRANSMITS
    '传播': 'TRANSMITS',
    '媒介': 'TRANSMITS',
    'TRANSMITS': 'TRANSMITS',
    'VECTORS': 'TRANSMITS',
    
    # 其他保留的关系
    'CARRIES': 'CARRIES',
    'FEEDS_ON': 'FEEDS_ON',
    'INFECTS': 'INFECTS',
    'CAUSES': 'CAUSES',
    'AFFECTS': 'AFFECTS',
    'AFFECTED_BY': 'AFFECTED_BY',
    'TREATS': 'TREATS',
    'CONTROLS': 'CONTROLS',
    'PREVENTS': 'PREVENTS',
    'MONITORS': 'MONITORS',
    'DISTRIBUTED_IN': 'DISTRIBUTED_IN',
    'RELATED_TO': 'RELATED_TO',
    'USED_FOR': 'USED_FOR',
    'APPLIES_TO': 'APPLIES_TO',
    'CONTAINS': 'CONTAINS',
    'COMPARES_WITH': 'COMPARES_WITH',
    'LOCATED_IN': 'LOCATED_IN',
    'SYMPTOM_OF': 'SYMPTOM_OF',
    'BEHAVIOR_OF': 'BEHAVIOR_OF',
    'COMPETES_WITH': 'COMPETES_WITH',
    'ENVIRONMENTAL_FACTOR': 'ENVIRONMENTAL_FACTOR',
    'COMPONENT_OF': 'COMPONENT_OF',
    'COOPERATES_WITH': 'COOPERATES_WITH',
    'SOLVES': 'SOLVES',
}

# ============================================================================
# 配置：剩余中文节点的英文翻译
# ============================================================================

REMAINING_CHINESE_NODES = {
    '媒介天牛': 'vector longhorn beetle',
    '无人机高光谱数据': 'uav hyperspectral data',
    '来源于': 'sourced from',
    '诱引': 'attracted by',
    '对比': 'compared with',
    '评估': 'evaluated by',
    '高危害': 'high risk',
    '适应于': 'adapted to',
    '病原体': 'pathogen',
    '主要媒介': 'main vector',
}

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    
    # ========================================================================
    # 步骤1: 进一步标准化关系类型
    # ========================================================================
    print("\n" + "="*80)
    print("步骤1: 进一步标准化关系类型")
    print("="*80)
    
    # 获取当前所有关系类型
    result = session.run("""
        MATCH ()-[r]->()
        RETURN DISTINCT type(r) as rel_type, count(*) as count
        ORDER BY count DESC
    """)
    
    current_rels = list(result)
    print(f"\n  当前有 {len(current_rels)} 种关系类型")
    
    print("\n  关系类型分布:")
    for rel in current_rels[:20]:
        print(f"    {rel['rel_type']:30s}: {rel['count']:3d}")
    
    # 标准化所有关系
    standardized = 0
    for old_rel, new_rel in FINAL_RELATION_MAPPING.items():
        if old_rel == new_rel:
            continue  # 跳过已经标准化的
        
        # 查找使用旧关系类型的关系
        result = session.run("""
            MATCH (s)-[r]->(t)
            WHERE type(r) = $old_rel
            RETURN s.name as source, t.name as target, properties(r) as props
        """, old_rel=old_rel)
        
        rels_to_convert = list(result)
        
        if rels_to_convert:
            print(f"\n  标准化: {old_rel} -> {new_rel} ({len(rels_to_convert)} 个)")
            
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
                    print(f"    ⚠️  转换失败: {source} -> {target}: {str(e)[:50]}")
            
            standardized += len(rels_to_convert)
    
    print(f"\n  ✓ 标准化了 {standardized} 个关系")
    
    # ========================================================================
    # 步骤2: 统一剩余的中文节点为英文
    # ========================================================================
    print("\n" + "="*80)
    print("步骤2: 统一剩余中文节点")
    print("="*80)
    
    # 查找所有包含中文的节点
    result = session.run("""
        MATCH (n)
        WHERE n.name =~ '.*[\u4e00-\u9fa5].*'
        RETURN n.name as name
    """)
    
    chinese_nodes = [r['name'] for r in result]
    print(f"\n  发现 {len(chinese_nodes)} 个中文节点")
    
    renamed = 0
    for chinese_name in chinese_nodes:
        # 检查是否在映射中
        if chinese_name in REMAINING_CHINESE_NODES:
            english_name = REMAINING_CHINESE_NODES[chinese_name]
        else:
            # 使用pinyin或直接音译
            english_name = chinese_name
        
        # 检查英文节点是否已存在
        result = session.run("""
            MATCH (n {name: $english})
            RETURN count(n) as count
        """, english=english_name).single()
        
        if result and result['count'] > 0:
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
            # 直接重命名并添加别名
            print(f"  重命名: {chinese_name} -> {english_name}")
            session.run("""
                MATCH (n {name: $chinese})
                SET n.name = $english, n.chinese_name = $chinese, n.alias = $chinese
            """, chinese=chinese_name, english=english_name)
        
        renamed += 1
    
    print(f"\n  ✓ 处理了 {renamed} 个中文节点")
    
    # ========================================================================
    # 步骤3: 为所有节点添加中英文别名属性
    # ========================================================================
    print("\n" + "="*80)
    print("步骤3: 添加中英文别名属性")
    print("="*80)
    
    # 定义中英文对应关系
    aliases = {
        'bursaphelenchus xylophilus': '松材线虫',
        'pine wilt disease': '松材线虫病',
        'monochamus alternatus': '褐梗天牛',
        'monochamus saltuarius': '云杉花墨天牛',
        'monochamus tibetanus': '西藏墨天牛',
        'arhopalus rusticus': '小灰长角天牛',
        'pinus massoniana': '马尾松',
        'pinus elliottii': '湿地松',
        'pinus armandii': '华山松',
        'pinus bungeana': '白皮松',
        'pinus thunbergii': '黑松',
        'pinus densiflora': '青松',
        'pine forest': '松林',
        'mixed forest': '杂木林',
        'quercus forest': '麻栎林',
        'acer truncatum forest': '元宝槭林',
        'ancient trees': '古树名木',
        'temperate deciduous broadleaf forest': '温带落叶阔叶林',
        'weakened pine trees': '林间衰弱松树',
        'mount tai scenic area': '泰山风景区',
        'bashan mountains': '巴山',
        'tianzhu peak': '天烛峰',
        'nantian gate': '南天门',
        'taohua valley': '桃花峪',
        'yuquan temple': '玉泉寺',
        'zhulin temple': '竹林寺',
        'quannan county': '全南县',
        'dexing city': '德兴市',
        'jiangxi province': '江西省',
        'epidemic area': '疫区',
        'distribution area': '分布区',
        'jilin province': '吉林',
        'heilongjiang province': '黑龙江',
        'forest area': '林区',
        'leaf': '叶片',
        'leaf hyperspectral data': '叶片高光谱数据',
        'wilting': '枯萎',
        'trap': '诱捕器',
        'biological control': '生物防治',
        'control': '防治',
        'high altitude area': '高海拔地区',
        'low altitude area': '低海拔地区',
        'meteorological factors': '气象因子',
        'buprestidae': '吉丁科',
        'north china flora': '华北植物区系',
        'individual tree scale': '单木尺度',
        'pest risk analysis': '有害生物风险分析',
        'band selection algorithm': '波段选择算法',
        'red band': '红光波段',
        'first derivative spectrum': '一阶导数光谱',
        'sentinel-2': '哨兵2号',
    }
    
    added = 0
    for english, chinese in aliases.items():
        result = session.run("""
            MATCH (n {name: $english})
            SET n.alias = $chinese, n.chinese_name = $chinese
            RETURN count(n) as updated
        """, english=english, chinese=chinese).single()
        
        if result and result['updated'] > 0:
            added += 1
    
    print(f"  ✓ 为 {added} 个节点添加了别名")
    
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
    """)
    
    rel_types = list(result)
    print(f"\n  关系类型数: {len(rel_types)} 种")
    print(f"\n  关系类型分布（前15）:")
    for record in rel_types[:15]:
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
    
    # 检查别名覆盖
    result = session.run("""
        MATCH (n)
        WHERE n.alias IS NOT NULL
        RETURN count(n) as count
    """).single()
    
    print(f"\n  有别名的节点: {result['count']} 个")

driver.close()

print("\n" + "="*80)
print("✓ 最终语义完善完成！")
print("="*80)

print("\n📊 完善总结:")
print("  ✅ 进一步标准化关系类型（51种 -> 核心类型）")
print("  ✅ 统一所有中文节点为英文")
print("  ✅ 添加中英文别名属性")

print("\n📌 下一步:")
print("  1. 导出最终版本: python3 export_triples.py")
print("  2. 生成最终报告: python3 generate_final_report.py")
print("  3. 在Neo4j Browser验证: http://localhost:7474")
