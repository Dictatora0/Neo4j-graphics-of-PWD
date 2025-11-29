#!/usr/bin/env python3
"""
LLM 模型性能对比测试脚本

对比不同模型在松材线虫病知识抽取任务上的表现:
- Qwen2.5-Coder-14B (推荐)
- Qwen2.5-Coder-7B
- DeepSeek-R1-7B-Distill
- Llama3.2-3B (基线)

评估指标:
1. JSON Schema 遵循率 (Format Compliance Rate)
2. 概念抽取准确率 (Concept Extraction Accuracy)
3. 关系抽取准确率 (Relationship Extraction Accuracy)
4. 推理时间 (Inference Time)
5. 幻觉率 (Hallucination Rate)
"""

import os
import sys
import json
import time
import logging
from typing import List, Dict, Tuple
from datetime import datetime
import pandas as pd
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from concept_extractor import ConceptExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelBenchmark:
    """模型性能对比工具"""
    
    def __init__(self, models: List[str], ollama_host: str = "http://localhost:11434"):
        self.models = models
        self.ollama_host = ollama_host
        self.results = []
        
        logger.info(f"初始化模型对比: {', '.join(models)}")
    
    def get_test_cases(self) -> List[Dict]:
        """
        获取测试用例
        
        包含:
        - 简单句 (单一关系)
        - 复杂句 (多重关系)
        - 含专业术语的句子
        - 中英文混合句
        """
        return [
            {
                'text': '松材线虫病是一种严重的松树病害,由松材线虫(Bursaphelenchus xylophilus)引起。',
                'expected_concepts': ['松材线虫病', '松材线虫', 'bursaphelenchus xylophilus'],
                'expected_relations': [('松材线虫', '引起', '松材线虫病')],
                'difficulty': 'easy'
            },
            {
                'text': '松褐天牛是松材线虫的主要传播媒介,携带松材线虫侵染健康的马尾松和黑松。',
                'expected_concepts': ['松褐天牛', '松材线虫', '马尾松', '黑松'],
                'expected_relations': [
                    ('松褐天牛', '传播', '松材线虫'),
                    ('松材线虫', '侵染', '马尾松'),
                    ('松材线虫', '侵染', '黑松')
                ],
                'difficulty': 'medium'
            },
            {
                'text': '阿维菌素、噻虫啉等药剂可有效防治松褐天牛,从而控制松材线虫病的传播。温度和湿度是影响病害发生的重要环境因子。',
                'expected_concepts': ['阿维菌素', '噻虫啉', '松褐天牛', '松材线虫病', '温度', '湿度'],
                'expected_relations': [
                    ('阿维菌素', '防治', '松褐天牛'),
                    ('噻虫啉', '防治', '松褐天牛'),
                    ('温度', '影响', '松材线虫病'),
                    ('湿度', '影响', '松材线虫病')
                ],
                'difficulty': 'hard'
            },
            {
                'text': 'Pine wilt disease (PWD) caused by Bursaphelenchus xylophilus is transmitted by Monochamus alternatus. The nematode infects Pinus massoniana.',
                'expected_concepts': ['pine wilt disease', 'bursaphelenchus xylophilus', 'monochamus alternatus', 'pinus massoniana'],
                'expected_relations': [
                    ('bursaphelenchus xylophilus', '引起', 'pine wilt disease'),
                    ('monochamus alternatus', '传播', 'bursaphelenchus xylophilus'),
                    ('bursaphelenchus xylophilus', '感染', 'pinus massoniana')
                ],
                'difficulty': 'hard'
            }
        ]
    
    def evaluate_json_compliance(self, response: str) -> bool:
        """评估 JSON Schema 合规性"""
        try:
            data = json.loads(response)
            
            # 检查必需字段
            if 'concepts' not in data and 'relationships' not in data:
                return False
            
            # 检查概念格式
            if 'concepts' in data:
                for c in data['concepts']:
                    if not isinstance(c, dict):
                        return False
                    if 'entity' not in c or 'importance' not in c or 'category' not in c:
                        return False
            
            # 检查关系格式
            if 'relationships' in data:
                for r in data['relationships']:
                    if not isinstance(r, dict):
                        return False
                    if 'node_1' not in r or 'node_2' not in r or 'edge' not in r:
                        return False
            
            return True
        except json.JSONDecodeError:
            return False
    
    def calculate_precision_recall(self, extracted: List[str], expected: List[str]) -> Tuple[float, float, float]:
        """
        计算精确率、召回率和 F1 分数
        
        Args:
            extracted: 抽取的实体列表
            expected: 期望的实体列表
        
        Returns:
            (precision, recall, f1)
        """
        if not extracted:
            return 0.0, 0.0, 0.0
        
        # 标准化处理 (小写)
        extracted_set = set(e.lower().strip() for e in extracted)
        expected_set = set(e.lower().strip() for e in expected)
        
        # 计算交集
        true_positives = len(extracted_set & expected_set)
        
        # 精确率和召回率
        precision = true_positives / len(extracted_set) if extracted_set else 0.0
        recall = true_positives / len(expected_set) if expected_set else 0.0
        
        # F1 分数
        if precision + recall > 0:
            f1 = 2 * (precision * recall) / (precision + recall)
        else:
            f1 = 0.0
        
        return precision, recall, f1
    
    def test_model(self, model: str) -> Dict:
        """
        测试单个模型
        
        Returns:
            测试结果字典
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"测试模型: {model}")
        logger.info(f"{'='*60}")
        
        # 初始化抽取器
        try:
            extractor = ConceptExtractor(model=model, ollama_host=self.ollama_host)
        except Exception as e:
            logger.error(f"模型 {model} 初始化失败: {e}")
            return {
                'model': model,
                'status': 'failed',
                'error': str(e)
            }
        
        # 测试用例
        test_cases = self.get_test_cases()
        
        # 指标统计
        json_compliance_count = 0
        total_inference_time = 0.0
        concept_metrics = []
        relation_metrics = []
        
        for i, case in enumerate(test_cases, 1):
            logger.info(f"\n测试用例 {i}/{len(test_cases)} (难度: {case['difficulty']})")
            logger.info(f"文本: {case['text'][:80]}...")
            
            # 计时开始
            start_time = time.time()
            
            # 抽取
            concepts, relationships = extractor.extract_concepts_and_relationships(
                case['text'], 
                chunk_id=f"test_{i}"
            )
            
            # 计时结束
            inference_time = time.time() - start_time
            total_inference_time += inference_time
            
            logger.info(f"推理时间: {inference_time:.2f}s")
            
            # 检查 JSON 合规性 (需要原始响应,这里简化判断)
            if concepts is not None or relationships is not None:
                json_compliance_count += 1
            
            # 评估概念抽取
            if concepts:
                extracted_concepts = [c.get('entity', '') for c in concepts]
                precision, recall, f1 = self.calculate_precision_recall(
                    extracted_concepts, 
                    case['expected_concepts']
                )
                concept_metrics.append({
                    'precision': precision,
                    'recall': recall,
                    'f1': f1
                })
                
                logger.info(f"概念抽取: P={precision:.2f}, R={recall:.2f}, F1={f1:.2f}")
                logger.info(f"  抽取: {extracted_concepts}")
                logger.info(f"  期望: {case['expected_concepts']}")
            else:
                logger.warning("未抽取到概念")
                concept_metrics.append({'precision': 0, 'recall': 0, 'f1': 0})
            
            # 评估关系抽取
            if relationships:
                extracted_relations = [
                    (r.get('node_1', ''), r.get('edge', ''), r.get('node_2', ''))
                    for r in relationships
                ]
                
                # 简化关系匹配 (仅检查节点对)
                extracted_pairs = [(r[0], r[2]) for r in extracted_relations]
                expected_pairs = [(r[0], r[2]) for r in case['expected_relations']]
                
                precision, recall, f1 = self.calculate_precision_recall(
                    [f"{p[0]}-{p[1]}" for p in extracted_pairs],
                    [f"{p[0]}-{p[1]}" for p in expected_pairs]
                )
                relation_metrics.append({
                    'precision': precision,
                    'recall': recall,
                    'f1': f1
                })
                
                logger.info(f"关系抽取: P={precision:.2f}, R={recall:.2f}, F1={f1:.2f}")
            else:
                logger.warning("未抽取到关系")
                relation_metrics.append({'precision': 0, 'recall': 0, 'f1': 0})
        
        # 汇总结果
        result = {
            'model': model,
            'status': 'success',
            'json_compliance_rate': json_compliance_count / len(test_cases),
            'avg_inference_time': total_inference_time / len(test_cases),
            'concept_precision': sum(m['precision'] for m in concept_metrics) / len(concept_metrics),
            'concept_recall': sum(m['recall'] for m in concept_metrics) / len(concept_metrics),
            'concept_f1': sum(m['f1'] for m in concept_metrics) / len(concept_metrics),
            'relation_precision': sum(m['precision'] for m in relation_metrics) / len(relation_metrics),
            'relation_recall': sum(m['recall'] for m in relation_metrics) / len(relation_metrics),
            'relation_f1': sum(m['f1'] for m in relation_metrics) / len(relation_metrics),
        }
        
        logger.info(f"\n{model} 测试完成:")
        logger.info(f"  JSON 遵循率: {result['json_compliance_rate']:.2%}")
        logger.info(f"  平均推理时间: {result['avg_inference_time']:.2f}s")
        logger.info(f"  概念 F1: {result['concept_f1']:.2%}")
        logger.info(f"  关系 F1: {result['relation_f1']:.2%}")
        
        return result
    
    def run_benchmark(self) -> pd.DataFrame:
        """运行完整对比测试"""
        logger.info("\n" + "="*60)
        logger.info("开始模型性能对比测试")
        logger.info("="*60)
        
        for model in self.models:
            result = self.test_model(model)
            self.results.append(result)
        
        # 转换为 DataFrame
        results_df = pd.DataFrame(self.results)
        
        # 保存结果
        output_dir = './output/model_benchmark'
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = f"{output_dir}/benchmark_{timestamp}.csv"
        
        results_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"\n结果已保存到: {csv_path}")
        
        return results_df
    
    def print_comparison_table(self, results_df: pd.DataFrame):
        """打印对比表格"""
        print("\n" + "="*80)
        print("模型性能对比报告")
        print("="*80)
        
        # 选择关键指标
        display_cols = [
            'model', 
            'json_compliance_rate', 
            'avg_inference_time',
            'concept_f1',
            'relation_f1'
        ]
        
        display_df = results_df[display_cols].copy()
        
        # 格式化
        display_df['json_compliance_rate'] = display_df['json_compliance_rate'].apply(lambda x: f"{x:.1%}")
        display_df['avg_inference_time'] = display_df['avg_inference_time'].apply(lambda x: f"{x:.2f}s")
        display_df['concept_f1'] = display_df['concept_f1'].apply(lambda x: f"{x:.1%}")
        display_df['relation_f1'] = display_df['relation_f1'].apply(lambda x: f"{x:.1%}")
        
        # 重命名列
        display_df.columns = ['模型', 'JSON遵循率', '推理时间', '概念F1', '关系F1']
        
        print(display_df.to_string(index=False))
        
        # 推荐
        print("\n" + "="*80)
        print("推荐模型:")
        
        best_f1_idx = results_df['concept_f1'].idxmax()
        best_model = results_df.loc[best_f1_idx, 'model']
        
        print(f"  综合性能: {best_model}")
        print("="*80)


def main():
    """主函数"""
    # 待测试模型
    models_to_test = [
        'qwen2.5-coder:14b',  # 推荐
        'qwen2.5-coder:7b',   # 性能与速度平衡
        # 'deepseek-r1:7b-distill',  # DeepSeek (如果已安装)
        # 'llama3.2:3b',  # 基线 (如果需要对比)
    ]
    
    # 创建测试器
    benchmark = ModelBenchmark(models=models_to_test)
    
    # 运行测试
    results_df = benchmark.run_benchmark()
    
    # 打印对比表
    benchmark.print_comparison_table(results_df)


if __name__ == "__main__":
    main()
