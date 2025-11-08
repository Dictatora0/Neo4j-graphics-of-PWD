#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据修正和导入脚本
修正实体和关系中的问题，然后导入到 Neo4j
"""

import pandas as pd
import re
from collections import defaultdict

def fix_entities(entities_df):
    """修正实体数据"""
    print("="*60)
    print("开始修正实体数据...")
    print("="*60)
    
    original_count = len(entities_df)
    
    # 1. 删除无效实体
    invalid_patterns = [
        r'^(for|with|and|the|of|in|to|from)\s',  # 以介词开头
        r'^\d+\s',  # 以数字开头
        r'^[A-Z]{1,2}$',  # 单个或两个大写字母
        r'.*\d{4}.*\d{4}',  # 包含多个年份
        r'^(words|affecting|during|博村林场)',  # 特定无效词
    ]
    
    for pattern in invalid_patterns:
        mask = entities_df['name'].str.contains(pattern, regex=True, case=False, na=False)
        removed = entities_df[mask]
        if len(removed) > 0:
            print(f"  删除匹配 '{pattern}' 的实体: {len(removed)} 个")
        entities_df = entities_df[~mask]
    
    # 2. 删除过长实体（>40字符）
    long_entities = entities_df[entities_df['name'].str.len() > 40]
    if len(long_entities) > 0:
        print(f"  删除过长实体（>40字符）: {len(long_entities)} 个")
        entities_df = entities_df[entities_df['name'].str.len() <= 40]
    
    # 3. 删除过短实体（<2字符）
    short_entities = entities_df[entities_df['name'].str.len() < 2]
    if len(short_entities) > 0:
        print(f"  删除过短实体（<2字符）: {len(short_entities)} 个")
        entities_df = entities_df[entities_df['name'].str.len() >= 2]
    
    # 4. 合并同义词和不完整实体
    entity_mapping = {
        # Disease 合并
        '松材': '松材线虫病',
        '松材线': '松材线虫病',
        '线虫病': '松材线虫病',
        'pine wilt': 'pine wilt disease',
        'PWD': 'pine wilt disease',
        'the pine wilt': 'pine wilt disease',
        'the PWD': 'pine wilt disease',
        'the PWD epidemic': 'pine wilt disease',
        'PWD during the': 'pine wilt disease',
        'affecting the PWD': 'pine wilt disease',
        'cold stress 泰山松材线虫病': '松材线虫病',
        
        # Pathogen 合并
        '松褐天': '松褐天牛',
        'pine wood nematode': '松材线虫',
        
        # Vector 合并
        '松墨天': '松褐天牛',
        'Monochamus alternatus Hope': 'Monochamus alternatus',
        
        # Host 规范化
        'pine samples using': '松树',
        'pine spectral': '松树',
        'with pine': '松树',
    }
    
    # 应用映射
    entities_df['name'] = entities_df['name'].replace(entity_mapping)
    
    # 5. 去除重复（保留第一次出现）
    before_dedup = len(entities_df)
    entities_df = entities_df.drop_duplicates(subset=['name'], keep='first')
    print(f"  去重: {before_dedup - len(entities_df)} 个重复实体")
    
    # 6. 修正错误分类
    # Pine 应该是 Host 而不是 Disease
    entities_df.loc[(entities_df['name'] == 'Pine') & (entities_df['type'] == 'Disease'), 'type'] = 'Host'
    entities_df.loc[(entities_df['name'] == 'Pinus') & (entities_df['type'] == 'Disease'), 'type'] = 'Host'
    
    # 7. 重新分配 ID
    entities_df = entities_df.reset_index(drop=True)
    entities_df['id'] = range(1, len(entities_df) + 1)
    
    print(f"\n实体修正完成:")
    print(f"  原始数量: {original_count}")
    print(f"  修正后数量: {len(entities_df)}")
    print(f"  删除比例: {(original_count - len(entities_df)) / original_count * 100:.1f}%")
    print()
    
    return entities_df


def fix_relations(relations_df, entities_df):
    """修正关系数据"""
    print("="*60)
    print("开始修正关系数据...")
    print("="*60)
    
    original_count = len(relations_df)
    
    # 创建实体名称到 ID 的映射
    valid_entities = set(entities_df['name'].unique())
    
    # 应用与实体相同的合并映射
    entity_mapping = {
        '松材': '松材线虫病',
        '松材线': '松材线虫病',
        '线虫病': '松材线虫病',
        'pine wilt': 'pine wilt disease',
        'PWD': 'pine wilt disease',
        'the pine wilt': 'pine wilt disease',
        'the PWD': 'pine wilt disease',
        '松褐天': '松褐天牛',
        '松墨天': '松褐天牛',
        'pine wood nematode': '松材线虫',
        'with pine': '松树',
        'pine samples using': '松树',
    }
    
    relations_df['head'] = relations_df['head'].replace(entity_mapping)
    relations_df['tail'] = relations_df['tail'].replace(entity_mapping)
    
    # 1. 删除 head 或 tail 不在有效实体中的关系
    before_filter = len(relations_df)
    relations_df = relations_df[
        relations_df['head'].isin(valid_entities) & 
        relations_df['tail'].isin(valid_entities)
    ]
    print(f"  删除无效关系: {before_filter - len(relations_df)} 个")
    
    # 2. 删除自环关系
    self_loops = relations_df[relations_df['head'] == relations_df['tail']]
    if len(self_loops) > 0:
        print(f"  删除自环关系: {len(self_loops)} 个")
        relations_df = relations_df[relations_df['head'] != relations_df['tail']]
    
    # 3. 去除完全重复的关系（保留置信度最高的）
    before_dedup = len(relations_df)
    relations_df = relations_df.sort_values('confidence', ascending=False)
    relations_df = relations_df.drop_duplicates(subset=['head', 'relation', 'tail'], keep='first')
    print(f"  去重: {before_dedup - len(relations_df)} 个重复关系")
    
    # 4. 只保留置信度 >= 0.65 的关系
    before_threshold = len(relations_df)
    relations_df = relations_df[relations_df['confidence'] >= 0.65]
    print(f"  置信度过滤(<0.65): {before_threshold - len(relations_df)} 个")
    
    print(f"\n关系修正完成:")
    print(f"  原始数量: {original_count}")
    print(f"  修正后数量: {len(relations_df)}")
    print(f"  删除比例: {(original_count - len(relations_df)) / original_count * 100:.1f}%")
    print()
    
    return relations_df


def generate_neo4j_files(entities_df, relations_df, output_dir='output/neo4j_import'):
    """生成 Neo4j 导入文件"""
    print("="*60)
    print("生成 Neo4j 导入文件...")
    print("="*60)
    
    # 1. 生成 nodes.csv
    nodes_df = entities_df[['id', 'name', 'type']].copy()
    nodes_df.columns = ['id', 'name', 'label']
    nodes_path = f'{output_dir}/nodes.csv'
    nodes_df.to_csv(nodes_path, index=False, encoding='utf-8')
    print(f"  ✓ 节点文件: {nodes_path} ({len(nodes_df)} 个节点)")
    
    # 2. 生成 relations.csv
    entity_name_to_id = dict(zip(entities_df['name'], entities_df['id']))
    relations_neo4j = relations_df.copy()
    relations_neo4j['start_id'] = relations_neo4j['head'].map(entity_name_to_id)
    relations_neo4j['end_id'] = relations_neo4j['tail'].map(entity_name_to_id)
    relations_neo4j = relations_neo4j[['start_id', 'relation', 'end_id', 'confidence']]
    relations_path = f'{output_dir}/relations.csv'
    relations_neo4j.to_csv(relations_path, index=False, encoding='utf-8')
    print(f"  ✓ 关系文件: {relations_path} ({len(relations_neo4j)} 条关系)")
    
    # 3. 生成统计信息
    print(f"\n  实体类型分布:")
    entity_counts = entities_df['type'].value_counts()
    for entity_type, count in entity_counts.items():
        print(f"    - {entity_type}: {count} ({count/len(entities_df)*100:.1f}%)")
    
    print(f"\n  关系类型分布:")
    relation_counts = relations_df['relation'].value_counts()
    for relation_type, count in relation_counts.items():
        print(f"    - {relation_type}: {count} ({count/len(relations_df)*100:.1f}%)")
    
    print()


def import_to_neo4j(uri='neo4j://127.0.0.1:7687', user='neo4j', password='12345678'):
    """导入数据到 Neo4j"""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("警告: neo4j 驱动未安装，跳过自动导入")
        print("请手动执行: pip install neo4j")
        return False
    
    print("="*60)
    print("开始导入数据到 Neo4j...")
    print("="*60)
    print(f"连接: {uri}")
    print(f"用户: {user}\n")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        # 读取文件
        nodes_df = pd.read_csv('output/neo4j_import/nodes.csv')
        relations_df = pd.read_csv('output/neo4j_import/relations.csv')
        
        with driver.session() as session:
            # 清空数据库
            print("清空现有数据...")
            session.run("MATCH (n) DETACH DELETE n")
            
            # 导入节点
            print(f"导入 {len(nodes_df)} 个节点...")
            for _, row in nodes_df.iterrows():
                query = f"""
                CREATE (n:{row['label']})
                SET n.id = $id, n.name = $name
                """
                session.run(query, id=int(row['id']), name=row['name'])
            print("  ✓ 节点导入完成")
            
            # 导入关系
            print(f"导入 {len(relations_df)} 条关系...")
            for _, row in relations_df.iterrows():
                query = f"""
                MATCH (a {{id: $start_id}})
                MATCH (b {{id: $end_id}})
                CREATE (a)-[r:{row['relation']}]->(b)
                SET r.confidence = $confidence
                """
                session.run(
                    query,
                    start_id=int(row['start_id']),
                    end_id=int(row['end_id']),
                    confidence=float(row['confidence'])
                )
            print("  ✓ 关系导入完成")
        
        driver.close()
        print("\n导入成功！")
        print(f"请访问 Neo4j Browser 查看: http://localhost:7474")
        return True
        
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        print("\n建议:")
        print("1. 确认 Neo4j 已启动: neo4j status")
        print("2. 确认连接信息正确")
        print("3. 手动在 Neo4j Browser 中执行 import.cypher")
        return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("松材线虫病知识图谱 - 数据修正与导入")
    print("="*60 + "\n")
    
    # 1. 读取原始数据
    print("读取原始数据...")
    entities_df = pd.read_csv('output/entities_clean.csv')
    relations_df = pd.read_csv('output/relations_clean.csv')
    print(f"  实体: {len(entities_df)} 个")
    print(f"  关系: {len(relations_df)} 条\n")
    
    # 2. 修正实体
    entities_fixed = fix_entities(entities_df)
    
    # 3. 修正关系
    relations_fixed = fix_relations(relations_df, entities_fixed)
    
    # 4. 保存修正后的数据
    entities_fixed.to_csv('output/entities_fixed.csv', index=False, encoding='utf-8')
    relations_fixed.to_csv('output/relations_fixed.csv', index=False, encoding='utf-8')
    print("修正后的数据已保存:")
    print("  - output/entities_fixed.csv")
    print("  - output/relations_fixed.csv\n")
    
    # 5. 生成 Neo4j 导入文件
    generate_neo4j_files(entities_fixed, relations_fixed)
    
    # 6. 尝试导入到 Neo4j
    import_choice = input("\n是否立即导入到 Neo4j? (y/n): ").strip().lower()
    if import_choice == 'y':
        import_to_neo4j()
    else:
        print("\n跳过自动导入。")
        print("可以手动导入:")
        print("  python output/neo4j_import/import_to_neo4j.py")
    
    print("\n" + "="*60)
    print("处理完成！")
    print("="*60)


if __name__ == '__main__':
    main()

