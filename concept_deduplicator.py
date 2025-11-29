#!/usr/bin/env python3
"""
Embedding-based Concept Deduplication Module
Uses semantic embeddings to identify and merge similar concepts
"""

import logging
from typing import List, Dict, Tuple, Set
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering

logger = logging.getLogger(__name__)


# 类别标准化映射 (统一为中文)
CATEGORY_MAPPING = {
    # 英文到中文
    'disease': '疾病',
    'pathogen': '病原',
    'organism': '生物',
    'host': '寄主',
    'vector': '媒介',
    'symptom': '症状',
    'treatment': '防治',
    'environment': '环境',
    'location': '地点',
    'mechanism': '机制',
    'process': '过程',
    'factor': '因素',
    'compound': '化合物',
    'misc': '其他',
    # 保持中文不变
    '疾病': '疾病',
    '病原': '病原',
    '生物': '生物',
    '寄主': '寄主',
    '媒介': '媒介',
    '症状': '症状',
    '防治': '防治',
    '环境': '环境',
    '地点': '地点',
    '机制': '机制',
    '过程': '过程',
    '因素': '因素',
    '化合物': '化合物',
    '其他': '其他',
}


class EmbeddingProvider:
    """Abstract base class for embedding providers"""
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for texts"""
        raise NotImplementedError


class BGE_M3_Embedder(EmbeddingProvider):
    """
    BGE-M3 embedding provider supporting dense+sparse hybrid retrieval
    v2.2 feature: 升级至 BAAI/bge-m3 以支持混合检索
    """
    
    def __init__(self, model_name: str = "BAAI/bge-m3", device=None):
        try:
            from sentence_transformers import SentenceTransformer
            import os
            
            # 设置离线模式环境变量（避免网络检查）
            os.environ['HF_HUB_OFFLINE'] = '1'
            os.environ['TRANSFORMERS_OFFLINE'] = '1'
            
            # 尝试从本地缓存加载
            logger.info(f"Loading BGE-M3 model (offline mode): {model_name}")
            self.model = SentenceTransformer(model_name, device=device)
            self.model_name = model_name
            logger.info(f"✓ Loaded BGE-M3 model successfully from local cache")
        except Exception as e:
            logger.error(f"Failed to load BGE-M3: {e}")
            raise
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """生成密集向量 embeddings"""
        if not texts:
            return np.array([])
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return np.array(embeddings)
    
    def embed_sparse(self, texts: List[str]) -> List[Dict]:
        """生成稀疏向量 embeddings (BGE-M3 特有)"""
        # 简化实现：使用 encode 获取稀疏表示
        # 实际 BGE-M3 可以通过特定参数获取 sparse embedding
        dense_embeddings = self.embed(texts)
        # 这里返回密集向量，实际应用可以调用 BGE-M3 的 sparse 接口
        return [{"dense": emb} for emb in dense_embeddings]
    
    def hybrid_similarity(self, text1: str, text2: str, alpha: float = 0.7) -> float:
        """
        混合相似度计算: alpha * dense_sim + (1-alpha) * sparse_sim
        
        Args:
            text1, text2: 待比较文本
            alpha: 密集向量权重 (0-1)
        """
        # Dense similarity
        emb1 = self.embed([text1])
        emb2 = self.embed([text2])
        dense_sim = cosine_similarity(emb1, emb2)[0][0]
        
        # Sparse similarity (简化版，实际可用 BM25 等)
        # 这里使用词级别的 Jaccard 相似度作为稀疏替代
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            sparse_sim = 0.0
        else:
            sparse_sim = len(words1 & words2) / len(words1 | words2)
        
        return alpha * dense_sim + (1 - alpha) * sparse_sim


class SentenceTransformerEmbedding(EmbeddingProvider):
    """Embedding provider using sentence-transformers"""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-MiniLM-L6-v2"):
        """
        Initialize with sentence-transformers model
        
        Args:
            model_name: HuggingFace model identifier
        """
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except ImportError:
            logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
            raise
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using sentence-transformers"""
        return self.model.encode(texts, show_progress_bar=False)


