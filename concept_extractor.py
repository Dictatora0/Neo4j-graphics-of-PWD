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
    
    def __init__(self, model: str = "mistral", ollama_host: str = "http://localhost:11434", timeout: int = 600):
        """
        Initialize concept extractor
        
        Args:
            model: Model name (mistral, zephyr, neural-chat, etc.)
            ollama_host: Ollama server URL
            timeout: Request timeout in seconds (default: 600s = 10min)
        """
        self.model = model
        self.ollama_host = ollama_host
        self.api_endpoint = f"{ollama_host}/api/generate"
        self.timeout = timeout
        self._verify_ollama_connection()
    
    def _verify_ollama_connection(self):
        """Verify Ollama server is running"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info(f"Connected to Ollama at {self.ollama_host}")
                models = response.json().get('models', [])
                model_names = [m.get('name', '').split(':')[0] for m in models]
                logger.info(f"Available models: {', '.join(model_names)}")
            else:
                raise ConnectionError(f"Ollama returned status {response.status_code}")
        except Exception as e:
            logger.error(f"Cannot connect to Ollama: {e}")
            logger.error("Please ensure Ollama is running: ollama serve")
            raise
    
    def _call_ollama(self, prompt: str, system_prompt: str = "", temperature: float = 0.1, max_retries: int = 3, json_mode: bool = True) -> Optional[str]:
        """
        Call Ollama API with retry mechanism and strict JSON mode for Qwen
        
        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            temperature: Temperature for generation (0.0-1.0)
            max_retries: Maximum number of retries on timeout
            json_mode: Enable strict JSON output mode (for Qwen models)
        
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
                    "top_p": 0.8,
                    "top_k": 20,
                    "repeat_penalty": 1.1,
                    "num_ctx": 8192,  # Qwen 支持更大上下文
                }
                
                # 如果是 Qwen 模型，启用 JSON mode
                if json_mode and 'qwen' in self.model.lower():
                    payload["format"] = "json"  # Ollama JSON mode
                
                # 使用配置的超时时间（默认600秒，支持大模型）
                response = requests.post(self.api_endpoint, json=payload, timeout=self.timeout)
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
        Extract concepts from text chunk using Qwen with strict JSON Schema
        
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
        # Qwen 优化的系统提示词 - 强制 JSON Schema
        system_prompt = """你是一个专业的松材线虫病(Pine Wilt Disease)知识图谱构建助手。你的任务是从科学文献中精确提取领域概念。

## 输出要求
你必须严格按照以下 JSON Schema 输出，不得添加任何额外文字、解释或 markdown 标记：

[
  {
    "entity": "概念名称(字符串)",
    "importance": 1到5的整数,
    "category": "类别名称(字符串)"
  }
]

## 提取范围
重点关注以下领域概念（按优先级）：
1. **病原体** (pathogen): 松材线虫、Bursaphelenchus xylophilus、伴生细菌、线虫种群
2. **寄主植物** (host): 马尾松、黑松、湿地松、赤松、云南松、华山松
3. **媒介昆虫** (vector): 松褐天牛、云杉花墨天牛、Monochamus alternatus
4. **病害症状** (symptom): 萎蔫、针叶变色、树脂分泌异常、枯死
5. **防治措施** (treatment): 阿维菌素、噻虫啉、诱捕器、生物防治剂
6. **环境因子** (environment): 温度、湿度、降水、海拔、气候类型
7. **地理位置** (location): 疫区、省份、县市、分布区域
8. **生理机制** (mechanism): 侵染途径、致病机理、抗性机制
9. **化学物质** (compound): 萜烯类、酚类物质、杀虫剂成分

## 重要性评分标准
- 5: 核心概念（如松材线虫、松褐天牛、马尾松）
- 4: 重要概念（如具体防治药剂、关键症状）
- 3: 一般概念（如环境因子、次要寄主）
- 2: 次要概念（如地理位置、辅助信息）
- 1: 边缘概念（如研究方法、实验设备）

## 过滤规则
排除以下内容：
- 过于宽泛的词：因素、过程、机制、方法、系统、影响
- 研究术语：实验、分析、研究、调查、统计
- 非领域概念：作者、文献、数据、表格

记住：只输出纯 JSON 数组，不要添加任何解释文字！"""
        
        user_prompt = f"""请从以下科学文本中提取松材线虫病相关的领域概念：

{text}

输出格式示例：
[
  {{"entity": "松材线虫", "importance": 5, "category": "pathogen"}},
  {{"entity": "松褐天牛", "importance": 5, "category": "vector"}},
  {{"entity": "马尾松", "importance": 4, "category": "host"}}
]"""
        
        response = self._call_ollama(user_prompt, system_prompt, temperature=0.1, json_mode=True)
        
        if not response:
            return None
        
        try:
            # 直接解析 JSON，不需要清理 markdown
            concepts = json.loads(response)
            
            # 验证和标准化
            valid_concepts = []
            for c in concepts:
                if isinstance(c, dict) and 'entity' in c:
                    importance_val = c.get('importance', 3)
                    if importance_val is None:
                        importance_val = 3
                    try:
                        importance = min(5, max(1, int(importance_val)))
                    except (ValueError, TypeError):
                        importance = 3
                    
                    valid_concepts.append({
                        'entity': str(c.get('entity', '')).lower().strip(),
                        'importance': importance,
                        'category': str(c.get('category', 'misc')).lower(),
                        'chunk_id': chunk_id,
                        'type': 'concept'
                    })
            
            return valid_concepts if valid_concepts else None
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败 [{chunk_id}] - Qwen 可能未正确输出 JSON")
            logger.error(f"错误: {str(e)}")
            logger.error(f"原始响应（前500字符）:\n{response[:500]}")
            return None
    
    def extract_relationships(self, text: str, chunk_id: str = "") -> Optional[List[Dict]]:
        """
        Extract semantic relationships using Qwen with strict JSON Schema
        
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
        # Qwen 优化的关系提取提示词
        system_prompt = """你是松材线虫病知识图谱关系提取专家。你的任务是识别实体间的明确因果、功能关系。

