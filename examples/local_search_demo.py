#!/usr/bin/env python3
"""
Local Search 功能演示脚本

演示如何使用 GraphRAG 的 Local Search 功能进行精确问答
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from graph_rag import GraphRAG

def load_data():
    """加载已处理的数据"""
    try:
        concepts_df = pd.read_csv('output/concepts.csv')
        relationships_df = pd.read_csv('output/relationships.csv')
        return concepts_df, relationships_df
    except FileNotFoundError:
        print("错误：未找到数据文件")
        print("请先运行主流程生成数据：bash start.sh")
        return None, None

def main():
    print("="*70)
    print("  Local Search 功能演示")
    print("="*70)
    print()
    
    # 加载数据
    print("[1/3] 加载数据...")
    concepts_df, relationships_df = load_data()
    
    if concepts_df is None:
        return 1
    
    print(f"  ✓ 已加载 {len(concepts_df)} 个概念")
    print(f"  ✓ 已加载 {len(relationships_df)} 条关系")
    print()
    
    # 初始化 GraphRAG
    print("[2/3] 初始化 GraphRAG...")
    graph_rag = GraphRAG(
        model="qwen2.5-coder:7b",
        embedding_model="BAAI/bge-m3"
    )
    print("  ✓ GraphRAG 初始化完成")
    print()
    
    # 构建 Local Search 索引
    print("[3/3] 构建 Local Search 索引...")
    try:
        graph_rag.build_local_search_index(concepts_df)
        print("  ✓ 索引构建完成")
    except Exception as e:
        print(f"  ✗ 索引构建失败: {e}")
        print("  提示: 请确保已安装 transformers 和 torch")
        return 1
    
    print()
    print("="*70)
    print("  开始查询演示")
    print("="*70)
    print()
    
    # 测试查询
    test_queries = [
        "阿维菌素对松褐天牛有什么作用？",
        "松材线虫的传播途径是什么？",
        "马尾松和黑松哪个更容易感染？",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n查询 {i}: {query}")
        print("-"*70)
        
        try:
            result = graph_rag.local_search(
                query=query,
                concepts_df=concepts_df,
                relationships_df=relationships_df,
                top_k=5,
                max_hops=2
            )
            
            print(f"\n相关节点 (Top-{len(result['relevant_nodes'])}):")
            for node, score in result['relevant_nodes']:
                print(f"  • {node} (相似度: {score:.3f})")
            
            print(f"\n子图规模: {result['subgraph_size']} 个节点")
            print(f"\n答案:\n{result['answer']}")
            
        except Exception as e:
            print(f"查询失败: {e}")
    
    print("\n" + "="*70)
    print("  演示完成")
    print("="*70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