class TfidfEmbedding(EmbeddingProvider):
    """Fallback embedding provider using TF-IDF"""
    
    def __init__(self):
        """Initialize TF-IDF vectorizer"""
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 3), max_features=100)
        logger.info("Using TF-IDF embeddings (fallback)")
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using TF-IDF"""
        return self.vectorizer.fit_transform(texts).toarray()


class ConceptDeduplicator:
    """Deduplicate semantically similar concepts"""
    
    def __init__(self, embedding_provider: EmbeddingProvider = None, 
                 similarity_threshold: float = 0.85):
        """
        Initialize deduplicator
        
        Args:
            embedding_provider: Provider for generating embeddings
            similarity_threshold: Threshold for considering concepts as duplicates (0-1)
        """
        if embedding_provider is None:
            try:
                embedding_provider = SentenceTransformerEmbedding()
            except:
                logger.warning("Falling back to TF-IDF embeddings")
                embedding_provider = TfidfEmbedding()
        
        self.embedding_provider = embedding_provider
        self.similarity_threshold = similarity_threshold
    
    def deduplicate_concepts(self, concepts_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """
        Deduplicate concepts based on semantic similarity
        
        Args:
            concepts_df: DataFrame with columns ['entity', 'importance', 'category', ...]
        
        Returns:
            Tuple of (deduplicated_df, mapping_dict)
            - deduplicated_df: DataFrame with merged concepts
            - mapping_dict: Dict mapping original concepts to canonical forms
        """
        if concepts_df.empty:
            return concepts_df, {}
        
        logger.info(f"Deduplicating {len(concepts_df)} concepts...")
        
        # Get unique concepts
        unique_concepts = concepts_df['entity'].unique()
        
        if len(unique_concepts) < 2:
            return concepts_df, {concept: concept for concept in unique_concepts}
        
        # Generate embeddings
        embeddings = self.embedding_provider.embed(list(unique_concepts))
        
        # Calculate similarity matrix
        similarity_matrix = cosine_similarity(embeddings)
        
        # Find duplicate clusters
        clusters = self._cluster_similar_concepts(similarity_matrix, unique_concepts)
        
        # Create mapping from original to canonical concept
        mapping = self._create_concept_mapping(clusters, unique_concepts, concepts_df)
        
        # Apply mapping to deduplicate
        deduplicated_df = concepts_df.copy()
        deduplicated_df['entity'] = deduplicated_df['entity'].map(mapping)
        
        # Standardize categories before aggregation
        deduplicated_df['category'] = deduplicated_df['category'].map(
            lambda x: CATEGORY_MAPPING.get(str(x).lower(), '其他')
        )
        
        # Aggregate by canonical concept
        deduplicated_df = deduplicated_df.groupby('entity').agg({
            'importance': 'max',
            'category': lambda x: x.mode()[0] if not x.empty else '其他',
            'chunk_id': lambda x: ','.join(x.unique()),
            'type': 'first'
        }).reset_index()
        
        logger.info(f"Deduplicated to {len(deduplicated_df)} unique concepts")
        
        return deduplicated_df, mapping
    
    def _cluster_similar_concepts(self, similarity_matrix: np.ndarray, 
                                 concepts: np.ndarray) -> List[Set[str]]:
        """
        Cluster similar concepts using hierarchical clustering
        
        Args:
            similarity_matrix: Pairwise similarity matrix
            concepts: Array of concept strings
        
        Returns:
            List of concept clusters
        """
        # Convert similarity to distance
        distance_matrix = 1 - similarity_matrix
        
        # Hierarchical clustering
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1 - self.similarity_threshold,
            linkage='average'
        )
        
        labels = clustering.fit_predict(distance_matrix)
        
        # Group concepts by cluster
        clusters = {}
        for concept, label in zip(concepts, labels):
            if label not in clusters:
                clusters[label] = set()
            clusters[label].add(concept)
        
        return list(clusters.values())
    
    def _create_concept_mapping(self, clusters: List[Set[str]], 
                               concepts: np.ndarray,
                               concepts_df: pd.DataFrame) -> Dict[str, str]:
        """
        Create mapping from original to canonical concepts
        
        Canonical concept is the one with highest importance in the cluster
        
        Args:
            clusters: List of concept clusters
            concepts: Array of all concepts
            concepts_df: DataFrame with concept metadata
        
        Returns:
            Mapping dictionary
        """
        mapping = {}
        
        for cluster in clusters:
            if len(cluster) == 1:
                concept = list(cluster)[0]
                mapping[concept] = concept
            else:
                # Find canonical concept (highest importance)
                cluster_df = concepts_df[concepts_df['entity'].isin(cluster)]
                canonical = cluster_df.loc[cluster_df['importance'].idxmax(), 'entity']
                
                for concept in cluster:
                    mapping[concept] = canonical
        
        return mapping
    
    def normalize_concept_names(self, concepts_df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize concept names (pluralization, case, etc.)
        
        Args:
            concepts_df: DataFrame with concepts
        
        Returns:
            DataFrame with normalized concepts
        """
        normalized_df = concepts_df.copy()
        
        # Convert to lowercase (already done in extraction)
        normalized_df['entity'] = normalized_df['entity'].str.lower().str.strip()
        
        # Remove common suffixes
        suffixes = ['s', 'es', 'ed', 'ing', 'tion', 'ness']
        for suffix in suffixes:
            mask = normalized_df['entity'].str.endswith(suffix)
            # Keep original for now - more sophisticated stemming can be added
        
        # Remove duplicates after normalization
        normalized_df = normalized_df.drop_duplicates(subset=['entity'])
        
        return normalized_df


