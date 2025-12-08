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
        # 统一转为小写,方便后续分支判断
        self.algorithm = algorithm.lower()
        
        # 如果环境缺少 NetworkX/igraph,自动降级到可用算法,保证功能可用性
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
        
        # 根据初始化时确定的算法分支到对应实现
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
        
        # 添加节点: 只要在概念表里出现过的 entity 都作为节点加入,同时记录重要性和类别
        for _, row in concepts_df.iterrows():
            G.add_node(
                row['entity'],
                importance=row.get('importance', 1),
                category=row.get('category', 'misc')
            )
        
        # 添加边: 仅当两端节点都存在于图中时才连边,避免脏数据引入孤立引用
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
        # 构建邻接表: 简单 undirected 图,用来在没有图算法库时兜底
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
        
        # BFS 查找连通分量: 每次从一个未访问节点出发,扩展出一个社区
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
        
        # 识别核心概念: 直接按 importance 排序取前几名,作为摘要里的“主角”
        core_concepts = community_concepts.nlargest(
            min(5, len(community_concepts)), 
            'importance'
        )['entity'].tolist()
        
        # 构建社区知识上下文: 选取部分概念和关系,作为 LLM 摘要的输入提示
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
            # 当 LLM 没有按预期返回 JSON 时,退回到规则摘要,保证功能可用
            logger.error("JSON 解析失败,使用规则生成")
            return self._rule_based_summary(community_entities, community_concepts, community_relations)
    
    def _rule_based_summary(self, entities: List[str], concepts_df: pd.DataFrame, 
                           relations_df: pd.DataFrame) -> Dict:
        """基于规则的摘要生成"""
        # 统计类别分布: 用出现次数最多的类别粗略代表该社区主题
        category_counts = concepts_df['category'].value_counts().to_dict()
        main_category = max(category_counts, key=category_counts.get) if category_counts else 'mixed'
        
        # 核心概念: 同样按 importance 取前若干个
        core_concepts = concepts_df.nlargest(
            min(5, len(concepts_df)), 'importance'
        )['entity'].tolist()
        
        # 生成标题
        title = f"{main_category.upper()} 相关知识 ({len(entities)} 概念)"
        
        # 生成摘要: 提供一个可以直接展示的简要说明,即使没有 LLM 也能工作
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


