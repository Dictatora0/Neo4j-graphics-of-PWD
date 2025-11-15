#!/usr/bin/env python3
'''
Neo4j 自动导入脚本
使用Python的neo4j驱动自动执行导入
'''

from neo4j import GraphDatabase
import os

# Neo4j 连接配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"  # 请修改为您的密码

def import_to_neo4j(uri, user, password, cypher_file):
    '''执行Cypher脚本导入数据'''
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        # 读取Cypher脚本
        with open(cypher_file, 'r', encoding='utf-8') as f:
            cypher_script = f.read()
        
        # 分割脚本为独立语句
        statements = [s.strip() for s in cypher_script.split(';') if s.strip() and not s.strip().startswith('//')]
        
        with driver.session() as session:
            for i, statement in enumerate(statements, 1):
                if statement:
                    print(f"执行语句 {i}/{len(statements)}...")
                    try:
                        result = session.run(statement)
                        print(f"✓ 完成")
                    except Exception as e:
                        print(f"✗ 错误: {e}")
        
        print("\n导入完成！")
        
    finally:
        driver.close()

if __name__ == "__main__":
    cypher_file = "./output/neo4j_import/import.cypher"
    
    if not os.path.exists(cypher_file):
        print(f"错误: 找不到文件 {cypher_file}")
        exit(1)
    
    print(f"开始导入数据到 Neo4j...")
    print(f"连接: {NEO4J_URI}")
    print(f"用户: {NEO4J_USER}")
    print()
    
    import_to_neo4j(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, cypher_file)
