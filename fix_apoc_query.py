#!/usr/bin/env python3
"""
Fix APOC shortestPath query in notebook to use standard Cypher
"""

import json
import sys

def fix_notebook():
    notebook_path = "/Users/lifulin/Desktop/PWD/PWD_Knowledge_Graph_Analysis.ipynb"
    
    # Read the notebook
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    
    # Find and replace the APOC query
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code' and 'source' in cell:
            source = ''.join(cell['source'])
            
            # Look for the APOC shortestPath query
            if "apoc.path.shortestPath" in source:
                # Replace the APOC query with standard Cypher
                old_query = '''shortest_path_query = """
MATCH (start {name: '松材线虫'}), (end {name: '黑松'})
CALL apoc.path.shortestPath(start, end, null, 5)
YIELD path
RETURN path
"""'''
                
                new_query = '''shortest_path_query = """
MATCH (start {name: '松材线虫'}), (end {name: '黑松'})
MATCH p = shortestPath((start)-[*..5]-(end))
RETURN p as path
"""'''
                
                # Replace the source
                new_source = source.replace(old_query, new_query)
                cell['source'] = new_source.split('\n')
                
                print("Found and replaced APOC shortestPath query")
                break
    
    # Write the fixed notebook back
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=2, ensure_ascii=False)
    
    print(f"Fixed notebook saved to {notebook_path}")

if __name__ == "__main__":
    fix_notebook()
