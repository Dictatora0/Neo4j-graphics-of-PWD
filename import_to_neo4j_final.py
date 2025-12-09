#!/usr/bin/env python3
"""Neo4j 图谱导入脚本

用于将上游清洗好的三元组(节点1、关系、节点2、权重等)批量导入本地 Neo4j 数据库,
并在导入过程中补充节点/关系样式、索引和统计信息, 方便后续在 Neo4j Browser 中进行
可视化浏览和交互式查询。

整体执行顺序:

1. **读取三元组 CSV**
   - 优先读取 `output/triples_export_semantic_clean.csv`(已做语义清洗);
   - 若该文件不存在, 回退到 `output/triples_export.csv` 原始三元组;
   - 打印总行数、关系类型数、唯一节点数等基础统计。

2. **连接 Neo4j 数据库**
   - 使用 `NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD` 建立驱动和会话;
   - 后续所有 Cypher 语句都在同一个 `session` 中按步骤顺序执行。

3. **步骤1: 清空现有图数据**
   - 执行 `MATCH (n) DETACH DELETE n`, 删除所有节点和关系;
   - 适用于“每次导入前都重建一张干净的新图”的场景。

4. **步骤2: 创建节点并应用样式**
   - 先根据三元组中的 `node_1/node_2` 计算所有唯一节点集合;
   - 对每个节点按以下优先级确定类型和样式:
     1) 如在 `node_styles` 中有手工配置, 直接使用预设 `type/color/icon`;
     2) 否则根据节点名称中的关键词(病/线虫/天牛/松/城市名等)自动推断类型,
        并从 `default_styles` 中选取默认颜色和图标;
   - 为每个节点创建一个带标签的节点(如 `:Pathogen`, `:Host`), 并写入:
     `name/type/color/icon/created_at/display_name` 等属性。

5. **步骤3: 创建关系并应用样式**
   - 遍历三元组表中每一行, 读取 `node_1/node_2/relationship/weight`;
   - 从 `relation_styles` 中按关系类型(如 INFECTS/CAUSES/CONTROLS 等)选择颜色/线宽/样式/中文标签;
   - 未配置的关系类型统一使用灰色虚线 `default_relation_style`;
   - 执行 `MATCH ... CREATE (s)-[r:RELTYPE {...}]->(t)` 创建加权有向边, 写入 `weight/color/style/label/created_at`。

6. **步骤4: 创建索引**
   - 预创建常用查询字段索引, 如 `n.name`、`n.type`、`r.weight`;
   - 目的是加快前端可视化加载和交互式查询的响应速度。

7. **步骤5: 添加统计信息**
   - 通过 Cypher 计算每个节点的出度、入度与总度数, 写回 `out_degree/in_degree/total_degree` 属性;
   - 统计不同关系类型的权重均值/最大值/最小值, 用于后续分析和调参。

8. **步骤6: 最终验证与汇总输出**
   - 统计图中节点数、关系数, 以及节点/关系类型分布和度数最高的节点;
   - 在控制台打印导入概览、常用查询示例和 Neo4j Browser 访问方式, 方便人工快速验证导入结果。

脚本设计为“一次性运行”的导入工具: 从读取 CSV 到关闭驱动, 按照上述步骤线性执行,
便于理解和在调试时逐步注释/放开某些阶段。
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
    
    # 层级本体定义：定义每个类型的父类关系
    # 格式: {'Type': ['ParentType1', 'ParentType2', ...]}
    # 例如: Pathogen 继承自 Organism, Host 继承自 Plant 和 Organism
    type_hierarchy = {
        'Pathogen': ['Organism', 'Concept'],
        'Disease': ['Condition', 'Concept'],
        'Vector': ['Insect', 'Animal', 'Organism', 'Concept'],
        'Host': ['Plant', 'Organism', 'Concept'],
        'Location': ['GeographicEntity', 'Concept'],
        'Technology': ['Method', 'Concept'],
        'Control': ['Treatment', 'Method', 'Concept'],
        'Environment': ['Factor', 'Concept'],
        'Other': ['Concept'],
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
        'Environment': {'color': '#87CEEB', 'size': 'medium', 'icon': 'ENVIRONMENT'},
        'Other': {'color': '#C7CEEA', 'size': 'small', 'icon': 'OTHER'},
    }
    
    # 获取所有唯一节点
    all_nodes = set(df['node_1'].unique()) | set(df['node_2'].unique())
    
    created_nodes = 0
    for node in all_nodes:
        # 确定节点类型和样式: 先查是否有手工定义的样式,否则按名称规则自动推断
        if node in node_styles:
            style = node_styles[node]
            node_type = style['type']
            color = style['color']
            icon = style['icon']
        else:
            # 根据节点名称推断类型（支持中英文）
            node_lower = node.lower()
            
            # 疾病（Disease）- 优先检查，因为"松材线虫病"应该是Disease不是Pathogen
            if any(x in node for x in ['病', 'disease', 'wilt', '萎蔫', '枯死', '疫情']):
                node_type = 'Disease'
                style = default_styles['Disease']
            # 病原体（Pathogen）- 纯"线虫"才是病原体
            elif any(x in node for x in ['线虫', 'nematode', 'xylophilus', 'bursaphelenchus']) and '病' not in node:
                node_type = 'Pathogen'
                style = default_styles['Pathogen']
            # 媒介昆虫（Vector）
            elif any(x in node for x in ['天牛', 'monochamus', 'arhopalus', 'beetle', '墨天牛']):
                node_type = 'Vector'
                style = default_styles['Vector']
            # 寄主植物（Host）- 排除线虫和天牛
            elif any(x in node for x in ['松', 'pine', 'pinus', 'forest', 'tree', '林']) and '线虫' not in node and '天牛' not in node:
                node_type = 'Host'
                style = default_styles['Host']
            # 防治方法（Control）
            elif any(x in node for x in ['防治', '防控', 'control', 'trap', 'biological', '诱捕', '药剂']):
                node_type = 'Control'
                style = default_styles['Control']
            # 技术方法（Technology）
            elif any(x in node_lower for x in ['sentinel', 'spectral', 'hyperspectral', 'algorithm', '遥感', '光谱', '监测']):
                node_type = 'Technology'
                style = default_styles['Technology']
            # 地点（Location）- 排除已分类的节点
            elif any(x in node for x in ['市', '省', '县', '区', '林场', 'area', 'region', 'province', 'mountain', 'peak']) and '病' not in node:
                node_type = 'Location'
                style = default_styles['Location']
            # 环境因子（Environment）
            elif any(x in node for x in ['气候', '温度', '湿度', '降雨', '土壤', '环境', 'climate', 'temperature', 'humidity']):
                node_type = 'Environment'
                style = default_styles.get('Environment', default_styles['Other'])
            else:
                node_type = 'Other'
                style = default_styles['Other']
            
            color = style['color']
            icon = style.get('icon', '')
        
        # 构建层级 Label 字符串
        # 例如: Pathogen 节点将有 :Pathogen:Organism:Concept 三个 Label
        labels = [node_type]
        if node_type in type_hierarchy:
            labels.extend(type_hierarchy[node_type])
        
        # 去重并保持顺序（具体类型在前，抽象类型在后）
        seen = set()
        unique_labels = []
        for label in labels:
            if label not in seen:
                seen.add(label)
                unique_labels.append(label)
        
        labels_str = ':'.join(unique_labels)
        
        # 创建节点（带层级 Label）
        session.run(f"""
            CREATE (n:{labels_str} {{
                name: $name,
                type: $type,
                primary_label: $primary_label,
                all_labels: $all_labels,
                color: $color,
                icon: $icon,
                created_at: $timestamp,
                display_name: $display_name
            }})
        """, 
        name=node,
        type=node_type,
        primary_label=node_type,
        all_labels=unique_labels,
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
        
        # 获取关系样式: 未在字典中出现的关系类型统一走默认灰色虚线
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
    
    # 为常用查询字段预创建索引,加快交互式探索和可视化加载速度
    index_queries = [
        "CREATE INDEX node_name IF NOT EXISTS FOR (n) ON (n.name)",
        "CREATE INDEX node_type IF NOT EXISTS FOR (n) ON (n.type)",
        "CREATE INDEX node_primary_label IF NOT EXISTS FOR (n) ON (n.primary_label)",
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
    
    # 计算节点重要性（基于度数）
    session.run("""
        MATCH (n)
        WITH n, n.total_degree as degree
        SET n.importance = CASE
            WHEN degree >= 30 THEN 5
            WHEN degree >= 20 THEN 4
            WHEN degree >= 10 THEN 3
            WHEN degree >= 5 THEN 2
            ELSE 1
        END
    """)
    
    print("  已计算节点重要性")
    
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
    
    # 显示重要性分布
    result = session.run("""
        MATCH (n)
        WHERE n.importance IS NOT NULL
        RETURN n.importance as importance, count(*) as count
        ORDER BY importance DESC
    """)
    
    print(f"\n  节点重要性分布:")
    for record in result:
        importance = record['importance']
        count = record['count']
        print(f"    {importance}星: {count:3d}")
    
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
print("\n层级本体查询示例:")
print("  查询所有生物: MATCH (n:Organism) RETURN n")
print("  查询所有植物: MATCH (n:Plant) RETURN n")
print("  查询所有动物: MATCH (n:Animal) RETURN n")
print("  查询所有防治方法: MATCH (n:Treatment) RETURN n")

print("\n访问 Neo4j Browser:")
print("  URL: http://localhost:7474")
print("  用户名: neo4j")
print("  密码: 12345678")

print("\n使用建议:")
print("  1. 在 Neo4j Browser 中运行查询查看可视化")
print("  2. 使用 MATCH (n) RETURN n LIMIT 25 查看节点")
print("  3. 使用 MATCH p=()-[r]->() RETURN p LIMIT 25 查看关系")
print("  4. 尝试路径查询: MATCH p=(a)-[*1..3]-(b) WHERE a.name='pine wilt disease' RETURN p")
print("  5. 利用层级本体: MATCH (o:Organism)-[r]->(h:Host) RETURN o, r, h")
print("  6. 查询节点的所有 Label: MATCH (n) RETURN n.name, labels(n) LIMIT 10")
