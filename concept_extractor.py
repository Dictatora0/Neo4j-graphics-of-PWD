#!/usr/bin/env python3
"""基于 LLM 的概念与关系抽取模块

通过本地 Ollama 模型(Mistral/Qwen 等)从文本块中抽取松材线虫病领域的概念和语义关系, 输出结构化 JSON, 供后续去重、过滤和导入 Neo4j 使用。

整体链路总览(从原始文本到 W1 关系):
1) 上游将 PDF 文本清洗并切分为若干 chunk, 每个 chunk 带有唯一 chunk_id;
2) 本模块对每个 chunk 调用一次 LLM, 同时抽取 concepts 与 relationships;
3) 将 LLM 输出转换为 DataFrame, 规范为 entity/category/importance 与 node_1/node_2/edge/weight 等字段;
4) 生成的 relationships 作为 W1(LLM 关系), 与 ContextualProximityAnalyzer 计算的 W2(共现关系)在后处理阶段合并。
"""

import json
import logging
from typing import List, Dict, Optional, Tuple
import requests
from tqdm import tqdm
import pandas as pd

logger = logging.getLogger(__name__)


class ConceptExtractor:
    """基于 LLM 的概念和关系提取器（使用 Ollama 本地模型）
    
    核心功能：
    1. 从文本块中提取领域概念（病原、寄主、媒介等）
    2. 识别实体间的语义关系（感染、传播、防治等）
    3. 使用严格的 JSON Schema 保证输出可靠性
    
    支持的模型：
    - mistral: 通用性能好，速度快
    - qwen2.5-coder: 结构化输出最佳（推荐）
    - llama3: Meta官方模型
    """
    
    def __init__(self, model: str = "mistral", ollama_host: str = "http://localhost:11434", timeout: int = 600):
        """初始化概念提取器

        参数:
            model: Ollama 模型名称(需提前拉取: ollama pull <model>)
            ollama_host: Ollama 服务地址(本地运行一般为 http://localhost:11434)
            timeout: 单次请求超时时间(秒), 大模型需要更长时间(默认 10 分钟)
        """
        self.model = model
        self.ollama_host = ollama_host
        self.api_endpoint = f"{ollama_host}/api/generate"
        self.timeout = timeout
        self._verify_ollama_connection()
    
    def _verify_ollama_connection(self):
        """验证 Ollama 服务是否正常运行
        
        检查步骤：
        1. 尝试连接 /api/tags 接口
        2. 获取已安装的模型列表
        3. 输出可用模型供参考
        
        如果失败，会抛出异常并提示运行 'ollama serve'
        """
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
        """调用 Ollama API 生成文本(带重试机制)

        参数:
            prompt: 用户提示词(包含待提取的文本)
            system_prompt: 系统提示词(定义任务规则和输出格式)
            temperature: 采样温度,0 表示基本确定性输出,1 表示随机性最大; 概念/关系提取通常使用 0.1 保证稳定性
            max_retries: 超时或网络异常时的最大重试次数
            json_mode: 是否启用严格 JSON 模式(Qwen 模型支持, 输出更接近预期的 JSON 结构)

        返回:
            LLM 生成的文本(字符串), 失败返回 None

        说明:
        - temperature 越低, 输出越稳定但也越保守;
        - 当 json_mode 为 True 且模型名称包含 qwen 时, 会在请求 payload 中设置 format="json", 限制模型必须输出合法 JSON;
        - 超过 max_retries 次仍失败时, 函数返回 None, 由上层决定当前 chunk 是否跳过。
        """
        # 简单重试机制: 防止偶发超时/网络抖动直接导致整块解析失败
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
                    "num_ctx": 4096,  # 降低上下文窗口减少内存占用
                }
                
                # Qwen 模型专属：强制 JSON 格式输出
                # Ollama 的 format="json" 会约束模型输出符合JSON规范
                if json_mode and 'qwen' in self.model.lower():
                    payload["format"] = "json"  # 严格模式，非法JSON会自动重试
                
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
        """从文本块中提取领域概念(使用严格的 JSON Schema)

        参数:
            text: 待提取的文本块(通常 2000~3000 字左右)
            chunk_id: 文本块唯一标识符(例如: PDF 文件名_块序号)

        返回:
            概念字典列表, 每个元素大致形如:
            {
                "entity": 概念名称(如 "松材线虫"),
                "importance": 1-5 的重要性评分(5 为核心概念),
                "category": 概念类别(pathogen/host/vector 等),
                "chunk_id": 来源文本块 ID
            }
            若当前文本块未能成功解析, 返回 None。

        提取策略:
        - 只提取松材线虫病相关的领域概念;
        - 过滤“因素、过程、机制、方法、系统”等过于通用的抽象词;
        - 优先保留病原、寄主、媒介等核心实体, 以便后续构图时重点突出主干节点。
        """
        # Qwen 专用系统提示词 - 严格限定输出格式和提取范围
        # 设计原则：
        # 1. 明确JSON Schema，避免格式错误
        # 2. 列出具体提取类别，减少无关概念
        # 3. 定义重要性评分标准，保证一致性
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
- 5: 核心概念（如松材线虫、松褐天牛、马尾松）- 出现频率高，领域关键
- 4: 重要概念（如具体防治药剂、关键症状）- 有明确应用价值
- 3: 一般概念（如环境因子、次要寄主）- 相关但非核心
- 2: 次要概念（如地理位置、辅助信息）- 背景信息
- 1: 边缘概念（如研究方法、实验设备）- 仅在特定上下文有用

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
            # 直接解析JSON（Qwen模型开启json_mode后输出必定是合法JSON）
            # 不需要清理markdown代码块（```json...```）
            concepts = json.loads(response)
            
            # 验证和标准化每个概念
            valid_concepts = []
            for c in concepts:
                if isinstance(c, dict) and 'entity' in c:
                    # 处理importance字段（可能是字符串、None等）
                    importance_val = c.get('importance', 3)
                    if importance_val is None:
                        importance_val = 3  # 默认中等重要性
                    try:
                        # 限制范围在1-5之间
                        importance = min(5, max(1, int(importance_val)))
                    except (ValueError, TypeError):
                        importance = 3  # 解析失败用默认值
                    
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
        """从文本块中提取实体间语义关系(使用 Qwen 严格 JSON Schema)

        参数:
            text: 待提取关系的文本块;
            chunk_id: 文本块唯一标识符。

        返回:
            关系列表, 每条关系大致形如:
            {
                "node_1": 源实体名称,
                "node_2": 目标实体名称,
                "edge": 关系类型/描述,
                "weight": W1 权重(LLM 抽取关系的置信度, 这里固定为 0.8),
                "chunk_id": 来源文本块 ID
            }
            若解析失败或无有效关系, 返回 None。
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
    
    def extract_concepts_and_relationships(self, text: str, chunk_id: str = "", 
                                          context_hint: str = "") -> Tuple[Optional[List[Dict]], Optional[List[Dict]]]:
        """在一次 LLM 调用中同时抽取概念和关系（支持上下文提示）

        相比先调用 extract_concepts 再调用 extract_relationships, 这里使用统一的 JSON Schema
        一次性返回 concepts 与 relationships, 可以减少网络往返并提高整体一致性,
        也是上层 extract_from_chunks 默认使用的路径。

        参数:
            text: 待处理的文本块;
            chunk_id: 文本块唯一标识符;
            context_hint: 上下文提示，包含前文提到的核心实体，帮助保持一致性。

        返回:
            (concepts_list, relationships_list) 二元组:
            - concepts_list: 概念字典列表, 结构与 extract_concepts 返回值一致, 无结果时为 None;
            - relationships_list: 关系字典列表, 结构与 extract_relationships 返回值一致, 无结果时为 None。
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