## 输出要求
严格按照以下 JSON Schema 输出，不得添加任何额外内容：

[
  {
    "node_1": "源实体名称",
    "node_2": "目标实体名称",
    "edge": "关系类型"
  }
]

## 关系类型定义
优先识别以下高价值关系（从高到低）：

1. **因果关系**
   - "引起" - 病原引起症状、环境导致发病
   - "导致" - X导致Y发生
   - "诱发" - 间接引起

2. **传播关系**
   - "传播" - 媒介传播病原
   - "携带" - 媒介携带病原
   - "扩散" - 病害扩散

3. **寄生/感染关系**
   - "感染" - 病原感染寄主
   - "寄生于" - 病原寄生于寄主
   - "侵染" - 病原侵入寄主

4. **防治关系**
   - "防治" - 药剂/措施防治病害
   - "控制" - 控制媒介/病原
   - "抑制" - 抑制病原生长
   - "杀灭" - 杀灭媒介/病原

5. **影响关系**
   - "影响" - 环境影响发病
   - "促进" - 促进病害发生
   - "抑制" - 抑制病害发展

6. **分布关系**
   - "分布于" - 病害/物种分布于地区
   - "发生于" - 病害发生于某地

## 提取原则
- 只提取文本中明确表述的关系
- 优先提取因果、功能关系，避免简单共现
- 关系描述使用动词短语，简洁明确
- 每个关系必须有明确的方向性（node_1 → node_2）

只输出 JSON 数组！"""
        
        user_prompt = f"""请从以下文本中提取松材线虫病相关的实体关系：

{text}

输出格式示例：
[
  {{"node_1": "松材线虫", "node_2": "马尾松", "edge": "感染"}},
  {{"node_1": "松褐天牛", "node_2": "松材线虫", "edge": "传播"}},
  {{"node_1": "阿维菌素", "node_2": "松褐天牛", "edge": "防治"}}
]"""
        
        response = self._call_ollama(user_prompt, system_prompt, temperature=0.1, json_mode=True)
        
        if not response:
            return None
        
        try:
            # 直接解析 JSON
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
        except json.JSONDecodeError as e:
            logger.warning(f"关系 JSON 解析失败 [{chunk_id}]: {str(e)}")
            return None
    
    def extract_concepts_and_relationships(self, text: str, chunk_id: str = "") -> Tuple[Optional[List[Dict]], Optional[List[Dict]]]:
        """
        Extract both concepts and relationships in a single LLM call with strict JSON Schema (FASTER + MORE RELIABLE)
        
        Args:
            text: Text chunk to extract from
            chunk_id: Unique identifier for the chunk
        
        Returns:
            Tuple of (concepts_list, relationships_list)
        """
        system_prompt = """你是专业的松材线虫病知识图谱构建系统。你的任务是从科学文献中同时提取概念和关系。

