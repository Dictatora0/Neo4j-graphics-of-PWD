#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面数据质量检查
"""

from neo4j import GraphDatabase
import pandas as pd

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"


def comprehensive_check():
    """全面检查数据质量"""
    print("="*60)
    print("Neo4j 数据库全面质量检查")
    print("="*60)
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            issues = []
            warnings = []
            
            # ============================================================
            # 1. 基础统计检查
            # ============================================================
            print("\n" + "="*60)
            print("1. 基础统计检查")
            print("="*60)
            
            result = session.run("MATCH (n) RETURN count(n) as count")
            total_nodes = result.single()['count']
            print(f"\n总节点数: {total_nodes}")
            
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            total_rels = result.single()['count']
            print(f"总关系数: {total_rels}")
            
            if total_nodes < 20:
                warnings.append(f"节点数量较少（{total_nodes}个），可能缺少重要实体")
            
            # ============================================================
            # 2. 核心实体存在性检查
            # ============================================================
            print("\n" + "="*60)
            print("2. 核心实体存在性检查")
            print("="*60)
            
            core_entities = {
                'Disease': ['松材线虫病', 'pine wilt disease'],
                'Pathogen': ['松材线虫'],
                'Vector': ['天牛', '松褐天牛'],
                'Host': ['马尾松', '黑松', '赤松'],
            }
            
            for entity_type, names in core_entities.items():
                print(f"\n{entity_type}:")
                for name in names:
                    result = session.run(f"""
                        MATCH (n:{entity_type} {{name: $name}})
                        RETURN count(n) as count
                    """, name=name)
                    count = result.single()['count']
                    if count > 0:
                        print(f"  ✓ {name}")
                    else:
                        print(f"  ✗ {name} - 缺失！")
                        issues.append(f"核心实体缺失: {entity_type} - {name}")
            
            # ============================================================
            # 3. 关系类型正确性检查
            # ============================================================
            print("\n" + "="*60)
            print("3. 关系类型正确性检查")
            print("="*60)
            
            # 定义正确的关系类型组合
            valid_relations = {
                'hasPathogen': ('Disease', 'Pathogen'),
                'hasHost': ('Disease', 'Host'),
                'hasVector': ('Disease', 'Vector'),
                'hasSymptom': ('Disease', 'Symptom'),
                'affectedBy': ('Disease', 'EnvironmentalFactor'),
                'controlledBy': ('Disease', 'ControlMeasure'),
                'occursIn': ('Disease', 'Region'),
                'transmits': ('Vector', 'Pathogen'),
                'infects': ('Pathogen', 'Host'),
            }
            
            result = session.run("""
                MATCH (a)-[r]->(b)
                RETURN type(r) as relType, labels(a)[0] as startType, 
                       labels(b)[0] as endType, count(*) as count
                ORDER BY relType
            """)
            
            print("\n关系类型检查:")
            for record in result:
                rel_type = record['relType']
                start_type = record['startType']
                end_type = record['endType']
                count = record['count']
                
                if rel_type in valid_relations:
                    expected_start, expected_end = valid_relations[rel_type]
                    if start_type == expected_start and end_type == expected_end:
                        print(f"  ✓ {rel_type}: {start_type} → {end_type} ({count}条)")
                    else:
                        print(f"  ✗ {rel_type}: {start_type} → {end_type} ({count}条)")
                        print(f"    期望: {expected_start} → {expected_end}")
                        issues.append(f"关系类型错误: {rel_type} 应该是 {expected_start} → {expected_end}, 实际是 {start_type} → {end_type}")
                else:
                    print(f"  ⚠️ {rel_type}: {start_type} → {end_type} ({count}条) - 未定义的关系类型")
                    warnings.append(f"未定义的关系类型: {rel_type}")
            
            # ============================================================
            # 4. 数据完整性检查
            # ============================================================
            print("\n" + "="*60)
            print("4. 数据完整性检查")
            print("="*60)
            
            # 4.1 孤立节点
            result = session.run("""
                MATCH (n) WHERE NOT (n)-[]-()
                RETURN labels(n)[0] as type, count(n) as count
            """)
            isolated = []
            for record in result:
                isolated.append((record['type'], record['count']))
            
            if isolated:
                print(f"\n  ✗ 孤立节点:")
                for node_type, count in isolated:
                    print(f"    - {node_type}: {count} 个")
                    issues.append(f"孤立节点: {node_type} ({count}个)")
            else:
                print("\n  ✓ 无孤立节点")
            
            # 4.2 自环关系
            result = session.run("MATCH (n)-[r]->(n) RETURN count(r) as count")
            self_loops = result.single()['count']
            if self_loops > 0:
                print(f"\n  ✗ 自环关系: {self_loops} 条")
                issues.append(f"自环关系: {self_loops}条")
            else:
                print("\n  ✓ 无自环关系")
            
            # 4.3 重复关系
            result = session.run("""
                MATCH (a)-[r]->(b)
                WITH a, b, type(r) as relType, count(r) as cnt
                WHERE cnt > 1
                RETURN count(*) as count
            """)
            duplicates = result.single()['count']
            if duplicates and duplicates > 0:
                print(f"\n  ✗ 重复关系: {duplicates} 组")
                issues.append(f"重复关系: {duplicates}组")
            else:
                print("\n  ✓ 无重复关系")
            
            # 4.4 空名称
            result = session.run("""
                MATCH (n)
                WHERE n.name IS NULL OR n.name = '' OR trim(n.name) = ''
                RETURN count(n) as count
            """)
            empty_names = result.single()['count']
            if empty_names > 0:
                print(f"\n  ✗ 空名称节点: {empty_names} 个")
                issues.append(f"空名称节点: {empty_names}个")
            else:
                print("\n  ✓ 无空名称节点")
            
            # ============================================================
            # 5. 松材线虫病关系完整性检查
            # ============================================================
            print("\n" + "="*60)
            print("5. 松材线虫病关系完整性检查")
            print("="*60)
            
            disease_name = '松材线虫病'
            
            # 检查是否有松材线虫病实体
            result = session.run("""
                MATCH (d:Disease {name: $name})
                RETURN count(d) as count
            """, name=disease_name)
            exists = result.single()['count'] > 0
            
            if not exists:
                issues.append(f"核心疾病实体缺失: {disease_name}")
                print(f"\n  ✗ {disease_name} 不存在！")
            else:
                print(f"\n  ✓ {disease_name} 存在")
                
                # 检查各种关系
                expected_relations = {
                    'hasPathogen': 'Pathogen',
                    'hasHost': 'Host',
                    'hasVector': 'Vector',
                    'hasSymptom': 'Symptom',
                    'affectedBy': 'EnvironmentalFactor',
                    'controlledBy': 'ControlMeasure',
                }
                
                print("\n  关系检查:")
                for rel_type, target_type in expected_relations.items():
                    result = session.run(f"""
                        MATCH (d:Disease {{name: $name}})-[r:{rel_type}]->(n:{target_type})
                        RETURN count(r) as count
                    """, name=disease_name)
                    count = result.single()['count']
                    
                    if count > 0:
                        print(f"    ✓ {rel_type} → {target_type}: {count} 条")
                    else:
                        print(f"    ⚠️ {rel_type} → {target_type}: 0 条")
                        if rel_type in ['hasPathogen', 'hasHost', 'hasVector']:
                            warnings.append(f"{disease_name} 缺少 {rel_type} 关系")
            
            # ============================================================
            # 6. 实体类型一致性检查
            # ============================================================
            print("\n" + "="*60)
            print("6. 实体类型一致性检查")
            print("="*60)
            
            # 检查可能的错误分类
            misclassified = []
            
            # Disease 中是否有应该是 Host 的实体
            result = session.run("""
                MATCH (d:Disease)
                WHERE d.name IN ['松树', 'Pine', 'Pinus', '马尾松', '黑松', '赤松']
                RETURN collect(d.name) as names
            """)
            names = result.single()['names']
            if names:
                print(f"\n  ✗ Disease 中发现可能的 Host 实体: {names}")
                misclassified.append(('Disease', 'Host', names))
            
            # Host 中是否有应该是 Disease 的实体
            result = session.run("""
                MATCH (h:Host)
                WHERE h.name IN ['松材线虫病', 'pine wilt disease', 'PWD']
                RETURN collect(h.name) as names
            """)
            names = result.single()['names']
            if names:
                print(f"\n  ✗ Host 中发现可能的 Disease 实体: {names}")
                misclassified.append(('Host', 'Disease', names))
            
            if not misclassified:
                print("\n  ✓ 未发现明显的错误分类")
            else:
                for old_type, new_type, names in misclassified:
                    issues.append(f"可能的错误分类: {old_type} 中的 {names} 应该是 {new_type}")
            
            # ============================================================
            # 7. 数据逻辑性检查
            # ============================================================
            print("\n" + "="*60)
            print("7. 数据逻辑性检查")
            print("="*60)
            
            # 检查是否有 Disease 没有 Pathogen
            result = session.run("""
                MATCH (d:Disease)
                WHERE NOT (d)-[:hasPathogen]->()
                RETURN d.name as name
            """)
            diseases_without_pathogen = [record['name'] for record in result]
            if diseases_without_pathogen:
                print(f"\n  ⚠️ 没有 Pathogen 的 Disease ({len(diseases_without_pathogen)} 个):")
                for name in diseases_without_pathogen[:5]:
                    print(f"    - {name}")
                if len(diseases_without_pathogen) > 5:
                    print(f"    ... 还有 {len(diseases_without_pathogen) - 5} 个")
                warnings.append(f"{len(diseases_without_pathogen)} 个 Disease 没有 Pathogen")
            
            # 检查是否有 Disease 没有 Host
            result = session.run("""
                MATCH (d:Disease)
                WHERE NOT (d)-[:hasHost]->()
                RETURN d.name as name
            """)
            diseases_without_host = [record['name'] for record in result]
            if diseases_without_host:
                print(f"\n  ⚠️ 没有 Host 的 Disease ({len(diseases_without_host)} 个):")
                for name in diseases_without_host[:5]:
                    print(f"    - {name}")
                if len(diseases_without_host) > 5:
                    print(f"    ... 还有 {len(diseases_without_host) - 5} 个")
                warnings.append(f"{len(diseases_without_host)} 个 Disease 没有 Host")
            
            # ============================================================
            # 8. 实体名称质量检查
            # ============================================================
            print("\n" + "="*60)
            print("8. 实体名称质量检查")
            print("="*60)
            
            # 检查过长的名称
            result = session.run("""
                MATCH (n)
                WHERE size(n.name) > 30
                RETURN labels(n)[0] as type, n.name as name, size(n.name) as len
                ORDER BY len DESC
                LIMIT 10
            """)
            long_names = [(record['type'], record['name'], record['len']) for record in result]
            if long_names:
                print(f"\n  ⚠️ 名称过长（>30字符）的实体:")
                for node_type, name, length in long_names:
                    print(f"    - [{node_type}] {name} ({length}字符)")
                warnings.append(f"{len(long_names)} 个实体名称过长")
            else:
                print("\n  ✓ 无过长名称")
            
            # 检查包含特殊字符的名称
            result = session.run("""
                MATCH (n)
                WHERE n.name =~ '.*[()\\[\\]{}].*'
                   OR n.name CONTAINS '，'
                   OR n.name CONTAINS '。'
                   OR n.name CONTAINS '；'
                   OR n.name CONTAINS '：'
                   OR n.name CONTAINS '"'
                   OR n.name CONTAINS '！'
                   OR n.name CONTAINS '？'
                RETURN labels(n)[0] as type, n.name as name
                LIMIT 10
            """)
            special_chars = [(record['type'], record['name']) for record in result]
            if special_chars:
                print(f"\n  ⚠️ 包含特殊字符的实体:")
                for node_type, name in special_chars:
                    print(f"    - [{node_type}] {name}")
                warnings.append(f"{len(special_chars)} 个实体包含特殊字符")
            else:
                print("\n  ✓ 无特殊字符")
            
            # ============================================================
            # 9. CSV与Neo4j一致性检查
            # ============================================================
            print("\n" + "="*60)
            print("9. CSV与Neo4j一致性检查")
            print("="*60)
            
            try:
                nodes_csv = pd.read_csv('output/neo4j_import/nodes.csv')
                relations_csv = pd.read_csv('output/neo4j_import/relations.csv')
                
                result = session.run("MATCH (n) RETURN count(n) as count")
                neo4j_nodes = result.single()['count']
                
                result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                neo4j_rels = result.single()['count']
                
                print(f"\n节点数量:")
                print(f"  CSV: {len(nodes_csv)}")
                print(f"  Neo4j: {neo4j_nodes}")
                if len(nodes_csv) == neo4j_nodes:
                    print("  ✓ 一致")
                else:
                    print(f"  ✗ 不一致（差异: {abs(len(nodes_csv) - neo4j_nodes)}）")
                    issues.append(f"CSV与Neo4j节点数不一致: CSV={len(nodes_csv)}, Neo4j={neo4j_nodes}")
                
                print(f"\n关系数量:")
                print(f"  CSV: {len(relations_csv)}")
                print(f"  Neo4j: {neo4j_rels}")
                if len(relations_csv) == neo4j_rels:
                    print("  ✓ 一致")
                else:
                    print(f"  ✗ 不一致（差异: {abs(len(relations_csv) - neo4j_rels)}）")
                    issues.append(f"CSV与Neo4j关系数不一致: CSV={len(relations_csv)}, Neo4j={neo4j_rels}")
            except Exception as e:
                warnings.append(f"无法检查CSV一致性: {e}")
            
            # ============================================================
            # 10. 总结报告
            # ============================================================
            print("\n" + "="*60)
            print("10. 检查总结")
            print("="*60)
            
            print(f"\n发现的问题 ({len(issues)} 个):")
            if issues:
                for i, issue in enumerate(issues, 1):
                    print(f"  {i}. {issue}")
            else:
                print("  ✓ 未发现严重问题")
            
            print(f"\n警告 ({len(warnings)} 个):")
            if warnings:
                for i, warning in enumerate(warnings, 1):
                    print(f"  {i}. {warning}")
            else:
                print("  ✓ 无警告")
            
            # 评分
            score = 100
            score -= len(issues) * 10
            score -= len(warnings) * 2
            score = max(0, score)
            
            print(f"\n数据质量评分: {score}/100")
            
            if score >= 90:
                print("评级: ⭐⭐⭐⭐⭐ 优秀")
            elif score >= 80:
                print("评级: ⭐⭐⭐⭐ 良好")
            elif score >= 70:
                print("评级: ⭐⭐⭐ 一般")
            elif score >= 60:
                print("评级: ⭐⭐ 需要改进")
            else:
                print("评级: ⭐ 需要重大改进")
            
            return issues, warnings, score
        
    except Exception as e:
        print(f"\n✗ 检查过程中出错: {e}")
        return [], [], 0
    finally:
        driver.close()


def main():
    print("\n" + "="*60)
    print("Neo4j 数据库全面质量检查")
    print("="*60)
    print(f"\n连接: {NEO4J_URI}")
    print(f"访问: http://localhost:7474\n")
    
    issues, warnings, score = comprehensive_check()
    
    print("\n" + "="*60)
    print("检查完成")
    print("="*60)
    
    if issues:
        print("\n建议:")
        print("1. 优先修复严重问题（issues）")
        print("2. 考虑处理警告（warnings）")
        print("3. 运行相应的修复脚本")
    else:
        print("\n✅ 数据质量良好，未发现严重问题！")


if __name__ == '__main__':
    main()