{text}{context_hint}

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
    
    def extract_from_chunks(self, chunks: List[Dict], max_chunks: int = None, 
                           use_context_window: bool = True, 
                           context_window_size: int = 5) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """批量从多个文本块中抽取概念和关系（支持滑动窗口上下文）

        参数:
            chunks: 文本块字典列表, 每个元素至少包含 'text' 和 'chunk_id' 字段;
            max_chunks: 限制最多处理的块数, 为 None 时处理全部块(默认);
            use_context_window: 是否启用滑动窗口上下文机制，帮助保持跨块实体一致性;
            context_window_size: 上下文窗口大小，保留前 N 个核心实体作为上下文。

        返回:
            (concepts_df, relationships_df) 二元组:
            - concepts_df: 汇总所有成功块后得到的概念 DataFrame;
            - relationships_df: 汇总所有成功块后得到的关系 DataFrame。
        
        滑动窗口机制说明:
        - 在处理 Chunk N 时，将 Chunk N-1 中提取的高重要性实体作为上下文提示
        - 帮助 LLM 识别跨块的实体指代（如代词、简称等）
        - 提高实体抽取的一致性和准确性
        """
        import gc  # 导入垃圾回收模块
        import time  # 导入时间模块用于添加延迟
        
        # Limit chunks if max_chunks is specified
        if max_chunks and len(chunks) > max_chunks:
            logger.warning(f"Limiting processing to {max_chunks} chunks (out of {len(chunks)})")
            logger.warning("Set max_chunks=None in code to process all chunks")
            chunks = chunks[:max_chunks]
        
        all_concepts = []
        all_relationships = []
        
        # 滑动窗口上下文：存储前一个 chunk 的核心实体
        context_entities = []
        
        logger.info(f"Extracting concepts and relationships from {len(chunks)} chunks...")
        logger.info("Optimized: single LLM call per chunk with strict JSON Schema")
        logger.info("Model: Using Qwen2.5-Coder with enhanced structured output")
        if use_context_window:
            logger.info(f"Context Window: Enabled (size={context_window_size}, maintains cross-chunk entity consistency)")
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
            
            # 构建上下文提示（如果启用滑动窗口）
            context_hint = ""
            if use_context_window and context_entities:
                context_hint = f"\n\n**前文提到的核心实体**: {', '.join(context_entities[:context_window_size])}\n请注意保持实体名称的一致性。"
            
            # Extract both concepts and relationships in ONE call
            concepts, relationships = self.extract_concepts_and_relationships(
                text, chunk_id, context_hint=context_hint
            )
            
            if concepts:
                all_concepts.extend(concepts)
                logger.debug(f"Extracted {len(concepts)} concepts")
                
                # 更新滑动窗口上下文：保留高重要性实体
                if use_context_window:
                    chunk_core_entities = [
                        c['entity'] for c in concepts 
                        if c.get('importance', 0) >= 4  # 只保留重要性 >= 4 的实体
                    ][:context_window_size]
                    
                    # 合并到上下文列表，去重并保持顺序
                    for entity in chunk_core_entities:
                        if entity not in context_entities:
                            context_entities.insert(0, entity)
                    
                    # 限制上下文窗口大小
                    context_entities = context_entities[:context_window_size]
                    
                    if chunk_core_entities:
                        logger.debug(f"Context updated: {context_entities}")
            else:
                logger.debug("No concepts extracted")
                # 单块失败只计数并跳过,让管道尽量在其余块上继续跑完
                failed_chunks += 1
                continue
            
            if relationships:
                all_relationships.extend(relationships)
                logger.debug(f"Extracted {len(relationships)} relationships")
            
            successful_chunks += 1
            
            # 添加延迟避免Ollama过载（内存不足时尤其重要）
            time.sleep(0.5)
            
            # 每10个chunk执行一次垃圾回收，防止内存累积
            if i % 10 == 0:
                gc.collect()
                logger.debug(f"[Memory] Garbage collection executed at chunk {i}")
        
        logger.info(f"Extraction complete: {successful_chunks} successful, {failed_chunks} failed")
        logger.info(f"Total concepts: {len(all_concepts)}")
        logger.info(f"Total relationships: {len(all_relationships)}")
        
        concepts_df = pd.DataFrame(all_concepts) if all_concepts else pd.DataFrame()
        relationships_df = pd.DataFrame(all_relationships) if all_relationships else pd.DataFrame()
        
        logger.info(f"Extracted {len(concepts_df)} concepts and {len(relationships_df)} relationships")
        
        return concepts_df, relationships_df


