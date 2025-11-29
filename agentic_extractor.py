#!/usr/bin/env python3
"""
Agentic Workflow for Knowledge Extraction
基于 LangGraph 范式的多智能体协作抽取系统

包含三个核心 Agent:
1. Extract Agent: 初次抽取概念和关系
2. Critic Agent: 审查抽取质量,识别错误和逻辑谬误
3. Refine Agent: 根据审稿意见修正和优化结果
"""

import json
import logging
from typing import List, Dict, Tuple, Optional
import requests
from dataclasses import dataclass
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """抽取结果数据类"""
    concepts: List[Dict]
    relationships: List[Dict]
    confidence: float
    issues: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []


class CriticAgent:
    """
    审稿人 Agent - 检查抽取结果的质量
    
    功能:
    1. 本体符合性检查: 概念类别是否符合领域定义
    2. 逻辑一致性检查: 关系是否存在逻辑谬误
    3. 完整性检查: 是否遗漏关键信息
    4. 格式规范检查: JSON Schema 合规性
    """
    
    def __init__(self, model: str, ollama_host: str):
        self.model = model
        self.ollama_host = ollama_host
        self.api_endpoint = f"{ollama_host}/api/generate"
        
        # 本体定义 (领域知识库)
        self.ontology = {
            'valid_categories': ['pathogen', 'host', 'vector', 'symptom', 'treatment', 
                               'environment', 'location', 'mechanism', 'compound'],
            'valid_relations': ['引起', '导致', '诱发', '传播', '携带', '扩散', 
                              '感染', '寄生于', '侵染', '防治', '控制', '抑制', 
                              '杀灭', '影响', '促进', '分布于', '发生于'],
            'logical_constraints': {
                # 关系方向约束: (source_category, relation, target_category)
                ('pathogen', '感染', 'host'),
                ('vector', '传播', 'pathogen'),
                ('treatment', '防治', 'pathogen'),
                ('treatment', '控制', 'vector'),
                ('environment', '影响', 'pathogen'),
            }
        }
    
    def _call_ollama(self, prompt: str, system_prompt: str = "", temperature: float = 0.1) -> Optional[str]:
        """调用 Ollama API"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "temperature": temperature,
                "num_ctx": 4096,
            }
            
            if 'qwen' in self.model.lower():
                payload["format"] = "json"
            
            response = requests.post(self.api_endpoint, json=payload, timeout=180)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '').strip()
        except Exception as e:
            logger.error(f"Critic Agent API error: {e}")
            return None
    
    def review_extraction(self, extraction: ExtractionResult, original_text: str) -> Dict:
        """
        审查抽取结果
        
        Args:
            extraction: 抽取结果对象
            original_text: 原始文本
        
        Returns:
            审查报告 {
                'overall_quality': float (0-1),
                'issues': List[str],
                'suggestions': List[str],
                'approved_concepts': List[str],
                'rejected_concepts': List[str],
                'approved_relations': List[Dict],
                'rejected_relations': List[Dict]
            }
        """
        system_prompt = """你是知识图谱质量审查专家。你的任务是严格审查抽取的概念和关系,识别错误、逻辑谬误和不符合本体的内容。

## 审查标准

### 概念审查
1. **本体符合性**: 类别必须属于 [pathogen, host, vector, symptom, treatment, environment, location, mechanism, compound]
2. **领域相关性**: 概念必须与松材线虫病直接相关
3. **过于宽泛**: 排除"因素"、"过程"、"机制"等泛化词
4. **重要性合理性**: 核心概念(如松材线虫)应为5分,次要概念应为1-3分

### 关系审查
1. **逻辑一致性**: 检查关系方向是否符合常识 (如"松树传播线虫"是错误的)
2. **文本支撑**: 关系必须在原文中有明确依据
3. **关系类型准确**: 使用标准关系词 [引起, 传播, 感染, 防治, 影响等]
4. **避免重复**: 同一对实体不应有多个相似关系

