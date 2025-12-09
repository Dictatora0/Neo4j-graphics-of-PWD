#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
松材线虫病知识图谱查询脚本
功能：执行常见的数据库查询命令，展示知识图谱成果
"""

import os
import sys
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
from tabulate import tabulate
from colorama import init, Fore, Style
import argparse

# 初始化 colorama
init(autoreset=True)


class KnowledgeGraphQuery:
    """知识图谱查询类 - 封装常用的Cypher查询操作
    
    功能模块：
    1. 统计查询 - 节点数、关系数、类型分布
    2. 实体查询 - 按类型、关键词搜索节点
    3. 关系查询 - 查看节点的邻居关系
    4. 路径查询 - 最短路径搜索
    5. 高级查询 - 社区分析、核心节点识别
    """
    
    def __init__(self, uri: str = "bolt://localhost:7687", 
                 user: str = "neo4j", 
                 password: str = "12345678"):
        """初始化Neo4j数据库连接
        
        Args:
            uri: Neo4j连接URI（默认本地：bolt://localhost:7687）
            user: 数据库用户名（默认neo4j）
            password: 数据库密码（需要在config.yaml中配置）
        
        连接失败会抛出异常，需要确保Neo4j服务正在运行
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
    def close(self):
        """关闭数据库连接"""
        self.driver.close()
        
    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """
        执行Cypher查询
        
        Args:
            query: Cypher查询语句
            parameters: 查询参数
            
        Returns:
            查询结果列表
        """
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]
    
    def print_header(self, title: str):
        """打印标题"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{title:^80}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    def print_section(self, title: str):
        """打印小节标题"""
        print(f"\n{Fore.YELLOW}▶ {title}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'-'*80}{Style.RESET_ALL}")
    
    def print_success(self, message: str):
        """打印成功信息"""
        print(f"{Fore.GREEN}[OK] {message}{Style.RESET_ALL}")
    
    def print_info(self, message: str):
        """打印提示信息"""
        print(f"{Fore.BLUE}[INFO] {message}{Style.RESET_ALL}")
    
    def print_warning(self, message: str):
        """打印警告信息"""
        print(f"{Fore.YELLOW}[WARN] {message}{Style.RESET_ALL}")
    
    def print_error(self, message: str):
        """打印错误信息"""
        print(f"{Fore.RED}[ERROR] {message}{Style.RESET_ALL}")
    
    # ========== 统计查询 ==========
    
    def get_database_stats(self):
        """获取数据库统计信息 - 总览知识图谱规模
        
        输出内容：
        - 总节点数、总关系数
        - 平均度数（每个节点的平均连接数）
        - 节点类型分布（Pathogen、Host、Vector等）
        - 关系类型分布（感染、传播、防治等）
        
        用途：快速了解知识图谱的规模和结构
        """
        self.print_section("数据库统计信息")
        
        # 节点总数
        node_count_query = "MATCH (n) RETURN count(n) as total_nodes"
        node_result = self.execute_query(node_count_query)
        total_nodes = node_result[0]['total_nodes']
        
        # 关系总数
        rel_count_query = "MATCH ()-[r]->() RETURN count(r) as total_relationships"
        rel_result = self.execute_query(rel_count_query)
        total_relationships = rel_result[0]['total_relationships']
        
        # 节点标签统计
        label_query = """
        MATCH (n)
        WITH labels(n)[0] as label, count(*) as count
        RETURN label, count
        ORDER BY count DESC
        """
        label_stats = self.execute_query(label_query)
        
        # 关系类型统计
        rel_type_query = """
        MATCH ()-[r]->()
        WITH type(r) as rel_type, count(*) as count
        RETURN rel_type, count
        ORDER BY count DESC
        """
        rel_type_stats = self.execute_query(rel_type_query)
        
        # 打印统计信息
        print(f"\n{Fore.GREEN}总节点数: {Fore.WHITE}{total_nodes:,}")
        print(f"{Fore.GREEN}总关系数: {Fore.WHITE}{total_relationships:,}")
        print(f"{Fore.GREEN}平均度数: {Fore.WHITE}{total_relationships*2/total_nodes:.2f}")
        
        print(f"\n{Fore.CYAN}节点类型分布:")
        if label_stats:
            table_data = [[item['label'], item['count'], 
                          f"{item['count']/total_nodes*100:.2f}%"] 
                         for item in label_stats]
            headers = ['节点类型', '数量', '占比']
            print(tabulate(table_data, headers=headers, tablefmt='simple'))
        
        print(f"\n{Fore.CYAN}关系类型分布:")
        if rel_type_stats:
            table_data = [[item['rel_type'], item['count'],
                          f"{item['count']/total_relationships*100:.2f}%"]
                         for item in rel_type_stats]
            headers = ['关系类型', '数量', '占比']
            print(tabulate(table_data, headers=headers, tablefmt='simple'))
    
    def get_node_degree_distribution(self):
        """获取节点度数分布 - 找出连接最多的核心节点
        
        度数：一个节点连接的关系总数（入度+出度）
        
        输出：Top 20高度数节点
        - 度数越高，说明该概念越重要，与其他概念关联越多
        - 如"松材线虫"通常度数最高（病原核心）
        
        应用：识别知识图谱中的关键概念
        """
        self.print_section("节点度数分布（Top 20）")
        
        query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[r]-()
        WITH n, count(r) as degree
        WHERE degree > 0
        RETURN n.name as node_name, 
               labels(n)[0] as node_type,
               degree
        ORDER BY degree DESC
        LIMIT 20
        """
        results = self.execute_query(query)
        
        if results:
            table_data = [[i+1, r['node_name'][:40], r['node_type'], r['degree']] 
                         for i, r in enumerate(results)]
            headers = ['排名', '节点名称', '类型', '度数']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
        else:
            self.print_warning("未找到相关数据")
    
    # ========== 实体查询 ==========
    
    def get_nodes_by_type(self, node_type: str, limit: int = 10):
        """获取指定类型的节点"""
        self.print_section(f"{node_type} 类型节点（前 {limit} 个）")
        
        query = f"""
        MATCH (n:{node_type})
        OPTIONAL MATCH (n)-[r]-()
        WITH n, count(r) as degree
        RETURN n.name as name, 
               n.type as type,
               degree
        ORDER BY degree DESC
        LIMIT {limit}
        """
        results = self.execute_query(query)
        
        if results:
            table_data = [[i+1, r['name'][:50], r.get('type', 'N/A'), r['degree']] 
                         for i, r in enumerate(results)]
            headers = ['序号', '名称', '子类型', '度数']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
        else:
            self.print_warning(f"未找到 {node_type} 类型节点")
    
    def search_node(self, keyword: str):
        """搜索节点"""
        self.print_section(f"搜索节点: '{keyword}'")
        
        query = """
        MATCH (n)
        WHERE toLower(n.name) CONTAINS toLower($keyword)
        OPTIONAL MATCH (n)-[r]-()
        WITH n, count(r) as degree
        RETURN n.name as name,
               labels(n)[0] as type,
               degree
        ORDER BY degree DESC
        LIMIT 20
        """
        results = self.execute_query(query, {'keyword': keyword})
        
        if results:
            table_data = [[i+1, r['name'][:50], r['type'], r['degree']] 
                         for i, r in enumerate(results)]
            headers = ['序号', '名称', '类型', '度数']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
            self.print_success(f"找到 {len(results)} 个匹配节点")
        else:
            self.print_warning(f"未找到包含 '{keyword}' 的节点")
    
    # ========== 关系查询 ==========
    
    def get_node_relationships(self, node_name: str):
        """获取指定节点的所有关系"""
        self.print_section(f"节点关系: '{node_name}'")
        
        query = """
        MATCH (n {name: $node_name})-[r]-(m)
        RETURN n.name as source,
               type(r) as relationship,
               m.name as target,
               labels(m)[0] as target_type
        LIMIT 50
        """
        results = self.execute_query(query, {'node_name': node_name})
        
        if results:
            table_data = [[i+1, r['source'][:30], r['relationship'], 
                          r['target'][:30], r['target_type']] 
                         for i, r in enumerate(results)]
            headers = ['序号', '源节点', '关系类型', '目标节点', '目标类型']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
            self.print_success(f"找到 {len(results)} 条关系")
        else:
            self.print_warning(f"未找到节点 '{node_name}' 或该节点没有关系")
    
    def get_relationships_by_type(self, rel_type: str, limit: int = 20):
        """获取指定类型的关系"""
        self.print_section(f"'{rel_type}' 类型关系（前 {limit} 条）")
        
        query = f"""
        MATCH (n)-[r:{rel_type}]->(m)
        RETURN n.name as source,
               labels(n)[0] as source_type,
               type(r) as relationship,
               m.name as target,
               labels(m)[0] as target_type
        LIMIT {limit}
        """
        results = self.execute_query(query)
        
        if results:
            table_data = [[i+1, r['source'][:25], r['source_type'], 
                          r['relationship'], r['target'][:25], r['target_type']] 
                         for i, r in enumerate(results)]
            headers = ['序号', '源节点', '源类型', '关系', '目标节点', '目标类型']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
        else:
            self.print_warning(f"未找到 '{rel_type}' 类型关系")
    
    # ========== 路径查询 ==========
    
    def find_shortest_path(self, source: str, target: str):
        """查找两个节点之间的最短路径 - 发现概念间的关联链
        
        Args:
            source: 源节点名称（如"松材线虫"）
            target: 目标节点名称（如"马尾松"）
        
        输出：
        - 路径长度（经过的关系数）
        - 完整路径（节点序列和关系类型）
        
        应用场景：
        - 理解两个概念如何关联（如病原到寄主的传播链）
        - 发现潜在的间接关系
        """
        self.print_section(f"最短路径: '{source}' → '{target}'")
        
        query = """
        MATCH path = shortestPath(
            (source {name: $source})-[*..10]-(target {name: $target})
        )
        RETURN [node in nodes(path) | node.name] as path_nodes,
               [rel in relationships(path) | type(rel)] as path_rels,
               length(path) as path_length
        """
        results = self.execute_query(query, {'source': source, 'target': target})
        
        if results:
            for i, r in enumerate(results):
                print(f"\n{Fore.GREEN}路径 {i+1}:")
                print(f"{Fore.CYAN}长度: {Fore.WHITE}{r['path_length']}")
                
                # 打印路径
                path_str = ""
                nodes = r['path_nodes']
                rels = r['path_rels']
                
                for j, node in enumerate(nodes):
                    path_str += f"{Fore.YELLOW}{node[:20]}{Style.RESET_ALL}"
                    if j < len(rels):
                        path_str += f" {Fore.BLUE}--[{rels[j]}]-->{Style.RESET_ALL} "
                
                print(f"\n{path_str}\n")
        else:
            self.print_warning(f"未找到从 '{source}' 到 '{target}' 的路径")
    
    # ========== 高级查询 ==========
    
    def get_community_analysis(self):
        """社区分析（根据连接紧密程度）"""
        self.print_section("核心节点群落分析")
        
        query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[r]-(m)
        WITH n, count(DISTINCT m) as neighbors, count(r) as total_connections
        WHERE neighbors >= 3
        RETURN n.name as node_name,
               labels(n)[0] as node_type,
               neighbors,
               total_connections
        ORDER BY total_connections DESC
        LIMIT 20
        """
        results = self.execute_query(query)
        
        if results:
            table_data = [[i+1, r['node_name'][:40], r['node_type'], 
                          r['neighbors'], r['total_connections']] 
                         for i, r in enumerate(results)]
            headers = ['排名', '节点名称', '类型', '邻居数', '总连接数']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
        else:
            self.print_warning("未找到核心节点群落")
    
    def get_knowledge_triples(self, limit: int = 20):
        """获取知识三元组"""
        self.print_section(f"知识三元组示例（前 {limit} 条）")
        
        query = f"""
        MATCH (n)-[r]->(m)
        RETURN n.name as subject,
               labels(n)[0] as subject_type,
               type(r) as predicate,
               m.name as object,
               labels(m)[0] as object_type
        LIMIT {limit}
        """
        results = self.execute_query(query)
        
        if results:
            table_data = [[i+1, r['subject'][:25], r['subject_type'],
                          r['predicate'], r['object'][:25], r['object_type']] 
                         for i, r in enumerate(results)]
            headers = ['序号', '主语', '主语类型', '谓语', '宾语', '宾语类型']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
        else:
            self.print_warning("未找到知识三元组")


def print_menu():
    """打印菜单"""
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{'松材线虫病知识图谱查询系统':^70}")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    menu_items = [
        ("1", "数据库统计信息", "查看节点、关系总数及类型分布"),
        ("2", "节点度数分布", "查看连接最多的核心节点"),
        ("3", "按类型查看节点", "查看特定类型的节点列表"),
        ("4", "搜索节点", "根据关键词搜索节点"),
        ("5", "查看节点关系", "查看指定节点的所有关系"),
        ("6", "按类型查看关系", "查看特定类型的关系"),
        ("7", "最短路径查询", "查找两个节点之间的最短路径"),
        ("8", "核心节点分析", "分析连接紧密的核心节点"),
        ("9", "知识三元组", "查看知识图谱三元组"),
        ("0", "退出系统", "")
    ]
    
    for num, title, desc in menu_items:
        if desc:
            print(f"{Fore.GREEN}{num}.{Style.RESET_ALL} {Fore.YELLOW}{title:<20}{Style.RESET_ALL} - {desc}")
        else:
            print(f"{Fore.RED}{num}.{Style.RESET_ALL} {Fore.YELLOW}{title}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}{'-'*80}{Style.RESET_ALL}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='松材线虫病知识图谱查询系统')
    parser.add_argument('--uri', default='bolt://localhost:7687', help='Neo4j URI')
    parser.add_argument('--user', default='neo4j', help='Neo4j用户名')
    parser.add_argument('--password', default='12345678', help='Neo4j密码')
    parser.add_argument('--auto', action='store_true', help='自动运行所有查询')
    
    args = parser.parse_args()
    
    # 创建查询实例
    try:
        kg = KnowledgeGraphQuery(args.uri, args.user, args.password)
        kg.print_success("成功连接到 Neo4j 数据库")
    except Exception as e:
        print(f"{Fore.RED}连接数据库失败: {e}{Style.RESET_ALL}")
        sys.exit(1)
    
    # 自动模式：运行所有查询
    if args.auto:
        kg.print_header("知识图谱成果展示")
        
        # 1. 数据库统计
        kg.get_database_stats()
        
        # 2. 节点度数分布
        kg.get_node_degree_distribution()
        
        # 3. 各类型节点示例
        node_types = ['Pathogen', 'Host', 'Vector', 'Disease', 'Location']
        for node_type in node_types:
            try:
                kg.get_nodes_by_type(node_type, limit=5)
            except:
                pass
        
        # 4. 核心节点分析
        kg.get_community_analysis()
        
        # 5. 知识三元组
        kg.get_knowledge_triples(limit=15)
        
        kg.close()
        return
    
    # 交互模式
    while True:
        print_menu()
        choice = input(f"\n{Fore.CYAN}请选择功能 (0-9): {Style.RESET_ALL}").strip()
        
        if choice == '0':
            kg.print_success("感谢使用！")
            break
        elif choice == '1':
            kg.get_database_stats()
        elif choice == '2':
            kg.get_node_degree_distribution()
        elif choice == '3':
            node_type = input(f"{Fore.CYAN}请输入节点类型 (如 Pathogen, Host, Vector): {Style.RESET_ALL}").strip()
            limit = input(f"{Fore.CYAN}显示数量 (默认10): {Style.RESET_ALL}").strip()
            limit = int(limit) if limit.isdigit() else 10
            kg.get_nodes_by_type(node_type, limit)
        elif choice == '4':
            keyword = input(f"{Fore.CYAN}请输入搜索关键词: {Style.RESET_ALL}").strip()
            kg.search_node(keyword)
        elif choice == '5':
            node_name = input(f"{Fore.CYAN}请输入节点名称: {Style.RESET_ALL}").strip()
            kg.get_node_relationships(node_name)
        elif choice == '6':
            rel_type = input(f"{Fore.CYAN}请输入关系类型: {Style.RESET_ALL}").strip()
            limit = input(f"{Fore.CYAN}显示数量 (默认20): {Style.RESET_ALL}").strip()
            limit = int(limit) if limit.isdigit() else 20
            kg.get_relationships_by_type(rel_type, limit)
        elif choice == '7':
            source = input(f"{Fore.CYAN}请输入源节点名称: {Style.RESET_ALL}").strip()
            target = input(f"{Fore.CYAN}请输入目标节点名称: {Style.RESET_ALL}").strip()
            kg.find_shortest_path(source, target)
        elif choice == '8':
            kg.get_community_analysis()
        elif choice == '9':
            limit = input(f"{Fore.CYAN}显示数量 (默认20): {Style.RESET_ALL}").strip()
            limit = int(limit) if limit.isdigit() else 20
            kg.get_knowledge_triples(limit)
        else:
            kg.print_warning("无效选择，请重新输入")
        
        input(f"\n{Fore.CYAN}按回车键继续...{Style.RESET_ALL}")
    
    kg.close()


if __name__ == '__main__':
    main()
