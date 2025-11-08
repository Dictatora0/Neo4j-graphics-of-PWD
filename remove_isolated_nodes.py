#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除孤立节点并重新生成CSV文件
"""

import pandas as pd
from neo4j import GraphDatabase

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"


def remove_isolated_from_neo4j():
    """从Neo4j删除孤立节点"""
    print("="*60)
    print("从 Neo4j 删除孤立节点")
    print("="*60)
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # 查询孤立节点
            result = session.run("""
                MATCH (n) 
                WHERE NOT (n)-[]-() 
                RETURN labels(n)[0] as type, count(n) as count
            """)
            
            print("\n孤立节点统计:")
            total = 0
            for record in result:
                print(f"  {record['type']}: {record['count']} 个")
                total += record['count']
            
            print(f"\n总计: {total} 个孤立节点")
            
            if total > 0:
                confirm = input("\n是否删除这些孤立节点? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    result = session.run("MATCH (n) WHERE NOT (n)-[]-() DETACH DELETE n")
                    print(f"✓ 已删除 {total} 个孤立节点")
                    
                    # 验证删除结果
                    result = session.run("MATCH (n) RETURN count(n) as count")
                    remaining = result.single()['count']
                    print(f"✓ 剩余节点: {remaining} 个")
                    
                    # 显示剩余节点统计
                    result = session.run("MATCH (n) RETURN labels(n)[0] as type, count(n) as count")
                    print("\n剩余节点分布:")
                    for record in result:
                        print(f"  {record['type']}: {record['count']} 个")
                    
                    return True
                else:
                    print("取消删除")
                    return False
            else:
                print("✓ 没有孤立节点")
                return False
    
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        return False
    finally:
        driver.close()


def export_from_neo4j():
    """从Neo4j导出当前数据到CSV"""
    print("\n" + "="*60)
    print("从 Neo4j 导出数据")
    print("="*60)
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # 导出节点
            result = session.run("""
                MATCH (n)
                RETURN id(n) as id, labels(n)[0] as label, n.name as name
                ORDER BY id
            """)
            
            nodes_data = []
            id_mapping = {}  # Neo4j内部ID到新ID的映射
            
            for new_id, record in enumerate(result, 1):
                nodes_data.append({
                    'id': new_id,
                    'name': record['name'],
                    'label': record['label']
                })
                id_mapping[record['id']] = new_id
            
            nodes_df = pd.DataFrame(nodes_data)
            print(f"\n导出节点: {len(nodes_df)} 个")
            
            # 导出关系
            result = session.run("""
                MATCH (a)-[r]->(b)
                RETURN id(a) as start_id, type(r) as relation, 
                       id(b) as end_id, r.confidence as confidence
            """)
            
            relations_data = []
            for record in result:
                relations_data.append({
                    'start_id': id_mapping[record['start_id']],
                    'relation': record['relation'],
                    'end_id': id_mapping[record['end_id']],
                    'confidence': record['confidence'] if record['confidence'] else 0.7
                })
            
            relations_df = pd.DataFrame(relations_data)
            print(f"导出关系: {len(relations_df)} 条")
            
            # 保存到CSV
            nodes_df.to_csv('output/neo4j_import/nodes.csv', index=False, encoding='utf-8')
            relations_df.to_csv('output/neo4j_import/relations.csv', index=False, encoding='utf-8')
            
            print("\n✓ 已保存到:")
            print("  - output/neo4j_import/nodes.csv")
            print("  - output/neo4j_import/relations.csv")
            
            return nodes_df, relations_df
    
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        return None, None
    finally:
        driver.close()


def display_final_stats(nodes_df, relations_df):
    """显示最终统计"""
    print("\n" + "="*60)
    print("最终数据统计")
    print("="*60)
    
    print(f"\n总节点: {len(nodes_df)}")
    print(f"总关系: {len(relations_df)}")
    
    print("\n节点类型分布:")
    for label, count in nodes_df['label'].value_counts().items():
        pct = count / len(nodes_df) * 100
        print(f"  {label}: {count} ({pct:.1f}%)")
    
    print("\n关系类型分布:")
    for rel, count in relations_df['relation'].value_counts().items():
        pct = count / len(relations_df) * 100
        print(f"  {rel}: {count} ({pct:.1f}%)")
    
    # 显示每种类型的实体
    print("\n" + "="*60)
    print("实体列表")
    print("="*60)
    
    for label in sorted(nodes_df['label'].unique()):
        entities = sorted(nodes_df[nodes_df['label'] == label]['name'].tolist())
        print(f"\n{label} ({len(entities)} 个):")
        for entity in entities:
            print(f"  - {entity}")


def main():
    print("\n" + "="*60)
    print("删除孤立节点工具")
    print("="*60)
    
    # 1. 从Neo4j删除孤立节点
    deleted = remove_isolated_from_neo4j()
    
    if deleted:
        # 2. 从Neo4j导出清理后的数据
        nodes_df, relations_df = export_from_neo4j()
        
        if nodes_df is not None and relations_df is not None:
            # 3. 显示最终统计
            display_final_stats(nodes_df, relations_df)
            
            print("\n" + "="*60)
            print("✅ 完成！数据已更新")
            print("="*60)
            print("\n数据库已清理完毕，所有孤立节点已删除")
            print("访问 Neo4j Browser 验证: http://localhost:7474")
    else:
        print("\n未进行任何更改")


if __name__ == '__main__':
    main()

