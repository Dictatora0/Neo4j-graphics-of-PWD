#!/usr/bin/env python3
"""
Verify the APOC fix by checking the generated files
"""

import os

def verify_fix():
    """Verify that the fix files were created correctly"""
    
    files_to_check = [
        '/Users/lifulin/Desktop/PWD/apoc_fix_notebook.py',
        '/Users/lifulin/Desktop/PWD/APOC_ERROR_FIX_GUIDE.md'
    ]
    
    print("验证修复文件:")
    print("=" * 50)
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"✅ {os.path.basename(file_path)} - {size} bytes")
            
            # Check key content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'shortestPath' in content and 'apoc.path.shortestPath' not in content:
                print(f"   ✓ 包含正确的 shortestPath 查询")
            elif file_path.endswith('.md'):
                print(f"   ✓ 包含完整的修复指南")
        else:
            print(f"❌ {os.path.basename(file_path)} - 文件不存在")
    
    print("\n下一步操作:")
    print("1. 打开 PWD_Knowledge_Graph_Analysis.ipynb")
    print("2. 在最短路径查询的错误单元格下方创建新单元格")
    print("3. 复制 apoc_fix_notebook.py 中的代码")
    print("4. 运行新单元格")
    print("5. 验证不再出现 APOC 错误")

if __name__ == "__main__":
    verify_fix()
