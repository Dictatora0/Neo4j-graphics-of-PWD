#!/usr/bin/env python3
"""
将清理后的三元组导入Neo4j数据库
包含样式优化和美观度提升
"""
from neo4j import GraphDatabase
import pandas as pd
from datetime import datetime
import os

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

print("="*80)
print("导入三元组到Neo4j数据库")
print("="*80)

# 读取CSV文件: 优先使用语义清洗后的版本
semantic_clean_path = 'output/triples_export_semantic_clean.csv'
raw_path = 'output/triples_export.csv'

if os.path.exists(semantic_clean_path):
    csv_path = semantic_clean_path
    print(f"\n使用语义清洗后的三元组文件: {csv_path}")
else:
    csv_path = raw_path
    print(f"\n未找到语义清洗文件, 使用原始三元组文件: {csv_path}")

df = pd.read_csv(csv_path)

print("\n数据统计:")
print(f"  总行数: {len(df)}")
print(f"  关系类型: {df['relationship'].nunique()}")
print(f"  唯一节点: {len(set(df['node_1'].unique()) | set(df['node_2'].unique()))}")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    
    # ========================================================================
    # 步骤1: 清空现有数据
    # ========================================================================
    print("\n" + "="*80)
    print("步骤1: 清空现有数据")
    print("="*80)
    
    session.run("MATCH (n) DETACH DELETE n")
    print("  已清空所有节点和关系")
    
    # ========================================================================
    # 步骤2: 定义节点样式和颜色
    # ========================================================================
    print("\n" + "="*80)
    print("步骤2: 创建节点（带样式）")
    print("="*80)
    
    # 节点分类和颜色（去除图标中的表情符号，只保留类型标签）
    node_styles = {
        'bursaphelenchus xylophilus': {
            'type': 'Pathogen',
            'color': '#FF6B6B',  # 红色
            'size': 'large',
            'icon': 'PATHOGEN'
        },
        'pine wilt disease': {
            'type': 'Disease',
            'color': '#FF8C42',  # 橙色
            'size': 'large',
            'icon': 'DISEASE'
        },
        'monochamus alternatus': {
            'type': 'Vector',
            'color': '#4ECDC4',  # 青色
            'size': 'large',
            'icon': 'VECTOR'
        },
        'monochamus saltuarius': {
            'type': 'Vector',
            'color': '#4ECDC4',
            'size': 'medium',
            'icon': 'VECTOR'
        },
        'pinus thunbergii': {
            'type': 'Host',
            'color': '#95E1D3',  # 浅绿色
            'size': 'large',
            'icon': 'HOST'
        },
        'pinus massoniana': {
            'type': 'Host',
            'color': '#95E1D3',
            'size': 'medium',
            'icon': 'HOST'
        },
        'pinus elliottii': {
            'type': 'Host',
            'color': '#95E1D3',
            'size': 'medium',
            'icon': 'HOST'
        },
        'biological control': {
            'type': 'Control',
            'color': '#A8E6CF',  # 绿色
            'size': 'medium',
            'icon': 'CONTROL'
        },
        'trap': {
            'type': 'Control',
            'color': '#A8E6CF',
            'size': 'medium',
            'icon': 'TRAP'
        },
    }
    
    # 默认样式
    default_styles = {
        'Pathogen': {'color': '#FF6B6B', 'size': 'medium', 'icon': 'PATHOGEN'},
        'Disease': {'color': '#FF8C42', 'size': 'medium', 'icon': 'DISEASE'},
        'Vector': {'color': '#4ECDC4', 'size': 'medium', 'icon': 'VECTOR'},
        'Host': {'color': '#95E1D3', 'size': 'medium', 'icon': 'HOST'},
        'Location': {'color': '#FFE66D', 'size': 'small', 'icon': 'LOCATION'},
        'Technology': {'color': '#95B8D1', 'size': 'small', 'icon': 'TECH'},
        'Control': {'color': '#A8E6CF', 'size': 'medium', 'icon': 'CONTROL'},
        'Other': {'color': '#C7CEEA', 'size': 'small', 'icon': 'OTHER'},
    }
    
    # 获取所有唯一节点
    all_nodes = set(df['node_1'].unique()) | set(df['node_2'].unique())
    
    created_nodes = 0
    for node in all_nodes:
        # 确定节点类型和样式
        if node in node_styles:
            style = node_styles[node]
            node_type = style['type']
            color = style['color']
            icon = style['icon']
        else:
            # 根据节点名称推断类型
            if any(x in node.lower() for x in ['pine', 'pinus', 'forest', 'tree']):
                node_type = 'Host'
                style = default_styles['Host']
            elif any(x in node.lower() for x in ['monochamus', 'arhopalus', 'beetle']):
                node_type = 'Vector'
                style = default_styles['Vector']
            elif any(x in node.lower() for x in ['disease', 'wilt']):
                node_type = 'Disease'
                style = default_styles['Disease']
            elif any(x in node.lower() for x in ['control', 'trap', 'biological']):
                node_type = 'Control'
                style = default_styles['Control']
            elif any(x in node.lower() for x in ['sentinel', 'spectral', 'hyperspectral', 'algorithm']):
                node_type = 'Technology'
                style = default_styles['Technology']
            elif any(x in node.lower() for x in ['area', 'region', 'province', 'mountain', 'peak']):
                node_type = 'Location'
                style = default_styles['Location']
            else:
                node_type = 'Other'
                style = default_styles['Other']
            
            color = style['color']
            icon = style.get('icon', '')
        
        # 创建节点
        session.run(f"""
            CREATE (n:{node_type} {{
                name: $name,
                type: $type,
                color: $color,
                icon: $icon,
                created_at: $timestamp,
                display_name: $display_name
            }})
        """, 
        name=node,
        type=node_type,
        color=color,
        icon=icon,
        timestamp=datetime.now().isoformat(),
        display_name=node)
        
        created_nodes += 1
    
    print(f"  创建了 {created_nodes} 个节点")
    
    # ========================================================================
    # 步骤3: 创建关系（带样式）
    # ========================================================================
    print("\n" + "="*80)
    print("步骤3: 创建关系")
    print("="*80)
    
    # 关系样式
    relation_styles = {
        'CO_OCCURS_WITH': {
            'color': '#CCCCCC',
            'width': 1,
            'style': 'dashed',
            'label': '共现'
        },
        'PARASITIZES': {
            'color': '#FF6B6B',
            'width': 3,
            'style': 'solid',
            'label': '寄生'
        },
        'TRANSMITS': {
            'color': '#FF8C42',
            'width': 3,
            'style': 'solid',
            'label': '传播'
        },
        'AFFECTS': {
            'color': '#FFD93D',
            'width': 2,
            'style': 'solid',
            'label': '影响'
        },
        'CAUSES': {
            'color': '#FF6B6B',
            'width': 3,
            'style': 'solid',
            'label': '引起'
        },
        'INFECTS': {
            'color': '#FF6B6B',
            'width': 3,
            'style': 'solid',
            'label': '感染'
        },
        'FEEDS_ON': {
            'color': '#4ECDC4',
            'width': 2,
            'style': 'solid',
            'label': '取食'
        },
        'CARRIES': {
            'color': '#4ECDC4',
            'width': 2,
            'style': 'solid',
            'label': '携带'
        },
        'TREATS': {
            'color': '#95E1D3',
            'width': 2,
            'style': 'solid',
            'label': '治疗'
        },
        'CONTROLS': {
            'color': '#A8E6CF',
            'width': 2,
            'style': 'solid',
            'label': '防治'
        },
        'DISTRIBUTED_IN': {
            'color': '#FFE66D',
            'width': 2,
            'style': 'solid',
            'label': '分布于'
        },
        'MONITORS': {
            'color': '#95B8D1',
            'width': 2,
            'style': 'solid',
            'label': '监测'
        },
    }
    
    default_relation_style = {
        'color': '#CCCCCC',
        'width': 1,
        'style': 'dashed',
        'label': '相关'
    }
    
    created_rels = 0
    for _, row in df.iterrows():
        source = row['node_1']
        target = row['node_2']
        rel_type = row['relationship']
        weight = row['weight']
        
        # 获取关系样式
        style = relation_styles.get(rel_type, default_relation_style)
        
        # 创建关系
        try:
            session.run(f"""
                MATCH (s {{name: $source}})
                MATCH (t {{name: $target}})
                CREATE (s)-[r:{rel_type} {{
                    weight: $weight,
                    color: $color,
                    width: $width,
                    style: $style,
                    label: $label,
                    created_at: $timestamp
                }}]->(t)
            """,
            source=source,
            target=target,
            weight=weight,
            color=style['color'],
            width=style['width'],
            style=style['style'],
            label=style['label'],
            timestamp=datetime.now().isoformat())
            
            created_rels += 1
        except Exception as e:
            print(f"  创建关系失败: {source} -> {target}: {str(e)[:50]}")
    
    print(f"  创建了 {created_rels} 个关系")
    
    # ========================================================================
    # 步骤4: 创建索引以提高查询性能
    # ========================================================================
    print("\n" + "="*80)
    print("步骤4: 创建索引")
    print("="*80)
    
    index_queries = [
        "CREATE INDEX node_name IF NOT EXISTS FOR (n) ON (n.name)",
        "CREATE INDEX node_type IF NOT EXISTS FOR (n) ON (n.type)",
        "CREATE INDEX rel_weight IF NOT EXISTS FOR ()-[r]-() ON (r.weight)",
    ]
    
    for query in index_queries:
        try:
            session.run(query)
            print(f"  已执行: {query.split('FOR')[0].strip()}")
        except:
            pass
    
    # ========================================================================
    # 步骤5: 添加统计信息
    # ========================================================================
    print("\n" + "="*80)
    print("步骤5: 添加统计信息")
    print("="*80)
    
    # 计算节点度数
    session.run("""
        MATCH (n)
        WITH n, COUNT {(n)-[]->()} as out_degree, COUNT {()-[]->(n)} as in_degree
        SET n.out_degree = out_degree, n.in_degree = in_degree, n.total_degree = out_degree + in_degree
    """)
    
    print("  已计算节点度数")
    
    # 计算关系权重统计
    session.run("""
        MATCH ()-[r]->()
        WITH type(r) as rel_type, avg(r.weight) as avg_weight, max(r.weight) as max_weight, min(r.weight) as min_weight
        RETURN rel_type, avg_weight, max_weight, min_weight
    """)
    
    print("  已计算关系权重统计")
    
    # ========================================================================
    # 步骤6: 最终验证
    # ========================================================================
    print("\n" + "="*80)
    print("步骤6: 最终验证")
    print("="*80)
    
    result = session.run("MATCH (n) RETURN count(n) as count").single()
    node_count = result['count']
    
    result = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()
    rel_count = result['count']
    
    print(f"\n  导入完成:")
    print(f"    节点数: {node_count}")
    print(f"    关系数: {rel_count}")
    
    # 显示节点类型分布
    result = session.run("""
        MATCH (n)
        RETURN n.type as type, count(*) as count
        ORDER BY count DESC
    """)
    
    print(f"\n  节点类型分布:")
    for record in result:
        print(f"    {record['type']:15s}: {record['count']:2d}")
    
    # 显示关系类型分布
    result = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) as rel_type, count(*) as count
        ORDER BY count DESC
        LIMIT 10
    """)
    
    print(f"\n  关系类型分布（前10）:")
    for record in result:
        print(f"    {record['rel_type']:25s}: {record['count']:3d}")
    
    # 显示度数最高的节点
    result = session.run("""
        MATCH (n)
        RETURN n.name as name, n.icon as icon, n.total_degree as degree
        ORDER BY degree DESC
        LIMIT 5
    """)
    
    print(f"\n  度数最高的节点:")
    for record in result:
        print(f"    {record['name']:40s}: {record['degree']}")

driver.close()

print("\n" + "="*80)
print("导入完成")
print("="*80)

print("\n导入统计:")
print(f"  节点: {created_nodes} 个")
print(f"  关系: {created_rels} 个")
print(f"  样式: 已应用")
print(f"  索引: 已创建")

print("\n查询示例:")
print("  查看所有节点: MATCH (n) RETURN n")
print("  查看所有关系: MATCH ()-[r]->() RETURN r")
print("  查看高度数节点: MATCH (n) RETURN n ORDER BY n.total_degree DESC LIMIT 10")
print("  查看特定关系: MATCH ()-[r:PARASITIZES]->() RETURN r")

print("\n访问 Neo4j Browser:")
print("  URL: http://localhost:7474")
print("  用户名: neo4j")
print("  密码: 12345678")

print("\n使用建议:")
print("  1. 在 Neo4j Browser 中运行查询查看可视化")
print("  2. 使用 MATCH (n) RETURN n LIMIT 25 查看节点")
print("  3. 使用 MATCH p=()-[r]->() RETURN p LIMIT 25 查看关系")
print("  4. 尝试路径查询: MATCH p=(a)-[*1..3]-(b) WHERE a.name='pine wilt disease' RETURN p")
