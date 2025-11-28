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
from transformers import AutoTokenizer, AutoModel

logger = logging.getLogger(__name__)

# 类别标准化映射 (统一为中文)
CATEGORY_MAPPING = {
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



# --- Embedding Provider with BGE-M3 Dense+Sparse ---
import torch
from transformers import AutoTokenizer, AutoModel

class BGE_M3_Embedder:
    """BGE-M3 embedding provider supporting dense+sparse hybrid retrieval"""
    def __init__(self, model_name: str = "BAAI/bge-m3", device=None):
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name)
            self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            self.model.eval()
            logger.info(f"Loaded BGE-M3 model: {model_name}")
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            raise

    @torch.no_grad()
    def embed(self, texts: List[str]) -> dict:
        """
        Returns: {"dense": np.ndarray, "sparse": np.ndarray or None}
        """
        inputs = self.tokenizer(texts, padding=True, truncation=True, return_tensors="pt").to(self.device)
        outputs = self.model(**inputs, output_hidden_states=True, return_dict=True)
        # Dense embedding
        dense_emb = outputs.pooler_output.cpu().numpy()
        # Sparse embedding (BGE-M3支持sparse_emb输出)
        sparse_emb = outputs.get("sparse_emb", None)
        if sparse_emb is not None:
            sparse_emb = sparse_emb.cpu().numpy()
        return {"dense": dense_emb, "sparse": sparse_emb}



# --- 混合相似度计算 ---
def hybrid_similarity(query_emb: dict, cand_emb: dict, alpha=0.7):
    """
    alpha: dense/sparse 加权
    query_emb, cand_emb: {"dense": ndarray, "sparse": ndarray or None}
    """
    dense_sim = cosine_similarity(query_emb["dense"], cand_emb["dense"])
    if query_emb["sparse"] is not None and cand_emb["sparse"] is not None:
        sparse_sim = np.matmul(query_emb["sparse"], cand_emb["sparse"].T)
        sim = alpha * dense_sim + (1 - alpha) * sparse_sim
    else:
        sim = dense_sim
    return sim



class ConceptDeduplicator:
    """Deduplicate semantically similar concepts using BGE-M3 hybrid retrieval"""
    def __init__(self, embedding_provider=None, similarity_threshold: float = 0.85, hybrid_alpha: float = 0.7):
        if embedding_provider is None:
            embedding_provider = BGE_M3_Embedder()
        self.embedding_provider = embedding_provider
        self.similarity_threshold = similarity_threshold
        self.hybrid_alpha = hybrid_alpha

    def deduplicate_concepts(self, concepts_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        if concepts_df.empty:
            return concepts_df, {}
        logger.info(f"Deduplicating {len(concepts_df)} concepts...")
        unique_concepts = concepts_df['entity'].unique()
        if len(unique_concepts) < 2:
            return concepts_df, {concept: concept for concept in unique_concepts}
        # Hybrid embedding
        emb = self.embedding_provider.embed(list(unique_concepts))
        sim_matrix = hybrid_similarity(emb, emb, alpha=self.hybrid_alpha)
        clusters = self._cluster_similar_concepts(sim_matrix, unique_concepts)
        mapping = self._create_concept_mapping(clusters, unique_concepts, concepts_df)
        deduplicated_df = concepts_df.copy()
        deduplicated_df['entity'] = deduplicated_df['entity'].map(mapping)
        deduplicated_df['category'] = deduplicated_df['category'].map(
            lambda x: CATEGORY_MAPPING.get(str(x).lower(), '其他')
        )
        deduplicated_df = deduplicated_df.groupby('entity').agg({
            'importance': 'max',
            'category': lambda x: x.mode()[0] if not x.empty else '其他',
            'chunk_id': lambda x: ','.join(x.unique()),
            'type': 'first'
        }).reset_index()
        logger.info(f"Deduplicated to {len(deduplicated_df)} unique concepts")
        return deduplicated_df, mapping

    def enhance_domain_dict(self, new_terms: List[str], dict_path="config/domain_dict.json", sim_threshold=0.85):
        """
        自动扩充领域词典：用BGE-M3计算新词与词典词的相似度，发现新同义词并扩充
        """
        import json, os
        embedder = self.embedding_provider
        if os.path.exists(dict_path):
            with open(dict_path, "r", encoding="utf-8") as f:
                domain_dict = json.load(f)
        else:
            domain_dict = {}
        dict_terms = []
        term_to_cat = {}
        for cat, terms in domain_dict.items():
            for t in terms:
                dict_terms.append(t)
                term_to_cat[t] = cat
        if not dict_terms:
            dict_emb = embedder.embed(new_terms)
            dict_terms = new_terms
        else:
            dict_emb = embedder.embed(dict_terms)
        new_emb = embedder.embed(new_terms)
        sim_matrix = hybrid_similarity(new_emb, dict_emb, alpha=self.hybrid_alpha)
        for i, term in enumerate(new_terms):
            max_idx = np.argmax(sim_matrix[i])
            max_sim = sim_matrix[i, max_idx]
            if max_sim > sim_threshold:
                cat = term_to_cat[dict_terms[max_idx]]
                if term not in domain_dict[cat]:
                    domain_dict[cat].append(term)
            else:
                # 新增类别或归为“其他”
                domain_dict.setdefault("其他", []).append(term)
        # 去重
        for k in domain_dict:
            domain_dict[k] = list(sorted(set(domain_dict[k])))
        with open(dict_path, "w", encoding="utf-8") as f:
            json.dump(domain_dict, f, ensure_ascii=False, indent=2)
        logger.info(f"领域词典已扩充，现有类别: {list(domain_dict.keys())}")
        return domain_dict
    
    def _cluster_similar_concepts(self, similarity_matrix: np.ndarray, concepts: np.ndarray) -> List[Set[str]]:
        distance_matrix = 1 - similarity_matrix
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1 - self.similarity_threshold,
            linkage='average'
        )
        labels = clustering.fit_predict(distance_matrix)
        clusters = {}
        for concept, label in zip(concepts, labels):
            clusters.setdefault(label, set()).add(concept)
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
        filtered_df = filtered_df[~filtered_df['entity'].str.lower().isin(ConceptImportanceFilter.GENERIC_CONCEPTS)]
        generic_filtered = initial_count - len(filtered_df)
        if generic_filtered > 0:
            logger.info(f"Filtered {generic_filtered} generic concepts")
        
        # Filter by importance
        filtered_df = filtered_df[filtered_df['importance'] >= min_importance]
        
        # Filter by connectivity
        if not relationships_df.empty:
            connected_concepts = set(relationships_df['node_1'].unique()) | set(relationships_df['node_2'].unique())
            
            # Count connections per concept
            connection_counts = {}
            for concept in filtered_df['entity']:
                count = len(relationships_df[(relationships_df['node_1'] == concept) | (relationships_df['node_2'] == concept)])
                connection_counts[concept] = count
            
            # Keep only concepts with minimum connections
            filtered_df = filtered_df[filtered_df['entity'].map(connection_counts) >= min_connections]
        
        logger.info(f"Filtered concepts: {len(concepts_df)} -> {len(filtered_df)}")
        
        return filtered_df
