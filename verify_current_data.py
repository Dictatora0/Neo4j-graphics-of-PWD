#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面验证当前Neo4j数据库数据质量
"""

import pandas as pd
from neo4j import GraphDatabase

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"


def verify_files():
    """验证CSV文件"""
    print("="*60)
    print("1. CSV 文件验证")
    print("="*60)
    
    nodes = pd.read_csv('output/neo4j_import/nodes.csv')
    relations = pd.read_csv('output/neo4j_import/relations.csv')
    
    print(f"\n节点文件: {len(nodes)} 个节点")
    print(f"关系文件: {len(relations)} 条关系")
    
    print("\n节点类型分布:")
    for label, count in nodes['label'].value_counts().items():
        pct = count / len(nodes) * 100
        print(f"  {label}: {count} ({pct:.1f}%)")
    
    print("\n关系类型分布:")
    for rel, count in relations['relation'].value_counts().items():
        pct = count / len(relations) * 100
        print(f"  {rel}: {count} ({pct:.1f}%)")
    
    return nodes, relations


def verify_neo4j():
    """验证Neo4j数据库"""
    print("\n" + "="*60)
    print("2. Neo4j 数据库验证")
    print("="*60)
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        driver.verify_connectivity()
        print("\n✓ Neo4j 连接成功\n")
        
        with driver.session() as session:
            # 节点统计
            result = session.run("MATCH (n) RETURN labels(n)[0] as type, count(n) as count")
            print("节点统计:")
            total_nodes = 0
            for record in result:
                print(f"  {record['type']}: {record['count']} 个")
                total_nodes += record['count']
            print(f"  总计: {total_nodes} 个")
            
            # 关系统计
            result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
            print("\n关系统计:")
            total_rels = 0
            for record in result:
                print(f"  {record['type']}: {record['count']} 条")
                total_rels += record['count']
            print(f"  总计: {total_rels} 条")
            
            # 数据质量检查
            print("\n" + "="*60)
            print("3. 数据质量检查")
            print("="*60)
            
            # 检查孤立节点
            result = session.run("MATCH (n) WHERE NOT (n)-[]-() RETURN count(n) as count")
            isolated = result.single()['count']
            if isolated > 0:
                print(f"\n✗ 孤立节点: {isolated} 个")
                result = session.run("""
                    MATCH (n) WHERE NOT (n)-[]-() 
                    RETURN labels(n)[0] as type, count(n) as count
                """)
                for record in result:
                    print(f"    - {record['type']}: {record['count']} 个")
            else:
                print("\n✓ 孤立节点: 无")
            
            # 检查自环
            result = session.run("MATCH (n)-[r]->(n) RETURN count(r) as count")
            self_loops = result.single()['count']
            if self_loops > 0:
                print(f"✗ 自环关系: {self_loops} 条")
            else:
                print("✓ 自环关系: 无")
            
            # 检查重复关系
            result = session.run("""
                MATCH (a)-[r]->(b)
                WITH a, b, type(r) as relType, count(r) as cnt
                WHERE cnt > 1
                RETURN sum(cnt) as total
            """)
            duplicates = result.single()['total']
            if duplicates and duplicates > 0:
                print(f"✗ 重复关系: {duplicates} 条")
            else:
                print("✓ 重复关系: 无")
            
            # 检查空名称
            result = session.run("""
                MATCH (n) 
                WHERE n.name IS NULL OR n.name = '' OR trim(n.name) = ''
                RETURN count(n) as count
            """)
            empty_names = result.single()['count']
            if empty_names > 0:
                print(f"✗ 空名称节点: {empty_names} 个")
            else:
                print("✓ 空名称节点: 无")
            
            # 实体名称长度检查
            print("\n" + "="*60)
            print("4. 实体名称长度分析")
            print("="*60)
            
            result = session.run("""
                MATCH (n)
                WITH labels(n)[0] as type, n.name as name
                RETURN type, 
                       round(avg(size(name))) as avg_len,
                       max(size(name)) as max_len,
                       min(size(name)) as min_len,
                       count(name) as count
                ORDER BY type
            """)
            
            print("\n类型\t\t平均长度\t最大\t最小\t数量")
            print("-" * 60)
            for record in result:
                print(f"{record['type']:<15}\t{record['avg_len']:.0f}\t\t{record['max_len']}\t{record['min_len']}\t{record['count']}")
            
            # 显示核心实体
            print("\n" + "="*60)
            print("5. 核心实体展示")
            print("="*60)
            
            # Disease 实体
            result = session.run("MATCH (d:Disease) RETURN d.name as name ORDER BY d.name LIMIT 10")
            print("\nDisease（前10个）:")
            for i, record in enumerate(result, 1):
                print(f"  {i}. {record['name']}")
            
            # Pathogen 实体
            result = session.run("MATCH (p:Pathogen) RETURN p.name as name ORDER BY p.name")
            print("\nPathogen（全部）:")
            for i, record in enumerate(result, 1):
                print(f"  {i}. {record['name']}")
            
            # Host 实体
            result = session.run("MATCH (h:Host) RETURN h.name as name ORDER BY h.name")
            print("\nHost（全部）:")
            for i, record in enumerate(result, 1):
                print(f"  {i}. {record['name']}")
            
            # 检查松材线虫病的关系
            print("\n" + "="*60)
            print("6. 核心实体关系验证")
            print("="*60)
            
            result = session.run("""
                MATCH (d:Disease {name: '松材线虫病'})
                RETURN d
            """)
            if result.single():
                print("\n✓ 核心实体'松材线虫病'存在")
                
                result = session.run("""
                    MATCH (d:Disease {name: '松材线虫病'})-[r]-(n)
                    RETURN type(r) as relType, labels(n)[0] as nodeType, 
                           count(*) as count
                    ORDER BY count DESC
                """)
                
                print("\n松材线虫病的关系:")
                for record in result:
                    print(f"  {record['relType']} → {record['nodeType']}: {record['count']} 条")
                
                # 显示具体关联的实体
                result = session.run("""
                    MATCH (d:Disease {name: '松材线虫病'})-[r:hasPathogen]->(p:Pathogen)
                    RETURN p.name as pathogen
                """)
                pathogens = [r['pathogen'] for r in result]
                if pathogens:
                    print(f"\n  病原体: {', '.join(pathogens)}")
            else:
                print("\n✗ 核心实体'松材线虫病'不存在！")
            
            # 数据完整性评分
            print("\n" + "="*60)
            print("7. 数据质量评分")
            print("="*60)
            
            score = 100
            issues = []
            
            if isolated > 0:
                score -= 10
                issues.append(f"有 {isolated} 个孤立节点")
            
            if self_loops > 0:
                score -= 20
                issues.append(f"有 {self_loops} 条自环关系")
            
            if duplicates and duplicates > 0:
                score -= 15
                issues.append(f"有 {duplicates} 条重复关系")
            
            if empty_names > 0:
                score -= 20
                issues.append(f"有 {empty_names} 个空名称节点")
            
            if total_nodes < 50:
                score -= 10
                issues.append("节点数量过少")
            
            if total_rels == 0:
                score -= 30
                issues.append("没有关系数据")
            
            print(f"\n总体评分: {score}/100")
            
            if score == 100:
                print("评级: ⭐⭐⭐⭐⭐ 优秀")
                print("状态: ✅ 数据质量完美，可以放心使用")
            elif score >= 80:
                print("评级: ⭐⭐⭐⭐ 良好")
                print("状态: ⚠️ 有少量问题需要注意")
                print("\n问题:")
                for issue in issues:
                    print(f"  - {issue}")
            elif score >= 60:
                print("评级: ⭐⭐⭐ 一般")
                print("状态: ⚠️ 存在一些问题需要修复")
                print("\n问题:")
                for issue in issues:
                    print(f"  - {issue}")
            else:
                print("评级: ⭐⭐ 需要改进")
                print("状态: ❌ 数据质量需要显著改进")
                print("\n问题:")
                for issue in issues:
                    print(f"  - {issue}")
            
    except Exception as e:
        print(f"\n✗ 错误: {e}")
    finally:
        driver.close()


def check_data_consistency(nodes, relations):
    """检查CSV和Neo4j的一致性"""
    print("\n" + "="*60)
    print("8. CSV与Neo4j数据一致性检查")
    print("="*60)
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # 检查节点数量
            result = session.run("MATCH (n) RETURN count(n) as count")
            neo4j_node_count = result.single()['count']
            csv_node_count = len(nodes)
            
            print(f"\n节点数量:")
            print(f"  CSV文件: {csv_node_count}")
            print(f"  Neo4j: {neo4j_node_count}")
            
            if csv_node_count == neo4j_node_count:
                print("  ✓ 一致")
            else:
                print(f"  ✗ 不一致（差异: {abs(csv_node_count - neo4j_node_count)}）")
            
            # 检查关系数量
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            neo4j_rel_count = result.single()['count']
            csv_rel_count = len(relations)
            
            print(f"\n关系数量:")
            print(f"  CSV文件: {csv_rel_count}")
            print(f"  Neo4j: {neo4j_rel_count}")
            
            if csv_rel_count == neo4j_rel_count:
                print("  ✓ 一致")
            else:
                print(f"  ✗ 不一致（差异: {abs(csv_rel_count - neo4j_rel_count)}）")
    
    except Exception as e:
        print(f"\n✗ 错误: {e}")
    finally:
        driver.close()


def main():
    print("\n" + "="*60)
    print("Neo4j 数据库全面验证")
    print("="*60)
    print(f"\n连接: {NEO4J_URI}")
    print(f"访问: http://localhost:7474\n")
    
    # 1. 验证CSV文件
    nodes, relations = verify_files()
    
    # 2. 验证Neo4j数据库
    verify_neo4j()
    
    # 3. 检查一致性
    check_data_consistency(nodes, relations)
    
    print("\n" + "="*60)
    print("验证完成")
    print("="*60)
    print("\n建议查询（在Neo4j Browser中执行）:")
    print("\n1. 查看所有节点类型:")
    print("   MATCH (n) RETURN labels(n)[0] AS 类型, count(n) AS 数量")
    print("\n2. 查看松材线虫病关系网络:")
    print("   MATCH (d:Disease {name: '松材线虫病'})-[r]-(n)")
    print("   RETURN d, r, n")
    print("\n3. 查看所有疾病:")
    print("   MATCH (d:Disease) RETURN d.name ORDER BY d.name")


if __name__ == '__main__':
    main()

