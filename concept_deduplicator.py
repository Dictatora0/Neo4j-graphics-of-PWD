#!/usr/bin/env python3
"""基于向量表征的概念去重模块

通过语义向量 (embedding) 度量概念之间的相似度, 自动识别并合并含义接近的概念, 减少知识图谱中的冗余节点。

整体流程总览(从原始概念到最终保留概念):
原始概念列表
  ↓  (EmbeddingProvider/BGE_M3_Embedder 生成稠密向量)
语义向量矩阵
  ↓  (cosine_similarity 计算两两相似度)
相似度矩阵
  ↓  (AgglomerativeClustering 按阈值聚类)
概念簇 + 规范名映射
  ↓  (ConceptImportanceFilter 按重要性与连接度过滤)
最终保留的规范概念集合
"""

import logging
from typing import List, Dict, Tuple, Set, Optional
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
    """向量生成器抽象基类

    所有具体的 embedding 实现(BGE-M3、SentenceTransformer、TF-IDF 等)都应继承该类,并实现 `embed` 方法。
    """
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """为一组文本生成向量表示

        返回形状为 `[样本数, 向量维度]` 的 numpy 数组,每一行对应一条文本的向量表示。
        """
        raise NotImplementedError


class BGE_M3_Embedder(EmbeddingProvider):
    """BGE-M3 向量生成器(支持稠密/稀疏混合检索)

    说明:
    - **Dense Embedding(稠密向量)**: 每条文本被编码成一个高维浮点数组(如 1024 维),所有维度几乎都是非 0,适合做语义相似度计算。
    - **Sparse Embedding(稀疏向量)**: 大部分维度是 0,只有少数维度非 0,基于BM25类似的词项匹配，适合关键词级检索。
    - **ColBERT**: 多向量表示，每个token对应一个向量，用于精细粒度匹配。
    - 本实现使用FlagEmbedding库的BGEM3FlagModel，支持真实的dense+sparse+colbert三模态编码。
    """
    
    def __init__(self, model_name: str = "BAAI/bge-m3", device=None, use_fp16: bool = True):
        """
        Args:
            model_name: 模型名称或路径
            device: 设备 ('cuda', 'cpu', None为自动检测)
            use_fp16: 是否使用FP16加速(仅GPU)
        """
        try:
            # 优先尝试使用FlagEmbedding库（支持真实的sparse encoding）
            try:
                from FlagEmbedding import BGEM3FlagModel
                import os
                
                # 强制设置离线模式
                os.environ['HF_HUB_OFFLINE'] = '1'
                os.environ['TRANSFORMERS_OFFLINE'] = '1'
                os.environ['HF_DATASETS_OFFLINE'] = '1'
                
                logger.info(f"Loading BGE-M3 with FlagEmbedding (supports true sparse): {model_name}")
                
                # 尝试加载模型（优先使用本地缓存路径）
                try:
                    # 检查本地缓存目录
                    cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
                    model_cache_name = f"models--{model_name.replace('/', '--')}"
                    model_cache_path = os.path.join(cache_dir, model_cache_name)
                    
                    # 尝试使用本地路径
                    local_model_path = None
                    if os.path.exists(model_cache_path):
                        # 优先使用main目录
                        main_path = os.path.join(model_cache_path, "snapshots", "main")
                        if os.path.exists(main_path) and os.path.exists(os.path.join(main_path, "pytorch_model.bin")):
                            local_model_path = main_path
                            logger.info(f"Using local model from: {main_path}")
                        else:
                            # 尝试查找其他snapshot
                            snapshots_dir = os.path.join(model_cache_path, "snapshots")
                            if os.path.exists(snapshots_dir):
                                for snapshot in os.listdir(snapshots_dir):
                                    snapshot_path = os.path.join(snapshots_dir, snapshot)
                                    if os.path.exists(os.path.join(snapshot_path, "pytorch_model.bin")):
                                        local_model_path = snapshot_path
                                        logger.info(f"Using local model from: {snapshot_path}")
                                        break
                    
                    # 加载模型（使用本地路径或model ID）
                    model_path_or_id = local_model_path if local_model_path else model_name
                    
                    self.model = BGEM3FlagModel(
                        model_path_or_id,
                        devices=device,  # FlagEmbedding使用devices而不是device
                        use_fp16=use_fp16,
                        normalize_embeddings=True,
                    )
                    self.use_flag_embedding = True
                    logger.info(f"✓ Loaded BGE-M3 with FlagEmbedding (dense+sparse+colbert support)")
                    
                except Exception as load_error:
                    # 如果加载失败，记录详细错误并回退
                    logger.warning(f"FlagEmbedding load failed: {load_error}")
                    logger.warning("Falling back to SentenceTransformer...")
                    raise ImportError("FlagEmbedding load failed") from load_error
                
            except ImportError:
                # 回退到sentence-transformers（仅支持dense）
                logger.warning("FlagEmbedding not available, falling back to SentenceTransformer (dense only)")
                logger.warning("Install with: pip install FlagEmbedding")
                
                from sentence_transformers import SentenceTransformer
                import os
                
                os.environ['HF_HUB_OFFLINE'] = '1'
                os.environ['TRANSFORMERS_OFFLINE'] = '1'
                
                logger.info(f"Loading BGE-M3 with SentenceTransformer (dense only): {model_name}")
                self.model = SentenceTransformer(model_name, device=device)
                self.use_flag_embedding = False
                logger.info(f"✓ Loaded BGE-M3 with SentenceTransformer (dense only)")
            
            self.model_name = model_name
            
        except Exception as e:
            logger.error(f"Failed to load BGE-M3: {e}")
            raise
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """生成稠密向量(dense embedding)

        每条输入文本会被编码成一个 L2 归一化后的高维向量,可以直接用余弦相似度表示语义相近程度。
        """
        if not texts:
            return np.array([])
        
        if self.use_flag_embedding:
            # FlagEmbedding的接口
            embeddings = self.model.encode(
                texts,
                batch_size=12,
                max_length=8192,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False
            )['dense_vecs']
        else:
            # SentenceTransformer的接口
            embeddings = self.model.encode(texts, normalize_embeddings=True)
        
        return np.array(embeddings)
    
    def embed_sparse(self, texts: List[str]) -> List[Dict]:
        """生成稀疏向量(sparse embedding)

        真实实现说明:
        - 使用FlagEmbedding库时，直接调用BGE-M3的sparse encoding功能
        - Sparse向量格式: {token_id: weight}，类似BM25的词项匹配
        - 如果使用SentenceTransformer后退模式，则使用TF-IDF近似实现
        
        Returns:
            List[Dict]: 每个文本返回 {"indices": [...], "values": [...]}
        """
        if not texts:
            return []
        
        if self.use_flag_embedding:
            # 真实BGE-M3稀疏编码
            try:
                result = self.model.encode(
                    texts,
                    batch_size=12,
                    max_length=8192,
                    return_dense=False,
                    return_sparse=True,
                    return_colbert_vecs=False
                )['lexical_weights']
                
                # 转换为统一格式
                sparse_vecs = []
                for sparse_dict in result:
                    # sparse_dict格式: {token_id: weight}
                    indices = list(sparse_dict.keys())
                    values = list(sparse_dict.values())
                    sparse_vecs.append({
                        "indices": indices,
                        "values": values
                    })
                
                logger.debug(f"Generated {len(sparse_vecs)} sparse vectors (FlagEmbedding)")
                return sparse_vecs
                
            except Exception as e:
                logger.warning(f"Sparse encoding failed: {e}, using fallback")
                return self._fallback_sparse(texts)
        else:
            # SentenceTransformer回退模式：使用TF-IDF近似
            logger.debug("Using TF-IDF fallback for sparse vectors")
            return self._fallback_sparse(texts)
    
    def _fallback_sparse(self, texts: List[str]) -> List[Dict]:
        """回退模式：使用TF-IDF近似稀疏向量"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            
            # 使用TF-IDF生成稀疏表示
            vectorizer = TfidfVectorizer(
                max_features=5000,
                lowercase=True,
                token_pattern=r'(?u)\b\w+\b'  # 支持中文
            )
            tfidf_matrix = vectorizer.fit_transform(texts)
            
            sparse_vecs = []
            for i in range(len(texts)):
                row = tfidf_matrix[i]
                # 获取非零元素
                indices = row.indices.tolist()
                values = row.data.tolist()
                sparse_vecs.append({
                    "indices": indices,
                    "values": values
                })
            
            return sparse_vecs
            
        except Exception as e:
            logger.error(f"Fallback sparse encoding failed: {e}")
            # 最后的回退：返回空稀疏向量
            return [{"indices": [], "values": []} for _ in texts]
    
    def hybrid_similarity(self, text1: str, text2: str, alpha: float = 0.7) -> float:
        """
        计算两段文本的“混合相似度”: `alpha * dense_sim + (1-alpha) * sparse_sim`

        参数说明:
        - `text1`, `text2`: 待比较的两段文本。
        - `alpha`: 稠密相似度权重,取值范围 0-1。越接近 1 表示越依赖语义向量,越接近 0 表示越依赖词项匹配。

        专业术语解释:
        - `dense_sim`: 稠密向量相似度,余弦相似度(cosine similarity)。值域 [-1, 1]。
        - `sparse_sim`: 稀疏向量相似度,基于词项匹配分数。值域 [0, 1]。
        """
        # Dense similarity
        emb1 = self.embed([text1])
        emb2 = self.embed([text2])
        dense_sim = cosine_similarity(emb1, emb2)[0][0]
        
        # Sparse similarity (使用真实的稀疏向量或回退到TF-IDF)
        try:
            sparse_vecs = self.embed_sparse([text1, text2])
            sparse1 = sparse_vecs[0]
            sparse2 = sparse_vecs[1]
            
            # 计算稀疏向量相似度（使用内积）
            sparse_sim = self._sparse_dot_product(sparse1, sparse2)
            
        except Exception as e:
            logger.debug(f"Sparse similarity calculation failed: {e}, using Jaccard")
            # 回退到Jaccard
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            if not words1 or not words2:
                sparse_sim = 0.0
            else:
                sparse_sim = len(words1 & words2) / len(words1 | words2)
        
        return alpha * dense_sim + (1 - alpha) * sparse_sim
    
    def _sparse_dot_product(self, sparse1: Dict, sparse2: Dict) -> float:
        """计算两个稀疏向量的内积
        
        Args:
            sparse1, sparse2: {"indices": [...], "values": [...]}
        
        Returns:
            内积值 (已归一化)
        """
        try:
            # 建立索引到值的映射
            dict1 = {idx: val for idx, val in zip(sparse1.get("indices", []), sparse1.get("values", []))}
            dict2 = {idx: val for idx, val in zip(sparse2.get("indices", []), sparse2.get("values", []))}
            
            # 计算共同索引的内积
            common_indices = set(dict1.keys()) & set(dict2.keys())
            if not common_indices:
                return 0.0
            
            dot_product = sum(dict1[idx] * dict2[idx] for idx in common_indices)
            
            # 归一化 (使用L2范数)
            norm1 = sum(v**2 for v in dict1.values()) ** 0.5
            norm2 = sum(v**2 for v in dict2.values()) ** 0.5
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
            
        except Exception as e:
            logger.error(f"Sparse dot product failed: {e}")
            return 0.0


class SentenceTransformerEmbedding(EmbeddingProvider):
    """基于 sentence-transformers 库的通用向量生成器

    作为 BGE-M3 的替代方案,在无法使用 BGE-M3 或对混合检索没有强需求时使用。
    """
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-MiniLM-L6-v2"):
        """初始化 sentence-transformers 模型

        参数:
        - `model_name`: HuggingFace 上的模型名称,例如 `sentence-transformers/paraphrase-MiniLM-L6-v2`。
        """
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except ImportError:
            logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
            raise
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """使用 sentence-transformers 生成稠密向量"""
        return self.model.encode(texts, show_progress_bar=False)


class TfidfEmbedding(EmbeddingProvider):
    """基于 TF-IDF 的简易向量生成器(降级方案)

    当环境中无法使用深度学习模型时,退回到 TF-IDF 这种传统特征表示方式,牺牲一定语义能力换取可用性。
    """
    
    def __init__(self):
        """初始化 TF-IDF 向量器

        这里使用 字符 n-gram(2~3 字符长度) 的方式构造特征,对中英文混合文本更鲁棒。
        """
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 3), max_features=100)
        logger.info("Using TF-IDF embeddings (fallback)")
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """使用 TF-IDF 生成向量

        返回一个稀疏矩阵转成的 numpy 数组,每一行表示一条文本在 n-gram 特征空间中的权重分布。
        """
        return self.vectorizer.fit_transform(texts).toarray()


class CanonicalResolver:
    """实体标准化解析器 - 基于规则和外部知识库的实体对齐
    
    功能:
    1. 生物分类学拉丁名对齐（如 Bursaphelenchus xylophilus）
    2. 常见别名映射（如 "松材线虫" → "Bursaphelenchus xylophilus"）
    3. 外部知识库查询（可选：NCBI Taxonomy、Wikidata 等）
    4. 规则优先级：外部知识库 > 内置规则 > Embedding 相似度
    """
    
    # 内置生物分类学标准名映射
    BIOLOGICAL_CANONICAL_NAMES = {
        # 病原体
        '松材线虫': 'Bursaphelenchus xylophilus',
        '线虫': 'Bursaphelenchus xylophilus',
        'bursaphelenchus xylophilus': 'Bursaphelenchus xylophilus',
        'b. xylophilus': 'Bursaphelenchus xylophilus',
        'pine wood nematode': 'Bursaphelenchus xylophilus',
        'pwn': 'Bursaphelenchus xylophilus',
        
        # 媒介昆虫
        '松褐天牛': 'Monochamus alternatus',
        '天牛': 'Monochamus alternatus',
        'monochamus alternatus': 'Monochamus alternatus',
        'm. alternatus': 'Monochamus alternatus',
        'japanese pine sawyer': 'Monochamus alternatus',
        
        '云杉花墨天牛': 'Monochamus saltuarius',
        'monochamus saltuarius': 'Monochamus saltuarius',
        
        # 寄主植物
        '马尾松': 'Pinus massoniana',
        'pinus massoniana': 'Pinus massoniana',
        'masson pine': 'Pinus massoniana',
        
        '黑松': 'Pinus thunbergii',
        'pinus thunbergii': 'Pinus thunbergii',
        'japanese black pine': 'Pinus thunbergii',
        
        '湿地松': 'Pinus elliottii',
        'pinus elliottii': 'Pinus elliottii',
        'slash pine': 'Pinus elliottii',
        
        '赤松': 'Pinus densiflora',
        'pinus densiflora': 'Pinus densiflora',
        'japanese red pine': 'Pinus densiflora',
        
        '云南松': 'Pinus yunnanensis',
        'pinus yunnanensis': 'Pinus yunnanensis',
        
        '华山松': 'Pinus armandii',
        'pinus armandii': 'Pinus armandii',
    }
    
    # 疾病标准名
    DISEASE_CANONICAL_NAMES = {
        '松材线虫病': 'Pine Wilt Disease',
        '松树萎蔫病': 'Pine Wilt Disease',
        'pine wilt disease': 'Pine Wilt Disease',
        'pwd': 'Pine Wilt Disease',
        'pine wilt': 'Pine Wilt Disease',
    }
    
    # 化学物质标准名
    CHEMICAL_CANONICAL_NAMES = {
        '阿维菌素': 'Avermectin',
        'avermectin': 'Avermectin',
        '噻虫啉': 'Thiacloprid',
        'thiacloprid': 'Thiacloprid',
        '吡虫啉': 'Imidacloprid',
        'imidacloprid': 'Imidacloprid',
    }
    
    def __init__(self, use_external_kb: bool = False, external_kb_api: str = None):
        """
        Args:
            use_external_kb: 是否使用外部知识库（如 NCBI Taxonomy）
            external_kb_api: 外部知识库 API 地址
        """
        self.use_external_kb = use_external_kb
        self.external_kb_api = external_kb_api
        
        # 合并所有标准名映射
        self.canonical_map = {
            **self.BIOLOGICAL_CANONICAL_NAMES,
            **self.DISEASE_CANONICAL_NAMES,
            **self.CHEMICAL_CANONICAL_NAMES
        }
        
        logger.info(f"CanonicalResolver initialized with {len(self.canonical_map)} built-in mappings")
        if use_external_kb:
            logger.info(f"External KB enabled: {external_kb_api}")
    
    def resolve(self, entity: str, category: str = None) -> str:
        """
        解析实体到标准名
        
        Args:
            entity: 原始实体名
            category: 实体类别（可选，用于优化查询）
        
        Returns:
            标准化后的实体名
        """
        entity_lower = entity.lower().strip()
        
        # 1. 优先使用内置规则
        if entity_lower in self.canonical_map:
            canonical = self.canonical_map[entity_lower]
            logger.debug(f"Resolved '{entity}' → '{canonical}' (built-in rule)")
            return canonical
        
        # 2. 尝试外部知识库（如果启用）
        if self.use_external_kb and self.external_kb_api:
            try:
                canonical = self._query_external_kb(entity, category)
                if canonical:
                    logger.debug(f"Resolved '{entity}' → '{canonical}' (external KB)")
                    return canonical
            except Exception as e:
                logger.warning(f"External KB query failed for '{entity}': {e}")
        
        # 3. 无法解析，返回原名
        return entity
    
    def _query_external_kb(self, entity: str, category: str = None) -> Optional[str]:
        """
        查询外部知识库（如 NCBI Taxonomy、Wikidata）
        
        Args:
            entity: 实体名称
            category: 实体类别（用于选择合适的知识库）
        
        Returns:
            标准名称，如果查询失败则返回 None
        """
        import requests
        from urllib.parse import quote
        
        # 根据类别选择查询策略
        # 生物相关类别优先使用 NCBI Taxonomy
        bio_categories = ['Pathogen', 'Vector', 'Host', 'Organism', 'Animal', 'Plant', 'Insect']
        
        if category in bio_categories:
            # 1. 尝试 NCBI Taxonomy
            result = self._query_ncbi_taxonomy(entity)
            if result:
                return result
        
        # 2. 尝试 Wikidata（通用知识库）
        result = self._query_wikidata(entity)
        if result:
            return result
        
        return None
    
    def _query_ncbi_taxonomy(self, entity: str) -> Optional[str]:
        """
        查询 NCBI Taxonomy 数据库
        
        API 文档: https://www.ncbi.nlm.nih.gov/books/NBK25499/
        """
        import requests
        from urllib.parse import quote
        
        try:
            # Step 1: 搜索实体，获取 TaxID
            search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            search_params = {
                'db': 'taxonomy',
                'term': entity,
                'retmode': 'json',
                'retmax': 1
            }
            
            search_response = requests.get(search_url, params=search_params, timeout=5)
            search_response.raise_for_status()
            search_data = search_response.json()
            
            # 检查是否有结果
            id_list = search_data.get('esearchresult', {}).get('idlist', [])
            if not id_list:
                return None
            
            tax_id = id_list[0]
            
            # Step 2: 获取详细信息
            fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            fetch_params = {
                'db': 'taxonomy',
                'id': tax_id,
                'retmode': 'xml'
            }
            
            fetch_response = requests.get(fetch_url, params=fetch_params, timeout=5)
            fetch_response.raise_for_status()
            
            # 解析 XML 获取学名
            import xml.etree.ElementTree as ET
            root = ET.fromstring(fetch_response.text)
            
            # 获取 ScientificName
            scientific_name = root.find('.//ScientificName')
            if scientific_name is not None and scientific_name.text:
                canonical = scientific_name.text.strip()
                logger.info(f"NCBI Taxonomy: '{entity}' → '{canonical}' (TaxID: {tax_id})")
                return canonical
            
            return None
        
        except requests.exceptions.Timeout:
            logger.warning(f"NCBI Taxonomy query timeout for '{entity}'")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"NCBI Taxonomy query failed for '{entity}': {e}")
            return None
        except Exception as e:
            logger.warning(f"NCBI Taxonomy parsing error for '{entity}': {e}")
            return None
    
    def _query_wikidata(self, entity: str) -> Optional[str]:
        """
        查询 Wikidata 知识库
        
        使用 SPARQL 查询接口
        """
        import requests
        from urllib.parse import quote
        
        try:
            # SPARQL 查询：搜索与实体名称匹配的条目
            sparql_query = f"""
            SELECT ?item ?itemLabel ?scientificName WHERE {{
              ?item rdfs:label "{entity}"@zh .
              OPTIONAL {{ ?item wdt:P225 ?scientificName . }}
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh,en". }}
            }}
            LIMIT 1
            """
            
            sparql_url = "https://query.wikidata.org/sparql"
            headers = {
                'User-Agent': 'PWD-KG-Builder/1.0',
                'Accept': 'application/json'
            }
            
            response = requests.get(
                sparql_url,
                params={'query': sparql_query, 'format': 'json'},
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # 解析结果
            bindings = data.get('results', {}).get('bindings', [])
            if bindings:
                result = bindings[0]
                
                # 优先使用 scientificName（拉丁学名）
                if 'scientificName' in result:
                    canonical = result['scientificName']['value']
                    logger.info(f"Wikidata: '{entity}' → '{canonical}' (scientific name)")
                    return canonical
                
                # 否则使用标签
                if 'itemLabel' in result:
                    canonical = result['itemLabel']['value']
                    # 如果标签就是原实体名，则不返回（避免循环）
                    if canonical.lower() != entity.lower():
                        logger.info(f"Wikidata: '{entity}' → '{canonical}' (label)")
                        return canonical
            
            return None
        
        except requests.exceptions.Timeout:
            logger.warning(f"Wikidata query timeout for '{entity}'")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Wikidata query failed for '{entity}': {e}")
            return None
        except Exception as e:
            logger.warning(f"Wikidata parsing error for '{entity}': {e}")
            return None
    
    def batch_resolve(self, entities: List[str], categories: List[str] = None) -> Dict[str, str]:
        """
        批量解析实体
        
        Args:
            entities: 实体列表
            categories: 类别列表（可选）
        
        Returns:
            {原始名: 标准名} 映射字典
        """
        if categories is None:
            categories = [None] * len(entities)
        
        mapping = {}
        for entity, category in zip(entities, categories):
            mapping[entity] = self.resolve(entity, category)
        
        return mapping
    
    def add_custom_mapping(self, original: str, canonical: str):
        """
        添加自定义映射（用于领域特定术语）
        
        Args:
            original: 原始名称
            canonical: 标准名称
        """
        self.canonical_map[original.lower().strip()] = canonical
        logger.info(f"Added custom mapping: '{original}' → '{canonical}'")


class ConceptDeduplicator:
    """基于语义相似度的概念去重器（增强版：支持实体标准化）

    主要职责:
    - 将文本中抽取出来的大量概念通过向量表示转换到同一语义空间;
    - 使用 CanonicalResolver 进行规则优先的实体标准化;
    - 计算任意两概念之间的相似度,识别"含义几乎相同"的概念组;
    - 为每个相似概念簇选出一个代表概念(规范名),其余全部映射到该代表名上;
    - 聚合重要性、类别和来源块信息,生成去重后的概念表。
    """
    
    def __init__(self, embedding_provider: EmbeddingProvider = None, 
                 similarity_threshold: float = 0.85,
                 use_canonical_resolver: bool = True,
                 use_external_kb: bool = False):
        """初始化概念去重器（增强版）

        参数:
        - `embedding_provider`: 具体的向量生成实现,如 `BGE_M3_Embedder`、`SentenceTransformerEmbedding` 等;
        - `similarity_threshold`: 判定两个概念为"重复/同义"的相似度阈值,范围 0-1,越接近 1 表示越严格;
        - `use_canonical_resolver`: 是否启用实体标准化解析器（推荐）;
        - `use_external_kb`: 是否使用外部知识库（需要网络连接）。
        """
        if embedding_provider is None:
            # 默认优先使用 sentence-transformers；环境不满足时退回到轻量级 TF-IDF
            try:
                embedding_provider = SentenceTransformerEmbedding()
            except:
                logger.warning("Falling back to TF-IDF embeddings")
                embedding_provider = TfidfEmbedding()
        
        self.embedding_provider = embedding_provider
        # 相似度阈值控制"多严格才算重复"：越接近 1.0，合并得越保守
        self.similarity_threshold = similarity_threshold
        
        # 实体标准化解析器
        self.canonical_resolver = None
        if use_canonical_resolver:
            self.canonical_resolver = CanonicalResolver(
                use_external_kb=use_external_kb
            )
            logger.info("CanonicalResolver enabled (rule-based entity linking)")
    
    def deduplicate_concepts(self, concepts_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """基于语义相似度对概念做去重（增强版：规则优先）

        参数:
        - `concepts_df`: 概念 DataFrame,通常包含 `entity`(概念名称)、`importance`(重要性)、`category`(类别)、`chunk_id` 等列。

        返回:
        - `deduplicated_df`: 去重后的概念 DataFrame,每行是一个"规范概念"; 
        - `mapping_dict`: 字典形式的映射关系,`原始概念名 -> 规范概念名`,便于后续更新关系表。
        
        改进:
        - 优先使用 CanonicalResolver 进行规则匹配（如生物分类学拉丁名）
        - 对无法规则匹配的实体，再使用 Embedding 相似度聚类
        - 提高实体标准化的准确性和一致性
        """
        if concepts_df.empty:
            return concepts_df, {}
        
        logger.info(f"Deduplicating {len(concepts_df)} concepts...")
        
        # Step 1: 使用 CanonicalResolver 进行规则优先的标准化
        if self.canonical_resolver:
            logger.info("Applying rule-based entity linking...")
            canonical_mapping = {}
            
            for _, row in concepts_df.iterrows():
                entity = row['entity']
                category = row.get('category', None)
                canonical = self.canonical_resolver.resolve(entity, category)
                
                if canonical != entity:
                    canonical_mapping[entity] = canonical
            
            if canonical_mapping:
                logger.info(f"Rule-based linking: {len(canonical_mapping)} entities standardized")
                # 应用规则映射
                concepts_df['entity'] = concepts_df['entity'].map(
                    lambda x: canonical_mapping.get(x, x)
                )
        
        # Step 2: 对剩余实体使用 Embedding 相似度聚类
        
        # 以 entity 为单位做去重: 先在文本层面去重,再在向量空间里按语义聚类
        # Get unique concepts
        unique_concepts = concepts_df['entity'].unique()
        
        if len(unique_concepts) < 2:
            return concepts_df, {concept: concept for concept in unique_concepts}
        
        # Generate embeddings: 为所有唯一概念生成向量表示
        embeddings = self.embedding_provider.embed(list(unique_concepts))
        
        # Calculate similarity matrix: 计算任意两概念向量之间的余弦相似度,得到 N×N 的相似度矩阵
        similarity_matrix = cosine_similarity(embeddings)
        
        # Find duplicate clusters: 根据相似度矩阵做聚类,得到若干“同义概念簇”
        clusters = self._cluster_similar_concepts(similarity_matrix, unique_concepts)
        
        # Create mapping from original to canonical concept: 为每个簇生成“原名 -> 规范名”的映射
        mapping = self._create_concept_mapping(clusters, unique_concepts, concepts_df)
        
        # Apply mapping to deduplicate
        deduplicated_df = concepts_df.copy()
        deduplicated_df['entity'] = deduplicated_df['entity'].map(mapping)
        
        # Standardize categories before aggregation
        deduplicated_df['category'] = deduplicated_df['category'].map(
            lambda x: CATEGORY_MAPPING.get(str(x).lower(), '其他')
        )
        
        # Aggregate by canonical concept：同一个规范实体聚合重要性、类别和来源块信息
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
        """使用层次聚类算法将相似概念划分到同一簇

        参数:
        - `similarity_matrix`: 概念之间的相似度矩阵,形状为 `[N, N]`,取值 0-1,对角线为 1;
        - `concepts`: 概念名称数组,长度为 N,与矩阵的行/列一一对应。

        返回:
        - 若干个概念集合列表,每个集合代表一个“语义上接近的概念簇”。
        """
        # Convert similarity to distance: 将相似度转为“距离”=1-sim,便于聚类算法使用
        distance_matrix = 1 - similarity_matrix
        
        # Hierarchical clustering：通过距离阈值控制簇大小，而不是预先指定簇数量
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1 - self.similarity_threshold,
            linkage='average'
        )
        
        labels = clustering.fit_predict(distance_matrix)
        
        # Group concepts by cluster: 按聚类标签将概念划分到不同簇中
        clusters = {}
        for concept, label in zip(concepts, labels):
            if label not in clusters:
                clusters[label] = set()
            clusters[label].add(concept)
        
        return list(clusters.values())
    
    def _create_concept_mapping(self, clusters: List[Set[str]], 
                               concepts: np.ndarray,
                               concepts_df: pd.DataFrame) -> Dict[str, str]:
        """根据聚类结果生成“原始概念名 → 规范概念名”的映射

        约定: 每个簇中重要性(importance)最高概念作为该簇的“规范名称”,其他同义项全部映射到该名称。

        参数:
        - `clusters`: 聚类得到的概念簇列表;
        - `concepts`: 所有概念名称数组(主要用于保持顺序,这里只作为辅助);
        - `concepts_df`: 含有 `importance` 等元信息的概念 DataFrame。

        返回:
        - `mapping` 字典: `原始概念名 -> 规范概念名`。
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
        """对概念名称做简单规范化(大小写、空白等)

        当前实现仅包含:
        - 统一转为小写并去掉首尾空白;
        - 去掉完全重复的概念行;
        复数形式等更激进的词形还原暂未启用,避免误伤专业名词。
        """
        normalized_df = concepts_df.copy()
        
        # 将实体名称统一转为小写并去掉首尾空白(抽取阶段通常已做,这里再次保证一致性)
        normalized_df['entity'] = normalized_df['entity'].str.lower().str.strip()
        
        # 常见英文后缀占位: 如复数/动词形态等,当前仅做标记,未真正裁剪
        suffixes = ['s', 'es', 'ed', 'ing', 'tion', 'ness']
        for suffix in suffixes:
            mask = normalized_df['entity'].str.endswith(suffix)
            # 暂不修改原文,避免粗暴词干提取误伤专业术语,后续如需可在此处扩展
        
        # 规范化之后再做一次去重,避免同一概念因大小写/空格差异重复出现
        normalized_df = normalized_df.drop_duplicates(subset=['entity'])
        
        return normalized_df


