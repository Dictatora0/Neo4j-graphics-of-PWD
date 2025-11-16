# 修复后的最短路径查询 - 使用标准Cypher替代APOC
# 在新的notebook单元格中运行此代码

# 使用标准Cypher shortestPath函数（推荐方案）
shortest_path_query = """
MATCH (start {name: '松材线虫'}), (end {name: '黑松'})
MATCH p = shortestPath((start)-[*..5]-(end))
RETURN p as path
"""

print("使用标准Cypher shortestPath函数替代APOC...")
print("查询语句:")
print(shortest_path_query.strip())

# 执行查询
try:
    shortest_path = query_database(shortest_path_query)
    
    if shortest_path:
        path = shortest_path[0]['path']
        
        # 安全地提取节点和关系
        nodes = []
        relationships = []
        
        for i, node in enumerate(path.nodes):
            node_name = node.get('name', f'Node{i+1}')
            nodes.append(node_name)
            
            if i < len(path.relationships):
                rel = path.relationships[i]
                rel_name = rel.get('label_cn', rel.get('type', 'RELATED'))
                relationships.append(rel_name)
        
        # 构建路径显示
        path_parts = []
        for i in range(len(nodes)):
            path_parts.append(nodes[i])
            if i < len(relationships):
                path_parts.append(f"[{relationships[i]}]")
        
        path_str = ' → '.join(path_parts)
        
        print("\n成功找到最短路径:")
        print(path_str)
        print(f"路径长度: {len(nodes)} 个节点")
        
        # 显示详细信息
        print("\n详细信息:")
        print(f"起始节点: {nodes[0]}")
        print(f"结束节点: {nodes[-1]}")
        print(f"中间节点: {nodes[1:-1] if len(nodes) > 2 else '无'}")
        print(f"关系数量: {len(relationships)}")
        
    else:
        print("\n未找到连接路径")
        
        # 尝试备用查询
        print("\n尝试备用查询（检查是否存在连接）...")
        backup_query = """
        MATCH (start {name: '松材线虫'}), (end {name: '黑松'})
        MATCH (start)-[r*1..3]-(end)
        RETURN count(r) as connections, length(r) as path_length
        ORDER BY path_length
        LIMIT 1
        """
        
        try:
            result = query_database(backup_query)
            if result:
                print("存在连接")
                print(f"连接数: {result[0]['connections']}")
                print(f"路径长度: {result[0]['path_length']}")
            else:
                print("未找到任何连接")
        except Exception as backup_error:
            print(f"备用查询失败: {backup_error}")
            
except Exception as e:
    print(f"\n查询出错: {e}")
    print("\n可能的解决方案:")
    print("1. 检查节点名称是否正确")
    print("2. 确认数据库中存在这些节点")
    print("3. 尝试增加路径搜索长度（将[*..5]改为[*..10]）")
    print("4. 检查Neo4j数据库连接")

# 方案2: 简化的路径查询（如果上述方案失败）
print("\n" + "="*50)
print("方案2: 简化查询（如果需要）")
print("="*50)

simple_query = """
MATCH (start {name: '松材线虫'}), (end {name: '黑松'})
MATCH path = (start)-[*1..5]-(end)
RETURN [node in nodes(path) | node.name] as node_names,
       [rel in relationships(path) | rel.label_cn] as rel_names,
       length(path) as path_length
ORDER BY path_length
LIMIT 1
"""

print("简化查询语句:")
print(simple_query.strip())
print("\n如需使用，请执行:")
print("result = query_database(simple_query)")
