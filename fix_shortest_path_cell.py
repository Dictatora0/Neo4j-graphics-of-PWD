#!/usr/bin/env python3
"""
Fix the shortest path cell with proper formatting
"""

import json

def fix_shortest_path_cell():
    notebook_path = "/Users/lifulin/Desktop/PWD/PWD_Knowledge_Graph_Analysis.ipynb"
    
    # Read the notebook
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    
    # Find the problematic cell and fix it
    for i, cell in enumerate(notebook['cells']):
        if cell['cell_type'] == 'code' and 'source' in cell:
            source = ''.join(cell['source'])
            
            # Check if this is the problematic shortest path cell
            if "shortest_path_query" in source and "黑松" in source and len(source) < 500:  # Compressed line
                # Replace with properly formatted code
                new_source = [
                    "# 使用标准Cypher查询最短路径（无需APOC插件）",
                    "shortest_path_query = \"\"\"",
                    "MATCH (start {name: '松材线虫'}), (end {name: '黑松'})",
                    "MATCH p = shortestPath((start)-[*..5]-(end))",
                    "RETURN p as path",
                    "\"\"\"",
                    "",
                    "try:",
                    "    shortest_path = query_database(shortest_path_query)",
                    "    ",
                    "    if shortest_path:",
                    "        path = shortest_path[0]['path']",
                    "        ",
                    "        # 提取路径中的节点",
                    "        nodes = []",
                    "        relationships = []",
                    "        ",
                    "        for i, node in enumerate(path.nodes):",
                    "            nodes.append(node.get('name', f'Node{i+1}'))",
                    "            if i < len(path.relationships):",
                    "                rel = path.relationships[i]",
                    "                rel_name = rel.get('label_cn', rel.get('type', 'RELATED'))",
                    "                relationships.append(rel_name)",
                    "        ",
                    "        # 构建路径字符串",
                    "        path_display = []",
                    "        for i in range(len(nodes)):",
                    "            path_display.append(nodes[i])",
                    "            if i < len(relationships):",
                    "                path_display.append(f'[{relationships[i]}]')",
                    "        ",
                    "        path_str = ' → '.join(path_display)",
                    "        ",
                    "        print('\"松材线虫\"到\"黑松\"的最短路径:')",
                    "        print(path_str)",
                    "        print(f'路径长度: {len(nodes)} 个节点')",
                    "    else:",
                    "        print('未找到连接路径')",
                    "        ",
                    "except Exception as e:",
                    "    print(f'查询出错: {e}')",
                    "    print('尝试简化查询...')",
                    "    ",
                    "    # 备用简化查询",
                    "    simple_query = \"\"\"",
                    "    MATCH (start {name: '松材线虫'}), (end {name: '黑松'})",
                    "    MATCH (start)-[r*1..3]-(end)",
                    "    RETURN count(r) as connections",
                    "    \"\"\"",
                    "    ",
                    "    try:",
                    "        result = query_database(simple_query)",
                    "        if result:",
                    "            print(f'存在连接，连接数: {result[0][\"connections\"]}')",
                    "        else:",
                    "            print('未找到任何连接')",
                    "    except Exception as e2:",
                    "        print(f'简化查询也失败: {e2}')"
                ]
                
                notebook['cells'][i]['source'] = new_source
                notebook['cells'][i]['execution_count'] = None
                notebook['cells'][i]['outputs'] = []
                
                print(f"Fixed cell {i} with proper shortest path query")
                break
    
    # Write the fixed notebook back
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=2, ensure_ascii=False)
    
    print(f"Fixed notebook saved to {notebook_path}")

if __name__ == "__main__":
    fix_shortest_path_cell()
