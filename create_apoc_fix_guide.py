#!/usr/bin/env python3
"""
Complete solution for APOC shortestPath issue
This script provides multiple approaches to fix the problem
"""

import json

def create_comprehensive_fix():
    """Create a comprehensive fix for the notebook"""
    
    # The issue: APOC procedures are not installed in Neo4j
    # Solution: Use standard Cypher functions instead
    
    fix_instructions = """
# APOC shortestPath 错误解决方案

## 问题原因
Neo4j 数据库中没有安装 APOC 插件，导致 `apoc.path.shortestPath` 过程不可用。

## 解决方案

### 方案1: 使用标准 Cypher shortestPath 函数 (推荐)

```cypher
MATCH (start {name: '松材线虫'}), (end {name: '黑松'})
MATCH p = shortestPath((start)-[*..5]-(end))
RETURN p as path
```

### 方案2: 使用更简单的路径查询

```cypher
MATCH (start {name: '松材线虫'}), (end {name: '黑松'})
MATCH (start)-[r*1..5]-(end)
RETURN start.name, end.name, length(r) as path_length
ORDER BY path_length
LIMIT 1
```

### 方案3: 安装 APOC 插件 (如果需要)

1. 停止 Neo4j 服务
2. 下载 APOC 插件 JAR 文件
3. 将 JAR 文件放入 Neo4j plugins 目录
4. 在 neo4j.conf 中添加: `dbms.security.procedures.unrestricted=apoc.*`
5. 重启 Neo4j 服务

## 修复后的 Python 代码

```python
# 使用标准 Cypher 的最短路径查询
shortest_path_query = """
MATCH (start {name: '松材线虫'}), (end {name: '黑松'})
MATCH p = shortestPath((start)-[*..5]-(end))
RETURN p as path
"""

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
        
        print("找到最短路径:")
        print(path_str)
        print(f"路径长度: {len(nodes)} 个节点")
    else:
        print("未找到连接路径")
        
except Exception as e:
    print(f"查询出错: {e}")
    
    # 备用查询
    backup_query = """
    MATCH (start {name: '松材线虫'}), (end {name: '黑松'})
    MATCH (start)-[r*1..3]-(end)
    RETURN count(r) as connections
    """
    
    try:
        result = query_database(backup_query)
        if result:
            print(f"存在连接，连接数: {result[0]['connections']}")
        else:
            print("未找到连接")
    except:
        print("备用查询也失败")
```
"""
    
    return fix_instructions

# Save the instructions
instructions = create_comprehensive_fix()
with open('/Users/lifulin/Desktop/PWD/APOC_FIX_GUIDE.md', 'w', encoding='utf-8') as f:
    f.write(instructions)

print("APOC 修复指南已创建: APOC_FIX_GUIDE.md")
print("\n请在 Jupyter Notebook 中运行以下代码来修复问题:")
print("\n# 复制 apoc_fix_notebook.py 中的代码到新的 notebook 单元格中运行")
