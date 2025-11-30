#!/usr/bin/env python3
"""
清空Neo4j数据库中的所有节点和关系
"""

from neo4j import GraphDatabase
import sys

# Neo4j 连接配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"


def clear_database():
    """清空数据库"""
    print("="*60)
    print("清空Neo4j数据库")
    print("="*60)
    
    try:
        # 连接Neo4j
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        with driver.session() as session:
            # 获取当前节点和关系数量
            result = session.run("MATCH (n) RETURN count(n) as node_count")
            node_count = result.single()["node_count"]
            
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
            rel_count = result.single()["rel_count"]
            
            print(f"\n当前数据:")
            print(f"  - 节点数量: {node_count}")
            print(f"  - 关系数量: {rel_count}")
            
            if node_count == 0 and rel_count == 0:
                print("\n数据库已经是空的，无需清空")
                driver.close()
                return
            
            # 确认清空
            print(f"\n即将删除所有节点和关系...")
            
            # 删除所有节点和关系（批量删除）
            print("正在删除...")
            
            # 删除所有关系
            session.run("MATCH ()-[r]->() DELETE r")
            
            # 删除所有节点
            session.run("MATCH (n) DELETE n")
            
            # 删除所有约束和索引
            try:
                constraints = session.run("SHOW CONSTRAINTS")
                for constraint in constraints:
                    constraint_name = constraint.get("name")
                    if constraint_name:
                        session.run(f"DROP CONSTRAINT {constraint_name} IF EXISTS")
            except Exception as e:
                print(f"  - 清理约束时出错（可忽略）: {e}")
            
            try:
                indexes = session.run("SHOW INDEXES")
                for index in indexes:
                    index_name = index.get("name")
                    if index_name and not index_name.startswith("constraint"):
                        session.run(f"DROP INDEX {index_name} IF EXISTS")
            except Exception as e:
                print(f"  - 清理索引时出错（可忽略）: {e}")
            
            # 验证清空结果
            result = session.run("MATCH (n) RETURN count(n) as node_count")
            final_node_count = result.single()["node_count"]
            
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
            final_rel_count = result.single()["rel_count"]
            
            print(f"\n清空完成:")
            print(f"  - 删除节点: {node_count} -> {final_node_count}")
            print(f"  - 删除关系: {rel_count} -> {final_rel_count}")
            
            if final_node_count == 0 and final_rel_count == 0:
                print("\n✓ 数据库已成功清空")
            else:
                print("\n✗ 警告: 数据库未完全清空")
        
        driver.close()
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        print("\n可能的原因:")
        print("  1. Neo4j服务未启动")
        print("  2. 连接配置错误")
        print("  3. 认证失败")
        sys.exit(1)


if __name__ == "__main__":
    clear_database()
