#!/usr/bin/env python3
"""
Fix path processing code to work with standard Cypher instead of APOC
"""

import json

def fix_path_processing():
    notebook_path = "/Users/lifulin/Desktop/PWD/PWD_Knowledge_Graph_Analysis.ipynb"
    
    # Read the notebook
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    
    # Find and fix the path processing code
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code' and 'source' in cell:
            source = ''.join(cell['source'])
            
            # Look for path processing code that uses APOC format
            if "path.nodes" in source and "path.relationships" in source:
                # Replace the path processing
                old_processing = '''if shortest_path:
    path = shortest_path[0]['path']
    
    nodes = [node['name'] for node in path.nodes]
    relationships = [rel['label_cn'] for rel in path.relationships]
    
    path_str = " → ".join([f"{nodes[i]} -[{relationships[i]}]->" for i in range(len(relationships))]) + nodes[-1]
    
    print("松材线虫"到"黑松"的最短路径:")
    print(path_str)
else:
    print("未找到连接路径")'''
                
                new_processing = '''if shortest_path:
    path = shortest_path[0]['path']
    
    # Extract nodes and relationships from standard Cypher path
    nodes = []
    relationships = []
    
    for i, node in enumerate(path):
        nodes.append(node['name'])
        if i < len(path) - 1:
            # Get relationship between current and next node
            rel = path.relationships[i] if hasattr(path, 'relationships') else None
            if rel:
                relationships.append(rel.get('label_cn', rel.get('type', 'RELATED')))
            else:
                relationships.append('RELATED')
    
    # Build path string
    path_parts = []
    for i in range(len(nodes)):
        path_parts.append(nodes[i])
        if i < len(relationships):
            path_parts.append(f"[{relationships[i]}]")
    
    path_str = " → ".join(path_parts)
    
    print(""松材线虫"到"黑松"的最短路径:")
    print(path_str)
else:
    print("未找到连接路径")'''
                
                # Replace the source
                new_source = source.replace(old_processing, new_processing)
                cell['source'] = new_source.split('\n')
                
                print("Found and fixed path processing code")
                break
    
    # Write the fixed notebook back
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=2, ensure_ascii=False)
    
    print(f"Fixed notebook saved to {notebook_path}")

if __name__ == "__main__":
    fix_path_processing()
