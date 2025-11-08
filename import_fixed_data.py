#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接导入修正后的数据到 Neo4j
"""

from neo4j import GraphDatabase
import pandas as pd

# Neo4j 连接配置
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

def import_to_neo4j():
    """导入数据到 Neo4j"""
    print("="*60)
    print("开始导入数据到 Neo4j...")
    print("="*60)
    print(f"连接: {NEO4J_URI}")
    print(f"用户: {NEO4J_USER}\n")
    
    try:
        # 连接数据库
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        # 读取修正后的文件
        nodes_df = pd.read_csv('output/neo4j_import/nodes.csv')
        relations_df = pd.read_csv('output/neo4j_import/relations.csv')
        
        print(f"读取数据:")
        print(f"  节点: {len(nodes_df)} 个")
        print(f"  关系: {len(relations_df)} 条\n")
        
        with driver.session() as session:
            # 1. 清空现有数据
            print("清空现有数据...")
            session.run("MATCH (n) DETACH DELETE n")
            print("  ✓ 完成\n")
            
            # 2. 创建索引
            print("创建索引...")
            session.run("CREATE INDEX IF NOT EXISTS FOR (n:Disease) ON (n.id)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (n:Pathogen) ON (n.id)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (n:Host) ON (n.id)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (n:Vector) ON (n.id)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (n:Symptom) ON (n.id)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (n:ControlMeasure) ON (n.id)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (n:Region) ON (n.id)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (n:EnvironmentalFactor) ON (n.id)")
            print("  ✓ 完成\n")
            
            # 3. 导入节点
            print(f"导入 {len(nodes_df)} 个节点...")
            node_count = 0
            for _, row in nodes_df.iterrows():
                query = f"""
                CREATE (n:{row['label']})
                SET n.id = $id, n.name = $name
                """
                session.run(query, id=int(row['id']), name=row['name'])
                node_count += 1
                if node_count % 100 == 0:
                    print(f"  已导入 {node_count} 个节点...")
            print(f"  ✓ 节点导入完成 ({node_count} 个)\n")
            
            # 4. 导入关系
            print(f"导入 {len(relations_df)} 条关系...")
            relation_count = 0
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
                relation_count += 1
                if relation_count % 50 == 0:
                    print(f"  已导入 {relation_count} 条关系...")
            print(f"  ✓ 关系导入完成 ({relation_count} 条)\n")
        
        # 5. 验证导入结果
        print("验证导入结果...")
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN labels(n)[0] as type, count(n) as count")
            print("\n  实体类型分布:")
            for record in result:
                print(f"    - {record['type']}: {record['count']} 个")
            
            result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
            print("\n  关系类型分布:")
            for record in result:
                print(f"    - {record['type']}: {record['count']} 条")
        
        driver.close()
        
        print("\n" + "="*60)
        print("导入成功！")
        print("="*60)
        print(f"\n请访问 Neo4j Browser 查看: http://localhost:7474")
        print("\n示例查询:")
        print("  // 查看所有节点类型")
        print("  MATCH (n) RETURN labels(n)[0] as Type, count(n) as Count")
        print("\n  // 查看松材线虫病的关系网络")
        print("  MATCH (d:Disease {name: '松材线虫病'})-[r]-(n)")
        print("  RETURN d, r, n LIMIT 50")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 导入失败: {e}")
        print("\n请检查:")
        print("1. Neo4j 是否已启动")
        print("2. 连接信息是否正确")
        print("3. 密码是否正确")
        return False


if __name__ == '__main__':
    import_to_neo4j()

