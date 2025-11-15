#!/usr/bin/env python3
"""
LLM-based Concept Extraction Module
Uses Ollama with Mistral/Zephyr for extracting concepts and semantic relationships
"""

import json
import logging
from typing import List, Dict, Optional, Tuple
import requests
from tqdm import tqdm
import pandas as pd

logger = logging.getLogger(__name__)


class ConceptExtractor:
    """Extract concepts and relationships using LLM (Ollama)"""
    
    def __init__(self, model: str = "mistral", ollama_host: str = "http://localhost:11434"):
        """
        Initialize concept extractor
        
        Args:
            model: Model name (mistral, zephyr, neural-chat, etc.)
            ollama_host: Ollama server URL
        """
        self.model = model
        self.ollama_host = ollama_host
        self.api_endpoint = f"{ollama_host}/api/generate"
        self._verify_ollama_connection()
    
    def _verify_ollama_connection(self):
        """Verify Ollama server is running"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info(f"✓ Connected to Ollama at {self.ollama_host}")
                models = response.json().get('models', [])
                model_names = [m.get('name', '').split(':')[0] for m in models]
                logger.info(f"  Available models: {', '.join(model_names)}")
            else:
                raise ConnectionError(f"Ollama returned status {response.status_code}")
        except Exception as e:
            logger.error(f"✗ Cannot connect to Ollama: {e}")
            logger.error("  Please ensure Ollama is running: ollama serve")
            raise
    
    def _call_ollama(self, prompt: str, system_prompt: str = "", temperature: float = 0.3, max_retries: int = 3) -> Optional[str]:
        """
        Call Ollama API with retry mechanism
        
        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            temperature: Temperature for generation (0.0-1.0)
            max_retries: Maximum number of retries on timeout
        
        Returns:
            Generated text or None if failed
        """
        for attempt in range(max_retries):
            try:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "top_k": 40,
                }
                
                # 超时时间 120 秒
                response = requests.post(self.api_endpoint, json=payload, timeout=120)
                response.raise_for_status()
                
                result = response.json()
                return result.get('response', '').strip()
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logger.warning(f"Ollama timeout (attempt {attempt + 1}/{max_retries}), retrying...")
                    continue
                else:
                    logger.error(f"Ollama API timeout after {max_retries} attempts")
                    return None
            except Exception as e:
                logger.error(f"Ollama API error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    continue
                return None
    
    def extract_concepts(self, text: str, chunk_id: str = "") -> Optional[List[Dict]]:
        """
        Extract concepts from text chunk
        
        Args:
            text: Text chunk to extract concepts from
            chunk_id: Unique identifier for the chunk
        
        Returns:
            List of concept dictionaries with format:
            {
                "entity": str,
                "importance": int (1-5),
                "category": str,
                "chunk_id": str
            }
        """
        # 领域特定的提示词
        system_prompt = """你是松材线虫病知识图谱构建专家。从文本中提取具体的领域概念。

重点关注:
- 病原体: 松材线虫、伴生细菌、线虫种类
- 寄主植物: 松树、马尾松、黑松、湿地松
- 媒介昆虫: 松褐天牛、云杉花墨天牛
- 病害症状: 萎蔫、枯死、变色、针叶脱落
- 防治措施: 药剂、诱捕器、生物防治
- 环境因子: 温度、湿度、海拔、气候
- 地理位置: 疫区、分布区、省份

类别: pathogen(病原), host(寄主), vector(媒介), symptom(症状), treatment(防治), environment(环境), location(地点), mechanism(机制), compound(化合物)

避免: 过于通用的词(因素、过程、机制、方法)
只返回JSON数组，无其他文字。"""
        
        user_prompt = (
            f"从以下文本提取松材线虫病相关概念:\n{text}\n\n"
            "JSON格式: [{'entity': '概念名', 'importance': 1-5, 'category': '类别'}, ...]"
        )
        
        response = self._call_ollama(user_prompt, system_prompt, temperature=0.1)
        
        if not response:
            return None
        
        try:
            # Try to extract JSON from response
            concepts = json.loads(response)
            
            # Validate and normalize
            valid_concepts = []
            for concept in concepts:
                if isinstance(concept, dict) and 'entity' in concept:
                    valid_concepts.append({
                        'entity': str(concept.get('entity', '')).lower().strip(),
                        'importance': min(5, max(1, int(concept.get('importance', 3)))),
                        'category': str(concept.get('category', 'misc')).lower(),
                        'chunk_id': chunk_id,
                        'type': 'concept'
                    })
            
            return valid_concepts if valid_concepts else None
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON response for chunk {chunk_id}")
            return None
    
    def extract_relationships(self, text: str, chunk_id: str = "") -> Optional[List[Dict]]:
        """
        Extract semantic relationships between concepts
        
        Args:
            text: Text chunk to extract relationships from
            chunk_id: Unique identifier for the chunk
        
        Returns:
            List of relationship dictionaries with format:
            {
                "node_1": str,
                "node_2": str,
                "edge": str (relationship description),
                "weight": float (W1 - LLM-extracted relationship weight),
                "chunk_id": str
            }
        """
        # 领域特定关系提取提示词
        system_prompt = """提取松材线虫病相关实体间的具体关系。

