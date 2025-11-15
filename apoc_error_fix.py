#!/usr/bin/env python3
"""
Fix for Neo4j APOC shortestPath error in Jupyter Notebook
This script will create a new cell with the corrected code
"""

import json

def create_fixed_cell():
    """Create a new cell with the corrected shortest path query"""
    
    fixed_code = '''# 修复后的最短路径查询 - 使用标准Cypher替代APOC
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
        
        print("\\n✅ 成功找到最短路径:")
        print(path_str)
        print(f"路径长度: {len(nodes)} 个节点")
        
        # 显示详细信息
        print("\\n详细信息:")
        print(f"起始节点: {nodes[0]}")
        print(f"结束节点: {nodes[-1]}")
        print(f"中间节点: {nodes[1:-1] if len(nodes) > 2 else '无'}")
        print(f"关系数量: {len(relationships)}")
        
    else:
        print("\\n❌ 未找到连接路径")
        
        # 尝试备用查询
        print("\\n尝试备用查询（检查是否存在连接）...")
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
                print(f"✅ 存在连接")
                print(f"连接数: {result[0]['connections']}")
                print(f"路径长度: {result[0]['path_length']}")
            else:
                print("❌ 未找到任何连接")
        except Exception as backup_error:
            print(f"❌ 备用查询失败: {backup_error}")
            
except Exception as e:
    print(f"\\n❌ 查询出错: {e}")
    print("\\n可能的解决方案:")
    print("1. 检查节点名称是否正确")
    print("2. 确认数据库中存在这些节点")
    print("3. 尝试增加路径搜索长度（将[*..5]改为[*..10]）")
    print("4. 检查Neo4j数据库连接")

# 方案2: 简化的路径查询（如果上述方案失败）
print("\\n" + "="*50)
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
print("\\n如需使用，请执行:")
print("result = query_database(simple_query)")
'''
    
    return fixed_code

def create_guide():
    """Create a comprehensive guide for fixing the APOC issue"""
    
    guide = '''# Neo4j APOC shortestPath 错误完整解决方案

## 问题原因
错误信息：`ClientError: Neo.ClientError.Procedure.ProcedureNotFound`
原因：Neo4j数据库中没有安装APOC插件，导致`apoc.path.shortestPath`过程不可用。

## 解决方案

### 方案1: 使用标准Cypher shortestPath函数（推荐）

这是最简单且推荐的解决方案，因为：
- 不需要安装额外插件
- 标准Cypher内置支持
- 性能良好

```cypher
MATCH (start {name: '松材线虫'}), (end {name: '黑松'})
MATCH p = shortestPath((start)-[*..5]-(end))
RETURN p as path
```

### 方案2: 使用路径展开查询

```cypher
MATCH (start {name: '松材线虫'}), (end {name: '黑松'})
MATCH path = (start)-[*1..5]-(end)
RETURN [node in nodes(path) | node.name] as node_names,
       [rel in relationships(path) | rel.label_cn] as rel_names,
       length(path) as path_length
ORDER BY path_length
LIMIT 1
```

### 方案3: 安装APOC插件（高级选项）

如果确实需要使用APOC的其他功能：

1. **停止Neo4j服务**
   ```bash
   # macOS
   sudo neo4j stop
   # 或使用系统偏好设置
   ```

2. **下载APOC插件**
   - 访问：https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases
   - 下载与Neo4j版本匹配的JAR文件

3. **安装插件**
   ```bash
   # 将JAR文件放入Neo4j plugins目录
   # macOS通常在：/usr/local/lib/neo4j/plugins/
   # 或：/Applications/Neo4j.app/Contents/Resources/app/plugins/
   cp apoc-*.jar /usr/local/lib/neo4j/plugins/
   ```

4. **配置Neo4j**
   编辑 `neo4j.conf` 文件：
   ```properties
   # 添加以下行
   dbms.security.procedures.unrestricted=apoc.*
   dbms.security.procedures.allowlist=apoc.*
   ```

5. **重启Neo4j**
   ```bash
   sudo neo4j start
   ```

## 修复后的Python代码

```python
# 使用标准Cypher的最短路径查询
shortest_path_query = """
MATCH (start {name: '松材线虫'}), (end {name: '黑松'})
MATCH p = shortestPath((start)-[*..5]-(end))
RETURN p as path
"""

try:
    shortest_path = query_database(shortest_path_query)
    
    if shortest_path:
        path = shortest_path[0]['path']
        
        # 提取节点和关系
        nodes = [node.get('name', f'Node{i}') for i, node in enumerate(path.nodes)]
        relationships = []
        
        for i, rel in enumerate(path.relationships):
            rel_name = rel.get('label_cn', rel.get('type', 'RELATED'))
            relationships.append(rel_name)
        
        # 构建路径显示
        path_parts = []
        for i in range(len(nodes)):
            path_parts.append(nodes[i])
            if i < len(relationships):
                path_parts.append(f"[{relationships[i]}]")
        
        path_str = ' → '.join(path_parts)
        
        print("✅ 找到最短路径:")
        print(path_str)
        print(f"路径长度: {len(nodes)} 个节点")
    else:
        print("❌ 未找到连接路径")
        
except Exception as e:
    print(f"❌ 查询出错: {e}")
    
    # 备用查询
    backup_query = """
    MATCH (start {name: '松材线虫'}), (end {name: '黑松'})
    MATCH (start)-[r*1..3]-(end)
    RETURN count(r) as connections
    """
    
    try:
        result = query_database(backup_query)
        if result:
            print(f"✅ 存在连接: {result[0]['connections']} 条路径")
    except:
        print("❌ 备用查询也失败")
```

## 常见问题

### Q: 为什么不直接安装APOC？
A: 
- 安装APOC需要管理员权限
- 可能与现有Neo4j版本不兼容
- 标准Cypher已经足够满足大部分需求

### Q: shortestPath和APOC shortestPath有什么区别？
A: 
- 功能基本相同
- APOC提供更多高级选项
- 标准shortestPath更简单易用

### Q: 如何验证修复是否成功？
A: 
- 运行修复后的代码
- 检查是否还有ClientError
- 确认能正确显示路径

## 下一步

1. 在Jupyter Notebook中创建新单元格
2. 复制`apoc_error_fix.py`中的代码
3. 运行新单元格
4. 验证结果

## 联系支持

如果问题持续存在：
1. 检查Neo4j版本兼容性
2. 确认数据库中存在指定节点
3. 验证网络连接
'''
    
    return guide

# 生成修复代码
fixed_code = create_fixed_cell()
with open('/Users/lifulin/Desktop/PWD/apoc_fix_notebook.py', 'w', encoding='utf-8') as f:
    f.write(fixed_code)

# 生成指南
guide = create_guide()
with open('/Users/lifulin/Desktop/PWD/APOC_ERROR_FIX_GUIDE.md', 'w', encoding='utf-8') as f:
    f.write(guide)

print("✅ 修复文件已生成:")
print("1. apoc_fix_notebook.py - 可直接在notebook中运行的修复代码")
print("2. APOC_ERROR_FIX_GUIDE.md - 完整的问题解决指南")
print("\n请在Jupyter Notebook中:")
print("1. 创建新的单元格")
print("2. 复制 apoc_fix_notebook.py 中的代码")
print("3. 运行该单元格")
