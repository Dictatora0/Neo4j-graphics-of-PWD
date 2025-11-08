#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正关系类型错误
"""

import pandas as pd
from neo4j import GraphDatabase

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"


def fix_relations():
    """修正关系类型"""
    print("="*60)
    print("修正关系类型")
    print("="*60)
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # 1. 修正 Disease → EnvironmentalFactor 的关系（从 hasPathogen 改为 affectedBy）
            print("\n1. 修正 Disease → EnvironmentalFactor 关系...")
            result = session.run("""
                MATCH (d:Disease)-[r:hasPathogen]->(e:EnvironmentalFactor)
                RETURN count(r) AS count
            """)
            count = result.single()['count']
            print(f"   发现 {count} 条错误关系")
            
            if count > 0:
                session.run("""
                    MATCH (d:Disease)-[r:hasPathogen]->(e:EnvironmentalFactor)
                    CREATE (d)-[r2:affectedBy]->(e)
                    SET r2.confidence = r.confidence
                    DELETE r
                """)
                print(f"   ✓ 已修正 {count} 条关系（hasPathogen → affectedBy）")
            
            # 2. 修正 Disease → Vector 的关系（从 hasPathogen 改为 hasVector）
            print("\n2. 修正 Disease → Vector 关系...")
            result = session.run("""
                MATCH (d:Disease)-[r:hasPathogen]->(v:Vector)
                RETURN count(r) AS count
            """)
            count = result.single()['count']
            print(f"   发现 {count} 条错误关系")
            
            if count > 0:
                session.run("""
                    MATCH (d:Disease)-[r:hasPathogen]->(v:Vector)
                    CREATE (d)-[r2:hasVector]->(v)
                    SET r2.confidence = r.confidence
                    DELETE r
                """)
                print(f"   ✓ 已修正 {count} 条关系（hasPathogen → hasVector）")
            
            # 3. 确保 Disease → Pathogen 的关系是 hasPathogen
            print("\n3. 检查 Disease → Pathogen 关系...")
            result = session.run("""
                MATCH (d:Disease)-[r]->(p:Pathogen)
                RETURN type(r) AS relType, count(r) AS count
            """)
            for record in result:
                print(f"   {record['relType']}: {record['count']} 条")
            
            # 4. 为松材线虫病创建正确的 hasPathogen 关系
            print("\n4. 创建 Disease → Pathogen 关系...")
            
            # 检查松材线虫病和松材线虫是否存在
            result = session.run("""
                MATCH (d:Disease {name: '松材线虫病'})
                MATCH (p:Pathogen {name: '松材线虫'})
                RETURN d, p
            """)
            if result.single():
                # 检查是否已有关系
                result = session.run("""
                    MATCH (d:Disease {name: '松材线虫病'})-[r:hasPathogen]->(p:Pathogen {name: '松材线虫'})
                    RETURN count(r) AS count
                """)
                count = result.single()['count']
                
                if count == 0:
                    session.run("""
                        MATCH (d:Disease {name: '松材线虫病'})
                        MATCH (p:Pathogen {name: '松材线虫'})
                        CREATE (d)-[r:hasPathogen]->(p)
                        SET r.confidence = 0.95
                    """)
                    print("   ✓ 已创建：松材线虫病 --[hasPathogen]--> 松材线虫")
                else:
                    print("   ✓ 关系已存在")
            else:
                print("   ⚠️ 松材线虫病或松材线虫不存在")
            
            # 5. 验证修正结果
            print("\n" + "="*60)
            print("验证修正结果")
            print("="*60)
            
            result = session.run("""
                MATCH (d:Disease {name: '松材线虫病'})-[r]-(n)
                RETURN type(r) AS 关系类型, labels(n)[0] AS 目标类型, count(*) AS 数量
                ORDER BY type(r), labels(n)[0]
            """)
            
            print("\n松材线虫病的关系:")
            for record in result:
                print(f"  {record['关系类型']} → [{record['目标类型']}]: {record['数量']} 条")
        
        driver.close()
        return True
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        driver.close()
        return False


def update_csv_files():
    """更新CSV文件以反映修正后的关系"""
    print("\n" + "="*60)
    print("更新CSV文件")
    print("="*60)
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # 导出节点（使用n.id属性）
            result = session.run("""
                MATCH (n)
                RETURN n.id as id, labels(n)[0] as label, n.name as name
                ORDER BY n.id
            """)
            
            nodes_data = []
            id_mapping = {}  # 旧ID到新ID的映射
            
            for new_id, record in enumerate(result, 1):
                old_id = record['id']
                nodes_data.append({
                    'id': new_id,
                    'name': record['name'],
                    'label': record['label']
                })
                id_mapping[old_id] = new_id
            
            nodes_df = pd.DataFrame(nodes_data)
            print(f"\n导出节点: {len(nodes_df)} 个")
            
            # 导出关系（使用节点ID属性）
            result = session.run("""
                MATCH (a)-[r]->(b)
                RETURN a.id as start_id, type(r) as relation,
                       b.id as end_id, r.confidence as confidence
            """)
            
            relations_data = []
            for record in result:
                start_id = id_mapping.get(record['start_id'])
                end_id = id_mapping.get(record['end_id'])
                
                if start_id and end_id:
                    relations_data.append({
                        'start_id': start_id,
                        'relation': record['relation'],
                        'end_id': end_id,
                        'confidence': record['confidence'] if record['confidence'] else 0.7
                    })
            
            relations_df = pd.DataFrame(relations_data)
            print(f"导出关系: {len(relations_df)} 条")
            
            # 保存
            nodes_df.to_csv('output/neo4j_import/nodes.csv', index=False, encoding='utf-8')
            relations_df.to_csv('output/neo4j_import/relations.csv', index=False, encoding='utf-8')
            
            print("\n✓ 已保存:")
            print("  - output/neo4j_import/nodes.csv")
            print("  - output/neo4j_import/relations.csv")
            
            # 显示关系类型分布
            print("\n关系类型分布:")
            for rel, count in relations_df['relation'].value_counts().items():
                pct = count / len(relations_df) * 100
                print(f"  {rel}: {count} ({pct:.1f}%)")
    
    except Exception as e:
        print(f"\n✗ 错误: {e}")
    finally:
        driver.close()


def main():
    print("\n" + "="*60)
    print("修正关系类型工具")
    print("="*60)
    
    # 1. 修正关系
    success = fix_relations()
    
    if success:
        # 2. 更新CSV文件
        update_csv_files()
        
        print("\n" + "="*60)
        print("✅ 完成！关系类型已修正")
        print("="*60)
        print("\n现在可以执行传播链分析查询:")
        print("""
MATCH (d:Disease {name: '松材线虫病'})-[:hasPathogen]->(p:Pathogen)
MATCH (d)-[:hasVector]->(v:Vector)
MATCH (d)-[:hasHost]->(h:Host)
RETURN d.name AS 疾病, p.name AS 病原体, v.name AS 媒介, h.name AS 宿主
        """)


if __name__ == '__main__':
    main()

