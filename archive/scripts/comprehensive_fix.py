#!/usr/bin/env python3
"""
Create a comprehensive fix for the shortest path query
"""

import json

def fix_shortest_path():
    notebook_path = "/Users/lifulin/Desktop/PWD/PWD_Knowledge_Graph_Analysis.ipynb"
    
    # Read the notebook
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    
    # Find the cell with shortest path code
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code' and 'source' in cell:
            source = ''.join(cell['source'])
            
            # Look for the specific shortest path code
            if "shortest_path_query" in source and "黑松" in source:
                # Replace the entire cell content with a working version
                new_source = '''# 使用标准Cypher查询最短路径
shortest_path_query = """
MATCH (start {name: '松材线虫'}), (end {name: '黑松'})
MATCH p = shortestPath((start)-[*..5]-(end))
RETURN p as path
"""

try:
    shortest_path = query_database(shortest_path_query)
    
    if shortest_path:
        path = shortest_path[0]['path']
        
        # 提取路径信息
        path_info = []
        nodes_in_path = []
        
        # 处理路径节点和关系
        for i, node in enumerate(path.nodes):
            nodes_in_path.append(node['name'])
            if i < len(path.relationships):
                rel = path.relationships[i]
                rel_type = rel.get('label_cn', rel.get('type', 'RELATED'))
                path_info.append(f"{node['name']} --[{rel_type}]-->")
        
        # 添加最后一个节点
        if nodes_in_path:
            path_info.append(nodes_in_path[-1])
        
        path_str = " ".join(path_info)
        
        print(""松材线虫"到"黑松"的最短路径:")
        print(path_str)
        print(f"路径长度: {len(nodes_in_path)} 个节点")
    else:
        print("未找到连接路径")
        
except Exception as e:
    print(f"查询出错: {e}")
    # 尝试更简单的查询
    simple_query = """
    MATCH (start {name: '松材线虫'}), (end {name: '黑松'})
    MATCH (start)-[r*1..3]-(end)
    RETURN start.name, end.name, length(r) as path_length
    LIMIT 1
    """
    
    try:
        result = query_database(simple_query)
        if result:
            print(f"找到连接: {result[0]['start.name']} -> {result[0]['end.name']} (长度: {result[0]['path_length']})")
        else:
            print("未找到连接")
    except Exception as e2:
        print(f"简单查询也失败: {e2}")'''
                
                cell['source'] = new_source.split('\n')
                cell['execution_count'] = None  # Reset execution count
                cell['outputs'] = []  # Clear previous outputs
                
                print("Fixed shortest path cell completely")
                break
    
    # Write the fixed notebook back
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=2, ensure_ascii=False)
    
    print(f"Fixed notebook saved to {notebook_path}")

if __name__ == "__main__":
    fix_shortest_path()