## 输出要求
严格按照以下 JSON Schema 输出，不得添加任何解释或 markdown：

{
  "concepts": [
    {"entity": "概念名称", "importance": 1-5整数, "category": "类别"}
  ],
  "relationships": [
    {"node_1": "源实体", "node_2": "目标实体", "edge": "关系类型"}
  ]
}

## 概念提取范围
**病原** (pathogen): 松材线虫、Bursaphelenchus xylophilus、伴生细菌
**寄主** (host): 马尾松、黑松、湿地松、赤松、云南松
**媒介** (vector): 松褐天牛、云杉花墨天牛、Monochamus alternatus
**症状** (symptom): 萎蔫、针叶变色、树脂分泌异常、枯死
**防治** (treatment): 阿维菌素、噻虫啉、诱捕器、生物防治
**环境** (environment): 温度、湿度、降水、海拔
**地点** (location): 疫区、省份、分布区
**机制** (mechanism): 侵染途径、致病机理
**化合物** (compound): 萜烯、酚类、杀虫剂成分

## 关系类型
**因果**: 引起、导致、诱发
**传播**: 传播、携带、扩散
**寄生**: 感染、寄生于、侵染
**防治**: 防治、控制、抑制、杀灭
**影响**: 影响、促进、抑制
**分布**: 分布于、发生于

## 重要性评分
5-核心概念, 4-重要概念, 3-一般概念, 2-次要概念, 1-边缘概念

只输出 JSON 对象！"""
        
        user_prompt = f"""从以下松材线虫病科学文本中提取概念和关系：

{text}

输出格式示例：
{{
  "concepts": [
    {{"entity": "松材线虫", "importance": 5, "category": "pathogen"}},
    {{"entity": "松褐天牛", "importance": 5, "category": "vector"}},
    {{"entity": "马尾松", "importance": 4, "category": "host"}}
  ],
  "relationships": [
    {{"node_1": "松材线虫", "node_2": "马尾松", "edge": "感染"}},
    {{"node_1": "松褐天牛", "node_2": "松材线虫", "edge": "传播"}}
  ]
}}"""
        
        response = self._call_ollama(user_prompt, system_prompt, temperature=0.1, json_mode=True)
        
        if not response:
            return None, None
        
        try:
            # 直接解析 JSON
            data = json.loads(response)
            
            # 解析概念
            concepts = []
            for c in data.get('concepts', []):
                if isinstance(c, dict) and 'entity' in c:
                    importance_val = c.get('importance', 3)
                    if importance_val is None:
                        importance_val = 3
                    try:
                        importance = min(5, max(1, int(importance_val)))
                    except (ValueError, TypeError):
                        importance = 3
                    
                    concepts.append({
                        'entity': str(c.get('entity', '')).lower().strip(),
                        'importance': importance,
                        'category': str(c.get('category', 'misc')).lower(),
                        'chunk_id': chunk_id,
                        'type': 'concept'
                    })
            
            # 解析关系
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
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败 [{chunk_id}] - Qwen 未正确输出 JSON")
            logger.error(f"错误: {str(e)}")
            logger.error(f"原始响应（前500字符）:\n{response[:500]}")
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
            logger.warning(f"Limiting processing to {max_chunks} chunks (out of {len(chunks)})")
            logger.warning("Set max_chunks=None in code to process all chunks")
            chunks = chunks[:max_chunks]
        
        all_concepts = []
        all_relationships = []
        
        logger.info(f"Extracting concepts and relationships from {len(chunks)} chunks...")
        logger.info("Optimized: single LLM call per chunk with strict JSON Schema")
        logger.info("Model: Using Qwen2.5-Coder with enhanced structured output")
        logger.info("Timeout: 180 seconds per request (Qwen 14B requires longer processing)")
        logger.info("Retry: 3 attempts per chunk with exponential backoff")
        logger.info(f"Estimated time: ~{len(chunks) * 20} seconds (20s per chunk for Qwen 14B)")
        
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
                logger.debug(f"Extracted {len(concepts)} concepts")
            else:
                logger.debug("No concepts extracted")
                failed_chunks += 1
                continue
            
            if relationships:
                all_relationships.extend(relationships)
                logger.debug(f"Extracted {len(relationships)} relationships")
            
            successful_chunks += 1
        
        logger.info(f"Extraction complete: {successful_chunks} successful, {failed_chunks} failed")
        logger.info(f"Total concepts: {len(all_concepts)}")
        logger.info(f"Total relationships: {len(all_relationships)}")
        
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