关系类型:
- 引起/导致: 病原引起症状、环境导致发病
- 传播: 媒介传播病原
- 寄生于: 病原寄生于寄主
- 感染: 病原感染寄主
- 防治: 药剂防治病害、措施控制媒介
- 影响: 环境影响发病、因素影响传播
- 分布于: 病害分布于地区
- 携带: 媒介携带病原
- 抑制: 药剂抑制病原

只提取明确的因果、功能关系，避免模糊的共现关系。
只返回JSON数组。"""
        
        user_prompt = (
            f"从以下文本提取实体关系:\n{text}\n\n"
            "JSON格式: [{'node_1': '实体1', 'node_2': '实体2', 'edge': '关系类型'}, ...]"
        )
        
        response = self._call_ollama(user_prompt, system_prompt, temperature=0.2)
        
        if not response:
            return None
        
        try:
            relationships = json.loads(response)
            
            valid_relationships = []
            for rel in relationships:
                if isinstance(rel, dict) and 'node_1' in rel and 'node_2' in rel:
                    valid_relationships.append({
                        'node_1': str(rel.get('node_1', '')).lower().strip(),
                        'node_2': str(rel.get('node_2', '')).lower().strip(),
                        'edge': str(rel.get('edge', 'related to')).strip(),
                        'weight': 0.8,  # W1 weight for LLM-extracted relationships
                        'chunk_id': chunk_id,
                        'source': 'llm'
                    })
            
            return valid_relationships if valid_relationships else None
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse relationships JSON for chunk {chunk_id}")
            return None
    
    def extract_concepts_and_relationships(self, text: str, chunk_id: str = "") -> Tuple[Optional[List[Dict]], Optional[List[Dict]]]:
        """
        Extract both concepts and relationships in a single LLM call (FASTER)
        
        Args:
            text: Text chunk to extract from
            chunk_id: Unique identifier for the chunk
        
        Returns:
            Tuple of (concepts_list, relationships_list)
        """
        system_prompt = """你是松材线虫病知识图谱构建专家。从文本中同时提取概念和关系。

重点关注:
- 病原体: 松材线虫、伴生细菌
- 寄主: 马尾松、黑松、湿地松
- 媒介: 松褐天牛、云杉花墨天牛
- 症状: 萎蔫、枯死、变色
- 防治: 药剂、诱捕器、生物防治
- 环境: 温度、湿度、海拔
- 地点: 疫区、分布区

关系类型: 引起、传播、寄生于、感染、防治、影响、分布于、携带、抑制

只返回JSON，无其他文字。"""
        
        user_prompt = f"""从以下文本提取概念和关系:
{text}