class RelationshipDeduplicator:
    """Deduplicate relationships based on concept deduplication"""
    
    @staticmethod
    def update_relationships(relationships_df: pd.DataFrame, 
                            concept_mapping: Dict[str, str]) -> pd.DataFrame:
        """
        Update relationships to use canonical concept names
        
        Args:
            relationships_df: DataFrame with relationships
            concept_mapping: Mapping from original to canonical concepts
        
        Returns:
            Updated relationships DataFrame
        """
        updated_df = relationships_df.copy()
        
        # Apply mapping to both nodes
        updated_df['node_1'] = updated_df['node_1'].map(
            lambda x: concept_mapping.get(x, x)
        )
        updated_df['node_2'] = updated_df['node_2'].map(
            lambda x: concept_mapping.get(x, x)
        )
        
        # Remove self-loops
        updated_df = updated_df[updated_df['node_1'] != updated_df['node_2']]
        
        # Aggregate duplicate relationships
        aggregated = updated_df.groupby(['node_1', 'node_2']).agg({
            'weight': 'sum',
            'edge': lambda x: ' | '.join(x.unique()),
            'chunk_id': lambda x: ','.join(x.unique()),
            'source': lambda x: ','.join(x.unique())
        }).reset_index()
        
        # Normalize weights
        max_weight = aggregated['weight'].max()
        if max_weight > 0:
            aggregated['weight'] = aggregated['weight'] / max_weight
        
        return aggregated


class ConceptImportanceFilter:
    """Filter out redundant or outlier concepts"""
    
    # 过于通用的概念列表（需要过滤）
    GENERIC_CONCEPTS = {
        'factor', 'factors', 'mechanism', 'mechanisms', 'process', 'processes',
        'method', 'methods', 'approach', 'approaches', 'system', 'systems',
        'compound', 'compounds', 'disease', 'diseases', 'organism', 'organisms',
        'study', 'studies', 'research', 'analysis', 'result', 'results',
        '因素', '机制', '过程', '方法', '系统', '化合物', '疾病', '生物',
        '研究', '分析', '结果', '影响', '作用', '效果', '现象', '情况',
    }
    
    @staticmethod
    def filter_concepts(concepts_df: pd.DataFrame, 
                       relationships_df: pd.DataFrame,
                       min_importance: int = 2,
                       min_connections: int = 1) -> pd.DataFrame:
        """
        Filter concepts based on importance and connectivity
        
        Args:
            concepts_df: DataFrame with concepts
            relationships_df: DataFrame with relationships
            min_importance: Minimum importance threshold (1-5)
            min_connections: Minimum number of relationships required
        
        Returns:
            Filtered concepts DataFrame
        """
        filtered_df = concepts_df.copy()
        
        # Filter out generic concepts
        initial_count = len(filtered_df)
        filtered_df = filtered_df[
            ~filtered_df['entity'].str.lower().isin(ConceptImportanceFilter.GENERIC_CONCEPTS)
        ]
        generic_filtered = initial_count - len(filtered_df)
        if generic_filtered > 0:
            logger.info(f"Filtered {generic_filtered} generic concepts")
        
        # Filter by importance
        filtered_df = filtered_df[filtered_df['importance'] >= min_importance]
        
        # Filter by connectivity
        if not relationships_df.empty:
            connected_concepts = set(relationships_df['node_1'].unique()) | \
                               set(relationships_df['node_2'].unique())
            
            # Count connections per concept
            connection_counts = {}
            for concept in filtered_df['entity']:
                count = len(relationships_df[
                    (relationships_df['node_1'] == concept) | 
                    (relationships_df['node_2'] == concept)
                ])
                connection_counts[concept] = count
            
            # Keep only concepts with minimum connections
            filtered_df = filtered_df[
                filtered_df['entity'].map(connection_counts) >= min_connections
            ]
        
        logger.info(f"Filtered concepts: {len(concepts_df)} -> {len(filtered_df)}")
        
        return filtered_df
