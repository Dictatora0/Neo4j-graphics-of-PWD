#!/usr/bin/env python3
"""
GraphRAG Module - Community Detection & Summarization
基于 Microsoft GraphRAG 思想的社区检测和摘要生成模块

核心功能:
1. 社区检测: 使用 Louvain/Leiden 算法识别图谱中的社区结构
2. 社区摘要: 使用 LLM 为每个社区生成综合性摘要
3. 全局查询: 支持基于社区摘要的全局性问题回答

优势:
- 解决单一三元组无法回答的全局性问题
- 提供多层次的知识组织结构
- 支持更复杂的知识推理
"""

import json
import logging
from typing import List, Dict, Tuple, Optional, Set
import pandas as pd
import numpy as np
import requests
from collections import defaultdict

logger = logging.getLogger(__name__)

# 尝试导入图分析库
try:
    import networkx as nx
    from networkx.algorithms import community as nx_community
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logger.warning("NetworkX 不可用,社区检测功能受限")

try:
    import igraph as ig
    IGRAPH_AVAILABLE = True
except ImportError:
    IGRAPH_AVAILABLE = False
    logger.warning("igraph 不可用,Leiden 算法不可用")


class CommunityDetector:
    """
    社区检测器 - 识别知识图谱中的社区结构
    
    支持算法:
    - Louvain: 快速模块度优化算法 (需要 NetworkX)
    - Leiden: 改进的 Louvain 算法 (需要 igraph)
    - Label Propagation: 标签传播算法 (需要 NetworkX)
    - Connected Components: 连通分量 (基础算法,无需额外依赖)
    """
    
    def __init__(self, algorithm: str = 'louvain'):
        """
        Args:
            algorithm: 社区检测算法 ('louvain', 'leiden', 'label_propagation', 'connected_components')
        """
        self.algorithm = algorithm.lower()
        
        if self.algorithm == 'louvain' and not NETWORKX_AVAILABLE:
            logger.warning("NetworkX 不可用,回退到 connected_components")
            self.algorithm = 'connected_components'
        
        if self.algorithm == 'leiden' and not IGRAPH_AVAILABLE:
            logger.warning("igraph 不可用,回退到 louvain")
            self.algorithm = 'louvain'
        
        logger.info(f"社区检测算法: {self.algorithm}")
    
    def detect_communities(self, concepts_df: pd.DataFrame, 
                          relationships_df: pd.DataFrame) -> Dict[int, List[str]]:
        """
        检测知识图谱中的社区
        
        Args:
            concepts_df: 概念 DataFrame
            relationships_df: 关系 DataFrame
        
        Returns:
            社区字典 {community_id: [entity_list]}
        """
        if concepts_df.empty or relationships_df.empty:
            logger.warning("输入数据为空,无法检测社区")
            return {}
        
        logger.info(f"开始社区检测: {len(concepts_df)} 概念, {len(relationships_df)} 关系")
        
        if self.algorithm == 'louvain':
            return self._detect_louvain(concepts_df, relationships_df)
        elif self.algorithm == 'leiden':
            return self._detect_leiden(concepts_df, relationships_df)
        elif self.algorithm == 'label_propagation':
            return self._detect_label_propagation(concepts_df, relationships_df)
        else:
            return self._detect_connected_components(concepts_df, relationships_df)
    
    def _build_networkx_graph(self, concepts_df: pd.DataFrame, 
                             relationships_df: pd.DataFrame) -> nx.Graph:
        """构建 NetworkX 图"""
        G = nx.Graph()
        
        # 添加节点
        for _, row in concepts_df.iterrows():
            G.add_node(
                row['entity'],
                importance=row.get('importance', 1),
                category=row.get('category', 'misc')
            )
        
        # 添加边
        for _, row in relationships_df.iterrows():
            node1 = row['node_1']
            node2 = row['node_2']
            weight = row.get('weight', 1.0)
            
            if node1 in G.nodes and node2 in G.nodes:
                G.add_edge(node1, node2, weight=weight, edge_type=row.get('edge', 'related'))
        
        logger.info(f"构建图谱: {G.number_of_nodes()} 节点, {G.number_of_edges()} 边")
        return G
    
    def _detect_louvain(self, concepts_df: pd.DataFrame, 
                       relationships_df: pd.DataFrame) -> Dict[int, List[str]]:
        """Louvain 社区检测"""
        if not NETWORKX_AVAILABLE:
            return self._detect_connected_components(concepts_df, relationships_df)
        
        G = self._build_networkx_graph(concepts_df, relationships_df)
        
        # Louvain 算法
        communities_generator = nx_community.louvain_communities(G, weight='weight', seed=42)
        
        # 转换为字典格式
        communities = {}
        for i, community_set in enumerate(communities_generator):
            communities[i] = list(community_set)
        
        logger.info(f"Louvain 检测到 {len(communities)} 个社区")
        
        # 打印社区统计
        for comm_id, members in communities.items():
            logger.debug(f"  社区 {comm_id}: {len(members)} 个节点")
        
        return communities
    
    def _detect_leiden(self, concepts_df: pd.DataFrame, 
                      relationships_df: pd.DataFrame) -> Dict[int, List[str]]:
        """Leiden 社区检测 (需要 igraph)"""
        if not IGRAPH_AVAILABLE:
            return self._detect_louvain(concepts_df, relationships_df)
        
        # 构建 igraph 图
        entities = list(concepts_df['entity'].unique())
        entity_to_idx = {e: i for i, e in enumerate(entities)}
        
        edges = []
        weights = []
        for _, row in relationships_df.iterrows():
            node1 = row['node_1']
            node2 = row['node_2']
            if node1 in entity_to_idx and node2 in entity_to_idx:
                edges.append((entity_to_idx[node1], entity_to_idx[node2]))
                weights.append(row.get('weight', 1.0))
        
        g = ig.Graph(edges=edges)
        g.vs["name"] = entities
        
        # Leiden 算法
        partition = g.community_leiden(weights=weights, objective_function='modularity')
        
        # 转换为字典格式
        communities = {}
        for i, community_indices in enumerate(partition):
            communities[i] = [entities[idx] for idx in community_indices]
        
        logger.info(f"Leiden 检测到 {len(communities)} 个社区")
        return communities
    
    def _detect_label_propagation(self, concepts_df: pd.DataFrame, 
                                  relationships_df: pd.DataFrame) -> Dict[int, List[str]]:
        """标签传播社区检测"""
        if not NETWORKX_AVAILABLE:
            return self._detect_connected_components(concepts_df, relationships_df)
        
        G = self._build_networkx_graph(concepts_df, relationships_df)
        
        # 标签传播算法
        communities_generator = nx_community.label_propagation_communities(G)
        
        communities = {}
        for i, community_set in enumerate(communities_generator):
            communities[i] = list(community_set)
        
        logger.info(f"Label Propagation 检测到 {len(communities)} 个社区")
        return communities
    
    def _detect_connected_components(self, concepts_df: pd.DataFrame, 
                                    relationships_df: pd.DataFrame) -> Dict[int, List[str]]:
        """连通分量检测 (基础算法,无需额外库)"""
        # 构建邻接表
        adjacency = defaultdict(set)
        
        for _, row in relationships_df.iterrows():
            node1 = row['node_1']
            node2 = row['node_2']
            adjacency[node1].add(node2)
            adjacency[node2].add(node1)
        
        # 添加孤立节点
        for entity in concepts_df['entity']:
            if entity not in adjacency:
                adjacency[entity] = set()
        
        # BFS 查找连通分量
        visited = set()
        communities = {}
        community_id = 0
        
        for entity in adjacency:
            if entity in visited:
                continue
            
            # BFS
            component = []
            queue = [entity]
            visited.add(entity)
            
            while queue:
                current = queue.pop(0)
                component.append(current)
                
                for neighbor in adjacency[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            
            communities[community_id] = component
            community_id += 1
        
        logger.info(f"Connected Components 检测到 {len(communities)} 个社区")
        return communities


class CommunitySummarizer:
    """
    社区摘要生成器 - 使用 LLM 为社区生成综合摘要
    
    功能:
    1. 提取社区内的核心概念和关系
    2. 调用 LLM 生成自然语言摘要
    3. 生成社区标题和关键主题
    """
    
    def __init__(self, model: str, ollama_host: str):
        self.model = model
        self.ollama_host = ollama_host
        self.api_endpoint = f"{ollama_host}/api/generate"
    
    def _call_ollama(self, prompt: str, system_prompt: str = "", temperature: float = 0.3) -> Optional[str]:
        """调用 Ollama API"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "temperature": temperature,
                "num_ctx": 8192,
            }
            
            response = requests.post(self.api_endpoint, json=payload, timeout=180)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '').strip()
        except Exception as e:
            logger.error(f"Community Summarizer API error: {e}")
            return None
    
    def summarize_community(self, community_entities: List[str],
                           concepts_df: pd.DataFrame,
                           relationships_df: pd.DataFrame) -> Dict:
        """
        为单个社区生成摘要
        
        Args:
            community_entities: 社区成员实体列表
            concepts_df: 概念 DataFrame
            relationships_df: 关系 DataFrame
        
        Returns:
            {
                'title': str,  # 社区标题
                'summary': str,  # 详细摘要
                'core_concepts': List[str],  # 核心概念
                'themes': List[str],  # 主要主题
                'size': int  # 社区大小
            }
        """
        if not community_entities:
            return None
        
        # 提取社区内的概念信息
        community_concepts = concepts_df[concepts_df['entity'].isin(community_entities)]
        
        # 提取社区内的关系
        community_relations = relationships_df[
            (relationships_df['node_1'].isin(community_entities)) &
            (relationships_df['node_2'].isin(community_entities))
        ]
        
        # 识别核心概念 (importance 最高的前5个)
        core_concepts = community_concepts.nlargest(
            min(5, len(community_concepts)), 
            'importance'
        )['entity'].tolist()
        
        # 构建社区知识上下文
        concepts_info = []
        for _, row in community_concepts.head(10).iterrows():
            concepts_info.append(f"- {row['entity']} ({row.get('category', 'unknown')}类, 重要性: {row.get('importance', 1)})")
        
        relations_info = []
        for _, row in community_relations.head(15).iterrows():
            relations_info.append(f"- {row['node_1']} → {row['edge']} → {row['node_2']}")
        
        # LLM 摘要提示
        system_prompt = """你是松材线虫病知识图谱分析专家。你的任务是为知识图谱中的一个社区(主题集群)生成简洁的摘要。

## 任务
1. 理解社区中的核心概念和关系
2. 识别主要主题 (如"病原传播机制"、"防治措施体系"等)
3. 生成一个简洁的标题(不超过15字)
4. 生成一段综合性摘要(80-150字),描述这个社区的核心知识

## 输出格式
{
  "title": "社区标题",
  "summary": "详细摘要",
  "themes": ["主题1", "主题2"]
}"""
        
        user_prompt = f"""请为以下知识社区生成摘要:

**社区规模**: {len(community_entities)} 个概念

**核心概念**:
{chr(10).join(concepts_info[:8])}

**主要关系**:
{chr(10).join(relations_info[:10])}

请输出 JSON 格式的摘要。"""
        
        response = self._call_ollama(user_prompt, system_prompt, temperature=0.3)
        
        if not response:
            logger.warning(f"社区摘要生成失败,使用规则生成")
            return self._rule_based_summary(community_entities, community_concepts, community_relations)
        
        try:
            summary_data = json.loads(response)
            
            return {
                'title': summary_data.get('title', f"社区 (含 {len(community_entities)} 个概念)"),
                'summary': summary_data.get('summary', ''),
                'core_concepts': core_concepts,
                'themes': summary_data.get('themes', []),
                'size': len(community_entities)
            }
        except json.JSONDecodeError:
            logger.error("JSON 解析失败,使用规则生成")
            return self._rule_based_summary(community_entities, community_concepts, community_relations)
    
    def _rule_based_summary(self, entities: List[str], concepts_df: pd.DataFrame, 
                           relations_df: pd.DataFrame) -> Dict:
        """基于规则的摘要生成"""
        # 统计类别分布
        category_counts = concepts_df['category'].value_counts().to_dict()
        main_category = max(category_counts, key=category_counts.get) if category_counts else 'mixed'
        
        # 核心概念
        core_concepts = concepts_df.nlargest(
            min(5, len(concepts_df)), 'importance'
        )['entity'].tolist()
        
        # 生成标题
        title = f"{main_category.upper()} 相关知识 ({len(entities)} 概念)"
        
        # 生成摘要
        summary = f"该社区包含 {len(entities)} 个概念,主要类别为 {main_category}。核心概念包括: {', '.join(core_concepts[:3])}。"
        
        return {
            'title': title,
            'summary': summary,
            'core_concepts': core_concepts,
            'themes': [main_category],
            'size': len(entities)
        }
    
    def summarize_all_communities(self, communities: Dict[int, List[str]],
                                  concepts_df: pd.DataFrame,
                                  relationships_df: pd.DataFrame) -> pd.DataFrame:
        """
        为所有社区生成摘要
        
        Returns:
            DataFrame with columns: [community_id, title, summary, core_concepts, themes, size]
        """
        logger.info(f"为 {len(communities)} 个社区生成摘要...")
        
        summaries = []
        
        for comm_id, members in communities.items():
            logger.debug(f"处理社区 {comm_id} ({len(members)} 成员)...")
            
            summary = self.summarize_community(members, concepts_df, relationships_df)
            
            if summary:
                summaries.append({
                    'community_id': comm_id,
                    **summary
                })
        
        summaries_df = pd.DataFrame(summaries)
        logger.info(f"社区摘要生成完成: {len(summaries_df)} 个社区")
        
        return summaries_df


class GraphRAG:
    """
    GraphRAG 主类 - 整合社区检测和摘要生成
    
    使用方法:
    ```python
    graph_rag = GraphRAG(model="qwen2.5-coder:14b", algorithm="louvain")
    communities_df = graph_rag.build_community_summaries(concepts_df, relationships_df)
    ```
    """
    
    def __init__(self, model: str, ollama_host: str = "http://localhost:11434",
                 algorithm: str = 'louvain'):
        self.detector = CommunityDetector(algorithm)
        self.summarizer = CommunitySummarizer(model, ollama_host)
    
    def build_community_summaries(self, concepts_df: pd.DataFrame,
                                  relationships_df: pd.DataFrame) -> pd.DataFrame:
        """
        构建社区摘要
        
        Args:
            concepts_df: 概念 DataFrame
            relationships_df: 关系 DataFrame
        
        Returns:
            社区摘要 DataFrame
        """
        # 1. 检测社区
        communities = self.detector.detect_communities(concepts_df, relationships_df)
        
        # 2. 生成摘要
        summaries_df = self.summarizer.summarize_all_communities(
            communities, concepts_df, relationships_df
        )
        
        return summaries_df


if __name__ == "__main__":
    # 测试 GraphRAG
    import sys
    
    # 模拟数据
    concepts_data = {
        'entity': ['松材线虫', '松褐天牛', '马尾松', '黑松', '阿维菌素', '噻虫啉'],
        'importance': [5, 5, 4, 4, 4, 4],
        'category': ['pathogen', 'vector', 'host', 'host', 'treatment', 'treatment']
    }
    
    relationships_data = {
        'node_1': ['松材线虫', '松褐天牛', '阿维菌素', '噻虫啉'],
        'node_2': ['马尾松', '松材线虫', '松褐天牛', '松材线虫'],
        'edge': ['感染', '传播', '防治', '杀灭'],
        'weight': [0.9, 0.9, 0.8, 0.8]
    }
    
    concepts_df = pd.DataFrame(concepts_data)
    relationships_df = pd.DataFrame(relationships_data)
    
    # 初始化 GraphRAG
    graph_rag = GraphRAG(
        model="qwen2.5-coder:14b",
        algorithm="louvain"
    )
    
    # 构建社区摘要
    print("\n=== GraphRAG 社区检测与摘要 ===")
    summaries_df = graph_rag.build_community_summaries(concepts_df, relationships_df)
    
    print(f"\n检测到 {len(summaries_df)} 个社区:\n")
    for _, row in summaries_df.iterrows():
        print(f"## {row['title']}")
        print(f"摘要: {row['summary']}")
        print(f"核心概念: {', '.join(row['core_concepts'])}")
        print(f"主题: {', '.join(row['themes'])}")
        print(f"规模: {row['size']} 个概念\n")
