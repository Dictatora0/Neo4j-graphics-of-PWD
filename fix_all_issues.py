#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复所有发现的问题
"""

from neo4j import GraphDatabase
import pandas as pd

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"


def fix_issues():
    """修复所有问题"""
    print("="*60)
    print("修复数据问题")
    print("="*60)
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # ============================================================
            # 1. 添加缺失的松褐天牛实体
            # ============================================================
            print("\n1. 添加缺失的松褐天牛实体...")
            
            result = session.run("""
                MATCH (v:Vector {name: '松褐天牛'})
                RETURN count(v) as count
            """)
            exists = result.single()['count'] > 0
            
            if not exists:
                # 获取最大ID
                result = session.run("MATCH (n) RETURN max(n.id) as max_id")
                max_id = result.single()['max_id'] or 0
                
                session.run("""
                    CREATE (v:Vector {id: $id, name: $name})
                """, id=max_id + 1, name='松褐天牛')
                print("  ✓ 已添加松褐天牛")
            else:
                print("  ✓ 松褐天牛已存在")
            
            # ============================================================
            # 2. 修正错误的关系类型
            # ============================================================
            print("\n2. 修正错误的关系类型...")
            
            # 2.1 Pathogen → EnvironmentalFactor (应该是 affectedBy)
            result = session.run("""
                MATCH (p:Pathogen)-[r:hasPathogen]->(e:EnvironmentalFactor)
                RETURN count(r) as count
            """)
            count = result.single()['count']
            if count > 0:
                session.run("""
                    MATCH (p:Pathogen)-[r:hasPathogen]->(e:EnvironmentalFactor)
                    CREATE (p)-[r2:affectedBy]->(e)
                    SET r2.confidence = r.confidence
                    DELETE r
                """)
                print(f"  ✓ 修正 Pathogen → EnvironmentalFactor: {count} 条 (hasPathogen → affectedBy)")
            
            # 2.2 Host → EnvironmentalFactor (应该是 affectedBy)
            result = session.run("""
                MATCH (h:Host)-[r:hasPathogen]->(e:EnvironmentalFactor)
                RETURN count(r) as count
            """)
            count = result.single()['count']
            if count > 0:
                session.run("""
                    MATCH (h:Host)-[r:hasPathogen]->(e:EnvironmentalFactor)
                    CREATE (h)-[r2:affectedBy]->(e)
                    SET r2.confidence = r.confidence
                    DELETE r
                """)
                print(f"  ✓ 修正 Host → EnvironmentalFactor: {count} 条 (hasPathogen → affectedBy)")
            
            # 2.3 Symptom → EnvironmentalFactor (应该是 affectedBy)
            result = session.run("""
                MATCH (s:Symptom)-[r:hasPathogen]->(e:EnvironmentalFactor)
                RETURN count(r) as count
            """)
            count = result.single()['count']
            if count > 0:
                session.run("""
                    MATCH (s:Symptom)-[r:hasPathogen]->(e:EnvironmentalFactor)
                    CREATE (s)-[r2:affectedBy]->(e)
                    SET r2.confidence = r.confidence
                    DELETE r
                """)
                print(f"  ✓ 修正 Symptom → EnvironmentalFactor: {count} 条 (hasPathogen → affectedBy)")
            
            # ============================================================
            # 3. 为松材线虫病添加hasSymptom关系
            # ============================================================
            print("\n3. 为松材线虫病添加hasSymptom关系...")
            
            result = session.run("""
                MATCH (d:Disease {name: '松材线虫病'})
                MATCH (s:Symptom {name: '枯死'})
                WHERE NOT (d)-[:hasSymptom]->(s)
                CREATE (d)-[r:hasSymptom]->(s)
                SET r.confidence = 0.9
                RETURN count(r) as count
            """)
            count = result.single()['count']
            if count > 0:
                print(f"  ✓ 已创建 hasSymptom 关系: 松材线虫病 → 枯死")
            else:
                print("  ✓ hasSymptom 关系已存在")
            
            # ============================================================
            # 4. 为松材线虫病添加hasVector关系（松褐天牛）
            # ============================================================
            print("\n4. 为松材线虫病添加hasVector关系（松褐天牛）...")
            
            result = session.run("""
                MATCH (d:Disease {name: '松材线虫病'})
                MATCH (v:Vector {name: '松褐天牛'})
                WHERE NOT (d)-[:hasVector]->(v)
                CREATE (d)-[r:hasVector]->(v)
                SET r.confidence = 0.95
                RETURN count(r) as count
            """)
            count = result.single()['count']
            if count > 0:
                print(f"  ✓ 已创建 hasVector 关系: 松材线虫病 → 松褐天牛")
            else:
                print("  ✓ hasVector 关系已存在")
            
            # ============================================================
            # 5. 验证修复结果
            # ============================================================
            print("\n" + "="*60)
            print("验证修复结果")
            print("="*60)
            
            # 检查关系类型
            result = session.run("""
                MATCH (a)-[r]->(b)
                RETURN type(r) as relType, labels(a)[0] as startType, 
                       labels(b)[0] as endType, count(*) as count
                ORDER BY relType, startType
            """)
            
            print("\n关系类型分布:")
            for record in result:
                print(f"  {record['relType']}: {record['startType']} → {record['endType']} ({record['count']}条)")
            
            # 检查松材线虫病的关系
            result = session.run("""
                MATCH (d:Disease {name: '松材线虫病'})-[r]-(n)
                RETURN type(r) AS 关系类型, labels(n)[0] AS 目标类型, count(*) AS 数量
                ORDER BY type(r)
            """)
            
            print("\n松材线虫病的关系:")
            for record in result:
                print(f"  {record['关系类型']} → [{record['目标类型']}]: {record['数量']} 条")
        
        driver.close()
        return True
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        driver.close()
        return False


def update_csv_files():
    """更新CSV文件"""
    print("\n" + "="*60)
    print("更新CSV文件")
    print("="*60)
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # 导出节点
            result = session.run("""
                MATCH (n)
                RETURN n.id as id, labels(n)[0] as label, n.name as name
                ORDER BY n.id
            """)
            
            nodes_data = []
            id_mapping = {}
            
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
            
            # 导出关系
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
            
            # 显示统计
            print("\n节点类型分布:")
            for label, count in nodes_df['label'].value_counts().items():
                print(f"  {label}: {count}")
            
            print("\n关系类型分布:")
            for rel, count in relations_df['relation'].value_counts().items():
                print(f"  {rel}: {count}")
    
    except Exception as e:
        print(f"\n✗ 错误: {e}")
    finally:
        driver.close()


def main():
    print("\n" + "="*60)
    print("修复所有数据问题")
    print("="*60)
    
    # 1. 修复问题
    success = fix_issues()
    
    if success:
        # 2. 更新CSV文件
        update_csv_files()
        
        print("\n" + "="*60)
        print("✅ 所有问题已修复！")
        print("="*60)
        print("\n建议:")
        print("1. 运行 comprehensive_data_check.py 再次验证")
        print("2. 在 Neo4j Browser 中查看修复结果")


if __name__ == '__main__':
    main()