class LocalSearchEngine:
    """
    Local Search 引擎 - 基于向量索引的精确检索
    
    功能:
    1. 为每个节点生成 Embedding 索引
    2. 根据用户查询检索 Top-K 相关节点
    3. 扩展子图 (1-2跳)
    4. 使用 LLM 基于子图生成答案
    """
    
    def __init__(self, model: str, ollama_host: str = "http://localhost:11434",
                 embedding_model: str = "BAAI/bge-m3"):
        """
        Args:
            model: LLM 模型名称
            ollama_host: Ollama 服务地址
            embedding_model: Embedding 模型名称
        """
        self.model = model
        self.ollama_host = ollama_host
        self.api_endpoint = f"{ollama_host}/api/generate"
        
        # 初始化 Embedding 模型
        try:
            from FlagEmbedding import BGEM3FlagModel
            logger.info(f"Loading embedding model: {embedding_model}")
            self.embedder = BGEM3FlagModel(
                embedding_model,
                use_fp16=True,
                normalize_embeddings=True
            )
            logger.info("✓ Embedding model loaded")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
        
        # 节点索引：{entity: embedding}
        self.node_index = {}
    
    def build_node_index(self, concepts_df: pd.DataFrame) -> None:
        """
        为所有节点构建 Embedding 索引
        
        Args:
            concepts_df: 概念 DataFrame
        """
        logger.info(f"Building node index for {len(concepts_df)} concepts...")
        
        entities = concepts_df['entity'].tolist()
        
        # 批量生成 Embedding
        embeddings = self.embedder.encode(
            entities,
            batch_size=32,
            max_length=512,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False
        )['dense_vecs']
        
        # 构建索引
        for entity, embedding in zip(entities, embeddings):
            self.node_index[entity] = embedding
        
        logger.info(f"✓ Node index built: {len(self.node_index)} nodes")
    
    def search_relevant_nodes(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        检索与查询最相关的 Top-K 节点
        
        Args:
            query: 用户查询
            top_k: 返回节点数量
        
        Returns:
            [(entity, similarity_score), ...]
        """
        if not self.node_index:
            logger.error("Node index not built. Call build_node_index() first.")
            return []
        
        # 生成查询 Embedding
        query_embedding = self.embedder.encode(
            [query],
            batch_size=1,
            max_length=512,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False
        )['dense_vecs'][0]
        
        # 计算相似度
        similarities = []
        for entity, node_embedding in self.node_index.items():
            # 余弦相似度
            similarity = np.dot(query_embedding, node_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(node_embedding)
            )
            similarities.append((entity, float(similarity)))
        
        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def expand_subgraph(self, seed_nodes: List[str], 
                       relationships_df: pd.DataFrame,
                       max_hops: int = 2) -> Tuple[Set[str], pd.DataFrame]:
        """
        从种子节点扩展子图
        
        Args:
            seed_nodes: 种子节点列表
            relationships_df: 关系 DataFrame
            max_hops: 最大跳数
        
        Returns:
            (subgraph_nodes, subgraph_relationships)
        """
        subgraph_nodes = set(seed_nodes)
        current_nodes = set(seed_nodes)
        
        # 多跳扩展
        for hop in range(max_hops):
            next_nodes = set()
            
            for node in current_nodes:
                # 查找直接连接的节点
                neighbors = relationships_df[
                    (relationships_df['node_1'] == node) | 
                    (relationships_df['node_2'] == node)
                ]
                
                for _, row in neighbors.iterrows():
                    next_nodes.add(row['node_1'])
                    next_nodes.add(row['node_2'])
            
            subgraph_nodes.update(next_nodes)
            current_nodes = next_nodes
            
            if not next_nodes:
                break
        
        # 提取子图关系
        subgraph_rels = relationships_df[
            (relationships_df['node_1'].isin(subgraph_nodes)) &
            (relationships_df['node_2'].isin(subgraph_nodes))
        ]
        
        logger.debug(f"Expanded subgraph: {len(subgraph_nodes)} nodes, {len(subgraph_rels)} relationships")
        
        return subgraph_nodes, subgraph_rels
    
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
            logger.error(f"Local Search API error: {e}")
            return None
    
    def answer_query(self, query: str, 
                    concepts_df: pd.DataFrame,
                    relationships_df: pd.DataFrame,
                    top_k: int = 5,
                    max_hops: int = 2) -> Dict:
        """
        基于 Local Search 回答用户查询
        
        Args:
            query: 用户查询
            concepts_df: 概念 DataFrame
            relationships_df: 关系 DataFrame
            top_k: 检索节点数
            max_hops: 子图扩展跳数
        
        Returns:
            {
                'query': str,
                'relevant_nodes': List[Tuple[str, float]],
                'subgraph_size': int,
                'answer': str
            }
        """
        logger.info(f"Processing query: {query}")
        
        # 1. 检索相关节点
        relevant_nodes = self.search_relevant_nodes(query, top_k)
        
        if not relevant_nodes:
            return {
                'query': query,
                'relevant_nodes': [],
                'subgraph_size': 0,
                'answer': '未找到相关信息。'
            }
        
        logger.info(f"Found {len(relevant_nodes)} relevant nodes")
        for node, score in relevant_nodes:
            logger.debug(f"  - {node}: {score:.3f}")
        
        # 2. 扩展子图
        seed_nodes = [node for node, _ in relevant_nodes]
        subgraph_nodes, subgraph_rels = self.expand_subgraph(
            seed_nodes, relationships_df, max_hops
        )
        
        # 3. 构建上下文
        context_nodes = []
        for node in list(subgraph_nodes)[:20]:  # 限制上下文大小
            node_info = concepts_df[concepts_df['entity'] == node]
            if not node_info.empty:
                row = node_info.iloc[0]
                context_nodes.append(
                    f"- {row['entity']} ({row.get('category', 'unknown')}类, 重要性: {row.get('importance', 1)})"
                )
        
        context_rels = []
        for _, row in subgraph_rels.head(30).iterrows():  # 限制关系数量
            context_rels.append(
                f"- {row['node_1']} → {row['edge']} → {row['node_2']}"
            )
        
        # 4. 生成答案
        system_prompt = """你是松材线虫病知识图谱问答助手。你的任务是基于提供的知识子图回答用户问题。

## 任务
1. 仔细阅读提供的概念和关系
2. 基于知识图谱中的信息回答问题
3. 如果信息不足，请明确说明
4. 回答要简洁、准确、有依据

## 输出要求
- 直接回答问题，不要添加额外的客套话
- 引用具体的实体和关系来支持你的答案
- 如果有多个相关实体，请列举说明"""
        
        user_prompt = f"""用户问题: {query}

**相关概念**:
{chr(10).join(context_nodes[:15])}

**相关关系**:
{chr(10).join(context_rels[:20])}

请基于以上知识图谱信息回答问题。"""
        
        answer = self._call_ollama(user_prompt, system_prompt, temperature=0.2)
        
        if not answer:
            answer = "抱歉，生成答案失败。请稍后重试。"
        
        return {
            'query': query,
            'relevant_nodes': relevant_nodes,
            'subgraph_size': len(subgraph_nodes),
            'answer': answer
        }


class GraphRAG:
    """
    GraphRAG 主类 - 整合社区检测、摘要生成和 Local Search
    
    使用方法:
    ```python
    # Global Search (社区摘要)
    graph_rag = GraphRAG(model="qwen2.5-coder:14b", algorithm="louvain")
    communities_df = graph_rag.build_community_summaries(concepts_df, relationships_df)
    
    # Local Search (精确检索)
    graph_rag.build_local_search_index(concepts_df)
    result = graph_rag.local_search("阿维菌素对松褐天牛有什么作用？", concepts_df, relationships_df)
    ```
    """
    
    def __init__(self, model: str, ollama_host: str = "http://localhost:11434",
                 algorithm: str = 'louvain', embedding_model: str = "BAAI/bge-m3"):
        self.detector = CommunityDetector(algorithm)
        self.summarizer = CommunitySummarizer(model, ollama_host)
        self.local_search_engine = LocalSearchEngine(model, ollama_host, embedding_model)
    
    def build_community_summaries(self, concepts_df: pd.DataFrame,
                                  relationships_df: pd.DataFrame) -> pd.DataFrame:
        """
        构建社区摘要 (Global Search)
        
        Args:
            concepts_df: 概念 DataFrame
            relationships_df: 关系 DataFrame
        
        Returns:
            社区摘要 DataFrame
        """
        # 1. 检测社区: 基于关系结构把图拆成若干主题簇
        communities = self.detector.detect_communities(concepts_df, relationships_df)
        
        # 2. 生成摘要: 为每个社区生成 title + summary,最终汇总成 DataFrame
        summaries_df = self.summarizer.summarize_all_communities(
            communities, concepts_df, relationships_df
        )
        
        return summaries_df
    
    def build_local_search_index(self, concepts_df: pd.DataFrame) -> None:
        """
        为 Local Search 构建节点索引
        
        Args:
            concepts_df: 概念 DataFrame
        """
        self.local_search_engine.build_node_index(concepts_df)
    
    def local_search(self, query: str,
                    concepts_df: pd.DataFrame,
                    relationships_df: pd.DataFrame,
                    top_k: int = 5,
                    max_hops: int = 2) -> Dict:
        """
        Local Search - 基于向量检索回答精确问题
        
        Args:
            query: 用户查询
            concepts_df: 概念 DataFrame
            relationships_df: 关系 DataFrame
            top_k: 检索节点数
            max_hops: 子图扩展跳数
        
        Returns:
            {
                'query': str,
                'relevant_nodes': List[Tuple[str, float]],
                'subgraph_size': int,
                'answer': str
            }
        """
        return self.local_search_engine.answer_query(
            query, concepts_df, relationships_df, top_k, max_hops
        )


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