## 输出格式 (严格 JSON)
{
  "overall_quality": 0.8,
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"],
  "approved_concepts": ["概念1", "概念2"],
  "rejected_concepts": ["概念3(原因)"],
  "approved_relations": [{"node_1": "A", "node_2": "B", "edge": "关系"}],
  "rejected_relations": [{"node_1": "X", "node_2": "Y", "edge": "错误关系", "reason": "逻辑错误"}]
}"""
        
        # 构建审查提示
        concepts_str = json.dumps(extraction.concepts, ensure_ascii=False, indent=2)
        relations_str = json.dumps(extraction.relationships, ensure_ascii=False, indent=2)
        
        user_prompt = f"""请审查以下知识抽取结果:

**原始文本**:
{original_text[:800]}

**抽取的概念**:
{concepts_str}

**抽取的关系**:
{relations_str}

请严格按照审查标准输出 JSON 格式的审查报告。"""
        
        response = self._call_ollama(user_prompt, system_prompt, temperature=0.1)
        
        if not response:
            logger.warning("Critic Agent 未能生成审查报告")
            return self._default_review_report(extraction)
        
        try:
            review_report = json.loads(response)
            logger.info(f"Critic Agent 审查完成: 质量评分 {review_report.get('overall_quality', 0)}")
            return review_report
        except json.JSONDecodeError:
            logger.error("Critic Agent JSON 解析失败,使用默认审查")
            return self._default_review_report(extraction)
    
    def _default_review_report(self, extraction: ExtractionResult) -> Dict:
        """默认审查报告 (当 LLM 失败时)"""
        # 简单的规则审查
        approved_concepts = []
        rejected_concepts = []
        
        for concept in extraction.concepts:
            category = concept.get('category', '').lower()
            entity = concept.get('entity', '')
            
            # 检查类别是否合法
            if category in self.ontology['valid_categories']:
                approved_concepts.append(entity)
            else:
                rejected_concepts.append(f"{entity} (类别 '{category}' 不合法)")
        
        approved_relations = []
        rejected_relations = []
        
        for rel in extraction.relationships:
            edge = rel.get('edge', '')
            if any(valid_rel in edge for valid_rel in self.ontology['valid_relations']):
                approved_relations.append(rel)
            else:
                rejected_relations.append({
                    **rel,
                    'reason': f"关系类型 '{edge}' 不在标准列表中"
                })
        
        return {
            'overall_quality': 0.7,
            'issues': ["使用默认规则审查(LLM 不可用)"],
            'suggestions': ["建议启用 LLM 审查以获得更精准的质量控制"],
            'approved_concepts': approved_concepts,
            'rejected_concepts': rejected_concepts,
            'approved_relations': approved_relations,
            'rejected_relations': rejected_relations
        }


class RefineAgent:
    """
    修正 Agent - 根据审稿意见优化抽取结果
    
    功能:
    1. 移除被拒绝的概念和关系
    2. 修正概念类别和重要性评分
    3. 修正关系方向和类型
    4. 补充遗漏的关键信息
    """
    
    def __init__(self, model: str, ollama_host: str):
        self.model = model
        self.ollama_host = ollama_host
        self.api_endpoint = f"{ollama_host}/api/generate"
    
    def _call_ollama(self, prompt: str, system_prompt: str = "", temperature: float = 0.1) -> Optional[str]:
        """调用 Ollama API"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "temperature": temperature,
                "num_ctx": 4096,
            }
            
            if 'qwen' in self.model.lower():
                payload["format"] = "json"
            
            response = requests.post(self.api_endpoint, json=payload, timeout=180)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '').strip()
        except Exception as e:
            logger.error(f"Refine Agent API error: {e}")
            return None
    
    def refine_extraction(self, extraction: ExtractionResult, review_report: Dict, 
                         original_text: str) -> ExtractionResult:
        """
        根据审查报告修正抽取结果
        
        Args:
            extraction: 原始抽取结果
            review_report: 审查报告
            original_text: 原始文本
        
        Returns:
            修正后的抽取结果
        """
        # 如果质量已经很高,直接返回
        if review_report.get('overall_quality', 0) >= 0.9:
            logger.info("抽取质量优秀,无需修正")
            return extraction
        
        system_prompt = """你是知识抽取修正专家。根据审查报告修正抽取结果中的错误。

## 修正任务
1. **移除被拒绝的概念和关系**
2. **修正概念类别**: 将错误类别改为正确类别
3. **修正关系方向**: 将逻辑错误的关系反转或删除
4. **补充遗漏**: 根据原文补充关键概念/关系

## 输出格式 (严格 JSON)
{
  "concepts": [
    {"entity": "概念名", "importance": 1-5, "category": "类别"}
  ],
  "relationships": [
    {"node_1": "源实体", "node_2": "目标实体", "edge": "关系"}
  ]
}"""
        
        concepts_str = json.dumps(extraction.concepts, ensure_ascii=False, indent=2)
        relations_str = json.dumps(extraction.relationships, ensure_ascii=False, indent=2)
        review_str = json.dumps({
            'issues': review_report.get('issues', []),
            'suggestions': review_report.get('suggestions', []),
            'rejected_concepts': review_report.get('rejected_concepts', []),
            'rejected_relations': review_report.get('rejected_relations', [])
        }, ensure_ascii=False, indent=2)
        
        user_prompt = f"""请根据审查报告修正以下抽取结果:

**原始文本**:
{original_text[:600]}

**当前抽取结果**:
概念: {concepts_str}
关系: {relations_str}

**审查报告**:
{review_str}

请输出修正后的概念和关系(JSON 格式)。"""
        
        response = self._call_ollama(user_prompt, system_prompt, temperature=0.1)
        
        if not response:
            logger.warning("Refine Agent 未能生成修正结果,使用规则修正")
            return self._rule_based_refine(extraction, review_report)
        
        try:
            refined_data = json.loads(response)
            
            # 标准化格式
            refined_concepts = []
            for c in refined_data.get('concepts', []):
                if isinstance(c, dict) and 'entity' in c:
                    refined_concepts.append({
                        'entity': str(c.get('entity', '')).lower().strip(),
                        'importance': min(5, max(1, int(c.get('importance', 3)))),
                        'category': str(c.get('category', 'misc')).lower(),
                        'type': 'concept'
                    })
            
            refined_relationships = []
            for r in refined_data.get('relationships', []):
                if isinstance(r, dict) and 'node_1' in r and 'node_2' in r:
                    refined_relationships.append({
                        'node_1': str(r.get('node_1', '')).lower().strip(),
                        'node_2': str(r.get('node_2', '')).lower().strip(),
                        'edge': str(r.get('edge', 'related to')).strip(),
                        'weight': 0.9,  # 修正后的结果置信度更高
                        'source': 'agentic_refined'
                    })
            
            logger.info(f"Refine Agent 完成: {len(refined_concepts)} 概念, {len(refined_relationships)} 关系")
            
            return ExtractionResult(
                concepts=refined_concepts,
                relationships=refined_relationships,
                confidence=min(1.0, review_report.get('overall_quality', 0.7) + 0.1),
                issues=[]
            )
        
        except json.JSONDecodeError:
            logger.error("Refine Agent JSON 解析失败,使用规则修正")
            return self._rule_based_refine(extraction, review_report)
    
    def _rule_based_refine(self, extraction: ExtractionResult, review_report: Dict) -> ExtractionResult:
        """基于规则的修正 (当 LLM 失败时)"""
        approved_concepts_set = set(review_report.get('approved_concepts', []))
        
        # 过滤概念
        refined_concepts = [
            c for c in extraction.concepts 
            if c.get('entity', '') in approved_concepts_set
        ]
        
        # 过滤关系
        refined_relationships = review_report.get('approved_relations', [])
        
        logger.info(f"规则修正: {len(refined_concepts)} 概念, {len(refined_relationships)} 关系")
        
        return ExtractionResult(
            concepts=refined_concepts,
            relationships=refined_relationships,
            confidence=review_report.get('overall_quality', 0.7),
            issues=review_report.get('issues', [])
        )


