#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恢复重要的Host实体并建立关系
"""

import pandas as pd
from neo4j import GraphDatabase

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"


def restore_hosts():
    """恢复Host实体并建立关系"""
    print("="*60)
    print("恢复Host实体")
    print("="*60)
    
    # 读取当前节点
    nodes = pd.read_csv('output/neo4j_import/nodes.csv')
    print(f"\n当前节点数: {len(nodes)}")
    
    # 松材线虫病的重要宿主植物（根据domain_dict.json）
    important_hosts = [
        '马尾松',      # Pinus massoniana - 最重要的宿主
        '黑松',        # Pinus thunbergii
        '赤松',        # Pinus densiflora
        '油松',        # Pinus tabuliformis
        '湿地松',      # Pinus elliottii
        '华山松',      # Pinus armandii
        '云南松',      # Pinus yunnanensis (已有)
        '思茅松',      # Pinus kesiya
        '日本黑松',    # Pinus thunbergii (已有)
        '樟子松',      # Pinus sylvestris var. mongolica (已有)
        '白皮松',      # Pinus bungeana (已有)
        '红松',        # Pinus koraiensis
        '火炬松',      # Pinus taeda
    ]
    
    # 检查哪些Host已经存在
    existing_hosts = set(nodes[nodes['label'] == 'Host']['name'].tolist())
    print(f"\n已有Host: {sorted(existing_hosts)}")
    
    # 找出需要添加的Host
    hosts_to_add = [h for h in important_hosts if h not in existing_hosts]
    print(f"\n需要添加的Host ({len(hosts_to_add)} 个):")
    for h in hosts_to_add:
        print(f"  - {h}")
    
    if not hosts_to_add:
        print("\n✓ 所有重要Host都已存在")
        return nodes, None
    
    # 添加新的Host实体
    max_id = nodes['id'].max()
    new_hosts = []
    for i, host_name in enumerate(hosts_to_add, 1):
        new_hosts.append({
            'id': max_id + i,
            'name': host_name,
            'label': 'Host'
        })
    
    new_hosts_df = pd.DataFrame(new_hosts)
    nodes_updated = pd.concat([nodes, new_hosts_df], ignore_index=True)
    
    print(f"\n✓ 已添加 {len(hosts_to_add)} 个Host实体")
    print(f"  更新后节点数: {len(nodes_updated)}")
    
    return nodes_updated, new_hosts_df


def create_host_relations(nodes_df, new_hosts_df):
    """为Host实体创建与松材线虫病的关系"""
    print("\n" + "="*60)
    print("创建Host关系")
    print("="*60)
    
    # 读取当前关系
    relations = pd.read_csv('output/neo4j_import/relations.csv')
    print(f"\n当前关系数: {len(relations)}")
    
    # 找到松材线虫病的ID
    disease_id = nodes_df[nodes_df['name'] == '松材线虫病']['id'].values[0]
    print(f"\n松材线虫病 ID: {disease_id}")
    
    # 获取所有Host的ID（包括新添加的）
    all_hosts = nodes_df[nodes_df['label'] == 'Host']
    print(f"\n所有Host实体 ({len(all_hosts)} 个):")
    for _, row in all_hosts.iterrows():
        print(f"  ID {row['id']}: {row['name']}")
    
    # 检查哪些Host已经有关系
    existing_host_ids = set(relations[relations['start_id'] == disease_id]['end_id'].tolist())
    host_ids_with_relation = set(all_hosts[all_hosts['id'].isin(existing_host_ids)]['id'].tolist())
    
    # 找出需要创建关系的Host
    all_host_ids = set(all_hosts['id'].tolist())
    hosts_needing_relation = all_host_ids - host_ids_with_relation
    
    if not hosts_needing_relation:
        print("\n✓ 所有Host都已有关联关系")
        return relations
    
    # 创建新的hasHost关系
    new_relations = []
    max_rel_id = relations.index.max() + 1 if len(relations) > 0 else 1
    
    for host_id in hosts_needing_relation:
        host_name = all_hosts[all_hosts['id'] == host_id]['name'].values[0]
        new_relations.append({
            'start_id': disease_id,
            'relation': 'hasHost',
            'end_id': host_id,
            'confidence': 0.8  # 高置信度，因为这些都是已知的宿主
        })
        print(f"  创建关系: 松材线虫病 --[hasHost]--> {host_name} (ID: {host_id})")
    
    new_relations_df = pd.DataFrame(new_relations)
    relations_updated = pd.concat([relations, new_relations_df], ignore_index=True)
    
    print(f"\n✓ 已创建 {len(new_relations)} 条hasHost关系")
    print(f"  更新后关系数: {len(relations_updated)}")
    
    return relations_updated


def import_to_neo4j(nodes_df, relations_df):
    """导入到Neo4j"""
    print("\n" + "="*60)
    print("导入到Neo4j")
    print("="*60)
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # 清空现有数据
            print("\n清空现有数据...")
            session.run("MATCH (n) DETACH DELETE n")
            print("  ✓")
            
            # 创建索引
            print("\n创建索引...")
            for label in nodes_df['label'].unique():
                session.run(f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n.id)")
            print("  ✓")
            
            # 导入节点
            print(f"\n导入节点 ({len(nodes_df)} 个)...")
            for _, row in nodes_df.iterrows():
                query = f"CREATE (n:{row['label']}) SET n.id = $id, n.name = $name"
                session.run(query, id=int(row['id']), name=row['name'])
            print("  ✓")
            
            # 导入关系
            print(f"\n导入关系 ({len(relations_df)} 条)...")
            for _, row in relations_df.iterrows():
                query = f"""
                MATCH (a {{id: $start_id}})
                MATCH (b {{id: $end_id}})
                CREATE (a)-[r:{row['relation']}]->(b)
                SET r.confidence = $confidence
                """
                session.run(query,
                          start_id=int(row['start_id']),
                          end_id=int(row['end_id']),
                          confidence=float(row['confidence']))
            print("  ✓")
            
            # 验证
            print("\n验证结果:")
            result = session.run("MATCH (n) RETURN labels(n)[0] as type, count(n) as count")
            print("  节点统计:")
            for record in result:
                print(f"    {record['type']}: {record['count']}")
            
            result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
            print("\n  关系统计:")
            for record in result:
                print(f"    {record['type']}: {record['count']}")
            
            # 验证松材线虫病的Host关系
            result = session.run("""
                MATCH (d:Disease {name: '松材线虫病'})-[r:hasHost]->(h:Host)
                RETURN h.name as host, count(r) as count
                ORDER BY h.name
            """)
            print("\n  松材线虫病的Host:")
            for record in result:
                print(f"    - {record['host']}")
        
        driver.close()
        return True
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        driver.close()
        return False


def main():
    print("\n" + "="*60)
    print("恢复Host实体工具")
    print("="*60)
    
    # 1. 恢复Host实体
    nodes_updated, new_hosts_df = restore_hosts()
    
    if new_hosts_df is None or len(new_hosts_df) == 0:
        print("\n无需添加新Host，检查关系...")
        nodes_updated = pd.read_csv('output/neo4j_import/nodes.csv')
    
    # 2. 创建关系
    relations_updated = create_host_relations(nodes_updated, new_hosts_df)
    
    # 3. 保存更新后的文件
    print("\n" + "="*60)
    print("保存更新后的文件")
    print("="*60)
    
    nodes_updated.to_csv('output/neo4j_import/nodes.csv', index=False, encoding='utf-8')
    relations_updated.to_csv('output/neo4j_import/relations.csv', index=False, encoding='utf-8')
    
    print("\n✓ 已保存:")
    print("  - output/neo4j_import/nodes.csv")
    print("  - output/neo4j_import/relations.csv")
    
    # 4. 显示最终统计
    print("\n" + "="*60)
    print("最终数据统计")
    print("="*60)
    
    print(f"\n总节点: {len(nodes_updated)}")
    print(f"总关系: {len(relations_updated)}")
    
    print("\n节点类型分布:")
    for label, count in nodes_updated['label'].value_counts().items():
        pct = count / len(nodes_updated) * 100
        print(f"  {label}: {count} ({pct:.1f}%)")
    
    print("\n关系类型分布:")
    for rel, count in relations_updated['relation'].value_counts().items():
        pct = count / len(relations_updated) * 100
        print(f"  {rel}: {count} ({pct:.1f}%)")
    
    # 5. 导入到Neo4j
    print("\n" + "="*60)
    confirm = input("\n是否导入到Neo4j? (yes/no): ").strip().lower()
    if confirm == 'yes':
        success = import_to_neo4j(nodes_updated, relations_updated)
        if success:
            print("\n" + "="*60)
            print("✅ 完成！Host实体已恢复")
            print("="*60)
            print("\n访问: http://localhost:7474")
            print("\n推荐查询:")
            print("  MATCH (d:Disease {name: '松材线虫病'})-[r:hasHost]->(h:Host)")
            print("  RETURN d, r, h")


if __name__ == '__main__':
    main()