返回格式:
{{
  "concepts": [{{"entity": "名称", "importance": 1-5, "category": "类别"}}],
  "relationships": [{{"node_1": "实体1", "node_2": "实体2", "edge": "关系"}}]
}}"""
        
        response = self._call_ollama(user_prompt, system_prompt, temperature=0.1)
        
        if not response:
            return None, None
        
        try:
            data = json.loads(response)
            
            # Parse concepts
            concepts = []
            for c in data.get('concepts', []):
                if isinstance(c, dict) and 'entity' in c:
                    concepts.append({
                        'entity': str(c.get('entity', '')).lower().strip(),
                        'importance': min(5, max(1, int(c.get('importance', 3)))),
                        'category': str(c.get('category', 'misc')).lower(),
                        'chunk_id': chunk_id,
                        'type': 'concept'
                    })
            
            # Parse relationships
            relationships = []
            for r in data.get('relationships', []):
                if isinstance(r, dict) and 'node_1' in r and 'node_2' in r:
                    relationships.append({
                        'node_1': str(r.get('node_1', '')).lower().strip(),
                        'node_2': str(r.get('node_2', '')).lower().strip(),
                        'edge': str(r.get('edge', 'related to')).strip(),
                        'weight': 0.8,
                        'chunk_id': chunk_id,
                        'source': 'llm'
                    })
            
            return (concepts if concepts else None, 
                    relationships if relationships else None)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON for chunk {chunk_id}")
            return None, None
    
    def extract_from_chunks(self, chunks: List[Dict], max_chunks: int = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Extract concepts and relationships from multiple chunks
        
        Args:
            chunks: List of chunk dictionaries with 'text' and 'chunk_id' keys
            max_chunks: Maximum number of chunks to process (None = all chunks)
        
        Returns:
            Tuple of (concepts_df, relationships_df)
        """
        # Limit chunks if max_chunks is specified
        if max_chunks and len(chunks) > max_chunks:
            logger.warning(f"⚠️  Limiting processing to {max_chunks} chunks (out of {len(chunks)})")
            logger.warning(f"    Set max_chunks=None in code to process all chunks")
            chunks = chunks[:max_chunks]
        
        all_concepts = []
        all_relationships = []
        
        logger.info(f"🚀 Extracting concepts and relationships from {len(chunks)} chunks...")
        logger.info(f"⚡ OPTIMIZED: Single LLM call per chunk (2x faster)")
        logger.info(f"⏱️  Timeout: 120 seconds per request")
        logger.info(f"🔄 Retry: 3 attempts per chunk")
        logger.info(f"💡 Estimated time: ~{len(chunks) * 15} seconds (15s per chunk)")
        
        successful_chunks = 0
        failed_chunks = 0
        
        for i, chunk in enumerate(tqdm(chunks, desc="Processing chunks"), 1):
            text = chunk.get('text', '')
            chunk_id = chunk.get('chunk_id', '')
            
            if not text or len(text.strip()) < 20:
                continue
            
            logger.debug(f"[{i}/{len(chunks)}] Processing chunk: {chunk_id}")
            
            # Extract both concepts and relationships in ONE call
            concepts, relationships = self.extract_concepts_and_relationships(text, chunk_id)
            
            if concepts:
                all_concepts.extend(concepts)
                logger.debug(f"  ✓ Extracted {len(concepts)} concepts")
            else:
                logger.debug(f"  ⚠ No concepts extracted")
                failed_chunks += 1
                continue
            
            if relationships:
                all_relationships.extend(relationships)
                logger.debug(f"  ✓ Extracted {len(relationships)} relationships")
            
            successful_chunks += 1
        
        logger.info(f"✓ Extraction complete: {successful_chunks} successful, {failed_chunks} failed")
        logger.info(f"  Total concepts: {len(all_concepts)}")
        logger.info(f"  Total relationships: {len(all_relationships)}")
        
        concepts_df = pd.DataFrame(all_concepts) if all_concepts else pd.DataFrame()
        relationships_df = pd.DataFrame(all_relationships) if all_relationships else pd.DataFrame()
        
        logger.info(f"Extracted {len(concepts_df)} concepts and {len(relationships_df)} relationships")
        
        return concepts_df, relationships_df


class ContextualProximityAnalyzer:
    """Analyze contextual proximity between concepts in chunks"""
    
    @staticmethod
    def extract_proximity_relationships(chunks: List[Dict]) -> pd.DataFrame:
        """
        Extract relationships based on contextual proximity (W2 weight)
        
        Concepts that appear in the same chunk are considered related by proximity
        
        Args:
            chunks: List of chunk dictionaries with extracted concepts
        
        Returns:
            DataFrame of proximity-based relationships
        """
        proximity_relationships = []
        
        for chunk in chunks:
            concepts = chunk.get('concepts', [])
            chunk_id = chunk.get('chunk_id', '')
            
            # Create pairwise relationships for all concepts in the chunk
            for i, concept1 in enumerate(concepts):
                for concept2 in concepts[i+1:]:
                    if concept1 != concept2:
                        proximity_relationships.append({
                            'node_1': concept1.lower(),
                            'node_2': concept2.lower(),
                            'edge': 'co-occurs in',
                            'weight': 0.5,  # W2 weight for contextual proximity
                            'chunk_id': chunk_id,
                            'source': 'proximity'
                        })
        
        return pd.DataFrame(proximity_relationships) if proximity_relationships else pd.DataFrame()
    
    @staticmethod
    def merge_relationships(llm_relationships: pd.DataFrame, 
                          proximity_relationships: pd.DataFrame) -> pd.DataFrame:
        """
        Merge LLM-extracted and proximity-based relationships
        
        Rules:
        - Group by (node_1, node_2) pairs
        - Sum weights
        - Concatenate relationship descriptions
        
        Args:
            llm_relationships: DataFrame from LLM extraction
            proximity_relationships: DataFrame from proximity analysis
        
        Returns:
            Merged and aggregated relationships
        """
        if llm_relationships.empty and proximity_relationships.empty:
            return pd.DataFrame()
        
        # Combine both relationship types
        all_relationships = pd.concat(
            [llm_relationships, proximity_relationships],
            ignore_index=True
        )
        
        # Group by node pairs and aggregate
        merged = all_relationships.groupby(['node_1', 'node_2']).agg({
            'weight': 'sum',
            'edge': lambda x: ' | '.join(x.unique()),
            'chunk_id': lambda x: ','.join(x.unique()),
            'source': lambda x: ','.join(x.unique())
        }).reset_index()
        
        # Normalize weights to 0-1 range
        max_weight = merged['weight'].max()
        if max_weight > 0:
            merged['weight'] = merged['weight'] / max_weight
        
        return merged