class RelationshipDeduplicator:
    """基于概念去重结果更新关系表

    在概念已经做了“同义合并”之后,需要同步更新关系中的 `node_1`/`node_2`,否则会出现老名称与新名称并存的问题。
    """
    
    @staticmethod
    def update_relationships(relationships_df: pd.DataFrame, 
                            concept_mapping: Dict[str, str]) -> pd.DataFrame:
        """根据概念映射结果更新关系中的节点名称

        参数:
        - `relationships_df`: 关系 DataFrame,包含 `node_1`、`node_2`、`edge`、`weight` 等列;
        - `concept_mapping`: 概念映射字典,`原始概念名 -> 规范概念名`。

        返回:
        - 已将节点名称替换为规范名,并聚合重复关系后的 DataFrame。
        """
        updated_df = relationships_df.copy()
        
        # Apply mapping to both nodes: 将两端节点名称统一替换为规范概念名
        updated_df['node_1'] = updated_df['node_1'].map(
            lambda x: concept_mapping.get(x, x)
        )
        updated_df['node_2'] = updated_df['node_2'].map(
            lambda x: concept_mapping.get(x, x)
        )
        
        # Remove self-loops: 删除 node_1 == node_2 的自环关系,避免概念自己连自己
        updated_df = updated_df[updated_df['node_1'] != updated_df['node_2']]
        
        # Aggregate duplicate relationships: 对同一对节点之间的多条边做聚合,累加权重并合并关系描述/来源块
        aggregated = updated_df.groupby(['node_1', 'node_2']).agg({
            'weight': 'sum',
            'edge': lambda x: ' | '.join(x.unique()),
            'chunk_id': lambda x: ','.join(x.unique()),
            'source': lambda x: ','.join(x.unique())
        }).reset_index()
        
        # Normalize weights: 将聚合后的权重归一化到 [0,1],便于不同图之间对比
        max_weight = aggregated['weight'].max()
        if max_weight > 0:
            aggregated['weight'] = aggregated['weight'] / max_weight
        
        return aggregated


class ConceptImportanceFilter:
    """基于重要性和连接度的概念过滤器

    目的:
    - 删掉“因素、机制、研究”等过于通用的概念,它们很难提供有价值的图谱信息;
    - 利用 `importance`(人工/LLM 评分) 和 `connections`(参与的关系条数) 做二次筛选,保留对下游分析真正有用的概念。
    """
    
    # 过于通用的概念列表（需要过滤）
    # 包含“因素、机制、研究、结果”等泛化词,这些词即使频繁出现也难以提供有用语义信息
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
        """按重要性与连接度过滤概念

        参数:
        - `concepts_df`: 概念 DataFrame;
        - `relationships_df`: 关系 DataFrame,用于统计每个概念参与了多少条关系;
        - `min_importance`: 最小重要性阈值(1-5),低于该值的概念会被丢弃;
        - `min_connections`: 最少连接数阈值,小于该值说明该概念在图中几乎不与其他节点交互,可视情况丢弃。

        返回:
        - 过滤后的概念 DataFrame。
        """
        # min_importance 控制“多重要才保留”, min_connections 控制“至少参与多少条关系才算有用”
        filtered_df = concepts_df.copy()
        
        # 处理顺序：先剔除过于通用的词，再按重要性和连接度筛一遍
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