class AgenticExtractor:
    """
    Agentic 知识抽取器 - 整合 Extract → Critic → Refine 工作流
    
    工作流程:
    1. Extract Agent 初次抽取
    2. Critic Agent 审查质量
    3. 如果质量低于阈值,Refine Agent 修正
    4. 返回最终结果
    """
    
    def __init__(self, extract_agent, model: str, ollama_host: str, 
                 review_threshold: Tuple[float, float] = (0.6, 0.85)):
        """
        Args:
            extract_agent: 已初始化的 ConceptExtractor
            model: LLM 模型名称
            ollama_host: Ollama 服务地址
            review_threshold: 需要审查的质量范围 (最小值, 最大值)
        """
        self.extract_agent = extract_agent
        self.critic = CriticAgent(model, ollama_host)
        self.refiner = RefineAgent(model, ollama_host)
        self.review_threshold = review_threshold
        
        logger.info(f"Agentic Extractor 已初始化: 审查阈值 {review_threshold}")
    
    def extract_with_review(self, text: str, chunk_id: str = "") -> Tuple[List[Dict], List[Dict]]:
        """
        带审查的抽取流程
        
        Args:
            text: 文本内容
            chunk_id: 文本块 ID
        
        Returns:
            (concepts, relationships)
        """
        # Step 1: Extract Agent 初次抽取
        logger.debug(f"[{chunk_id}] Extract Agent 抽取中...")
        concepts, relationships = self.extract_agent.extract_concepts_and_relationships(text, chunk_id)
        
        if not concepts:
            logger.debug(f"[{chunk_id}] 未抽取到概念")
            return None, None
        
        extraction = ExtractionResult(
            concepts=concepts or [],
            relationships=relationships or [],
            confidence=0.7  # 初始置信度
        )
        
        # Step 2: Critic Agent 审查 (仅对中等质量结果审查)
        # 假设初始置信度在阈值范围内则审查
        if self.review_threshold[0] <= extraction.confidence <= self.review_threshold[1]:
            logger.debug(f"[{chunk_id}] Critic Agent 审查中...")
            review_report = self.critic.review_extraction(extraction, text)
            
            # Step 3: 如果质量不佳,Refine Agent 修正
            if review_report.get('overall_quality', 0) < 0.85:
                logger.debug(f"[{chunk_id}] Refine Agent 修正中...")
                extraction = self.refiner.refine_extraction(extraction, review_report, text)
        
        return extraction.concepts, extraction.relationships


if __name__ == "__main__":
    # 测试 Agentic Workflow
    from concept_extractor import ConceptExtractor
    
    # 初始化
    extract_agent = ConceptExtractor(model="qwen2.5-coder:14b")
    agentic = AgenticExtractor(
        extract_agent=extract_agent,
        model="qwen2.5-coder:14b",
        ollama_host="http://localhost:11434",
        review_threshold=(0.6, 0.85)
    )
    
    # 测试文本
    test_text = """
    松材线虫病是一种严重的松树病害,由松材线虫(Bursaphelenchus xylophilus)引起。
    松褐天牛是其主要传播媒介,携带松材线虫侵染健康松树。
    该病害在马尾松林中传播迅速,导致大面积松树枯死。
    """
    
    concepts, relationships = agentic.extract_with_review(test_text, "test_001")
    
    print("\n=== Agentic 抽取结果 ===")
    print(f"概念数量: {len(concepts) if concepts else 0}")
    print(f"关系数量: {len(relationships) if relationships else 0}")
    
    if concepts:
        print("\n概念:")
        for c in concepts:
            print(f"  - {c}")
    
    if relationships:
        print("\n关系:")
        for r in relationships:
            print(f"  - {r}")