class ContextualProximityAnalyzer:
    """基于上下文共现的关系分析器(W2)

    作用:
    - 在不调用 LLM 的前提下, 仅根据概念在同一文本块中的共现情况生成一批“弱关系”;
    - 这些关系赋予固定权重 W2, 后续与 LLM 抽取的 W1 关系在 merge_relationships 中合并。
    """
    
    @staticmethod
    def extract_proximity_relationships(chunks: List[Dict]) -> pd.DataFrame:
        """根据同一文本块内的共现情况生成关系(W2)

        规则:
        - 同一 chunk 中的任意两概念视为存在上下文关联;
        - 为每一对概念创建一条关系, edge 固定为 'co-occurs in', weight 固定为 0.5。

        参数:
            chunks: 含有已抽取概念的文本块列表, 每个元素通常包含 'concepts' 和 'chunk_id' 字段。

        返回:
            由共现关系构成的 DataFrame。
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
        """合并 LLM 抽取关系(W1) 和上下文共现关系(W2)

        规则:
        - 先将两类关系简单拼接在一起;
        - 按 (node_1, node_2) 成对分组, 对权重求和, 将 edge/chunk_id/source 等字段合并去重;
        - 最后把合并后的 weight 归一化到 [0,1] 区间, 便于后续按“强关系”排序。

        参数:
            llm_relationships: 来自 LLM 抽取的关系 DataFrame, 权重为 W1;
            proximity_relationships: 来自上下文共现分析的关系 DataFrame, 权重为 W2。

        返回:
            已聚合并归一化权重的关系 DataFrame。
        """
        if llm_relationships.empty and proximity_relationships.empty:
            return pd.DataFrame()
        
        # Combine both relationship types
        all_relationships = pd.concat(
            [llm_relationships, proximity_relationships],
            ignore_index=True
        )
        
        # Group by node pairs and aggregate: 将 LLM 关系(W1) 与上下文共现关系(W2) 的权重累加,并合并关系描述
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
