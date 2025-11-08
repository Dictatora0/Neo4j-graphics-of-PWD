"""
关系抽取模块
使用规则匹配 + 模式识别提取实体间关系
"""

import re
import pandas as pd
from typing import Dict, List, Tuple
from tqdm import tqdm
from logger_config import get_logger


class RelationExtractor:
    """关系抽取器"""
    
    def __init__(self):
        self.logger = get_logger('RelationExtractor')
        # 定义关系类型和对应的模式
        self.relation_patterns = {
            'hasPathogen': [
                (r'(.+?)的病原[体为是](.+?)[\。\,\；]', 1, 2),
                (r'(.+?)由(.+?)引起', 1, 2),
                (r'(.+?)是由(.+?)导致', 1, 2),
                (r'病原[体为](.+?)[\。\,]', None, 1),  # Disease -> Pathogen
                (r'(.+?)[是为](.+?)的病原', 2, 1),
                (r'Bursaphelenchus xylophilus', None, None),
            ],
            'hasHost': [
                (r'(.+?)侵染(.+?)[\。\,]', 1, 2),
                (r'(.+?)寄主[为是](.+?)[\。\,]', 1, 2),
                (r'(.+?)危害(.+?)[\。\,]', 1, 2),
                (r'在(.+?)上[发生传播]', None, 1),
                (r'感染(.+?)树', None, 1),
            ],
            'hasVector': [
                (r'(.+?)由(.+?)传播', 1, 2),
                (r'(.+?)通过(.+?)传播', 1, 2),
                (r'传播媒介[为是](.+?)[\。\,]', None, 1),
                (r'(.+?)[是为](.+?)的传播媒介', 2, 1),
                (r'(.+?)携带(.+?)[\。\,]', 1, 2),
            ],
            'hasSymptom': [
                (r'症状[为是包括有](.+?)[\。\,]', None, 1),
                (r'表现为(.+?)[\。\,]', None, 1),
                (r'出现(.+?)症状', None, 1),
                (r'(.+?)导致(.+?)[变色枯死萎蔫]', 1, 2),
            ],
            'controlledBy': [
                (r'(.+?)防治[方法措施][为是包括有](.+?)[\。\,]', 1, 2),
                (r'采用(.+?)[防治控制](.+?)[\。\,]', 1, 2),
                (r'通过(.+?)[防治控制除治]', None, 1),
                (r'(.+?)可以[防治控制](.+?)[\。\,]', 2, 1),
            ],
            'occursIn': [
                (r'(.+?)发生在(.+?)[\。\,]', 1, 2),
                (r'在(.+?)[发生分布]', None, 1),
                (r'(.+?)地区[发生有](.+?)[\。\,]', 1, 2),
            ],
            'affectedBy': [
                (r'(.+?)受(.+?)影响', 1, 2),
                (r'(.+?)与(.+?)[相关有关]', 1, 2),
                (r'(.+?)影响(.+?)[\。\,]', 2, 1),
            ],
            'transmits': [
                (r'(.+?)传播(.+?)[\。\,]', 1, 2),
                (r'(.+?)携带(.+?)[\。\,]', 1, 2),
            ],
            'infects': [
                (r'(.+?)感染(.+?)[\。\,]', 1, 2),
                (r'(.+?)侵染(.+?)[\。\,]', 1, 2),
            ],
        }
        
        # 特定实体对的关系映射
        self.entity_pair_relations = {
            ('Disease', 'Pathogen'): 'hasPathogen',
            ('Disease', 'Host'): 'hasHost',
            ('Disease', 'Vector'): 'hasVector',
            ('Disease', 'Symptom'): 'hasSymptom',
            ('Disease', 'ControlMeasure'): 'controlledBy',
            ('Disease', 'Region'): 'occursIn',
            ('Disease', 'EnvironmentalFactor'): 'affectedBy',
            ('Pathogen', 'Host'): 'infects',
            ('Pathogen', 'Vector'): 'transmits',
            ('Vector', 'Host'): 'infects',
            ('Vector', 'Pathogen'): 'transmits',
        }

        self.relation_confidence = {
            'hasPathogen': 0.85,
            'hasHost': 0.82,
            'hasVector': 0.8,
            'hasSymptom': 0.78,
            'controlledBy': 0.8,
            'occursIn': 0.78,
            'affectedBy': 0.75,
            'transmits': 0.78,
            'infects': 0.78,
        }

    def _build_entity_map(self, entities_df: pd.DataFrame, source_pdf: str) -> Dict[str, str]:
        pdf_entities = entities_df[entities_df['source_pdf'] == source_pdf]
        entity_map: Dict[str, str] = {}
        for _, row in pdf_entities.iterrows():
            name = row['name'].strip()
            if name and name not in entity_map:
                entity_map[name] = row['type']
        return entity_map

    def _validate_relation(self, head: str, relation: str, tail: str,
                           entity_map: Dict[str, str]) -> bool:
        head_type = entity_map.get(head)
        tail_type = entity_map.get(tail)
        if not head_type or not tail_type:
            return False
        expected = self.entity_pair_relations.get((head_type, tail_type))
        if expected and expected != relation:
            return False
        # 限制 occursIn 等关系方向
        if relation in ['hasPathogen', 'hasHost', 'hasVector', 'hasSymptom', 'controlledBy', 'occursIn']:
            if head_type != 'Disease':
                return False
        if relation == 'affectedBy' and head_type != 'Disease':
            return False
        if relation == 'transmits' and head_type not in ['Vector', 'Pathogen']:
            return False
        if relation == 'infects' and head_type not in ['Pathogen', 'Vector']:
            return False
        return True
    
    def extract_relations_by_pattern(self, text: str, entities_df: pd.DataFrame, 
                                     source_pdf: str) -> List[Tuple[str, str, str, str, float]]:
        """使用模式匹配提取关系"""
        relations = []
        entity_map = self._build_entity_map(entities_df, source_pdf)
        
        # 遍历所有关系模式
        for relation_type, patterns in self.relation_patterns.items():
            for pattern_info in patterns:
                if len(pattern_info) == 3:
                    pattern, head_idx, tail_idx = pattern_info
                    matches = re.finditer(pattern, text)
                    
                    for match in matches:
                        try:
                            if head_idx is None:
                                # 默认头实体为疾病
                                head = "松材线虫病"
                                tail = match.group(tail_idx).strip()
                            elif tail_idx is None:
                                head = match.group(head_idx).strip()
                                tail = "松材线虫病"
                            else:
                                head = match.group(head_idx).strip()
                                tail = match.group(tail_idx).strip()
                            
                            # 清洗实体
                            head = self.clean_entity(head)
                            tail = self.clean_entity(tail)
                            
                            if head and tail and head != tail and self._validate_relation(head, relation_type, tail, entity_map):
                                confidence = self.relation_confidence.get(relation_type, 0.75)
                                # 如果默认疾病被填充，降低置信度
                                if head == "松材线虫病" or tail == "松材线虫病":
                                    confidence = min(confidence, 0.72)
                                relations.append((head, relation_type, tail, source_pdf, confidence))
                        except:
                            continue
        
        return relations
    
    def extract_relations_by_cooccurrence(self, text: str, entities_df: pd.DataFrame, 
                                          source_pdf: str, window_size: int = 100) -> List[Tuple[str, str, str, str, float]]:
        """基于共现提取关系"""
        relations = []
        entity_map = self._build_entity_map(entities_df, source_pdf)
        if not entity_map:
            return relations

        sentences = [s.strip() for s in text.split('\n') if s.strip()]
        for sentence in sentences:
            sentence_entities = [name for name in entity_map.keys() if name in sentence]
            if len(sentence_entities) < 2:
                continue
            for i, head in enumerate(sentence_entities):
                for tail in sentence_entities[i + 1:]:
                    if head == tail:
                        continue
                    head_type = entity_map.get(head)
                    tail_type = entity_map.get(tail)
                    relation = self.entity_pair_relations.get((head_type, tail_type))
                    if relation and self._validate_relation(head, relation, tail, entity_map):
                        confidence = min(self.relation_confidence.get(relation, 0.7) - 0.15, 0.7)
                        relations.append((head, relation, tail, source_pdf, confidence))
                    # 反向组合
                    relation_rev = self.entity_pair_relations.get((tail_type, head_type))
                    if relation_rev and self._validate_relation(tail, relation_rev, head, entity_map):
                        confidence = min(self.relation_confidence.get(relation_rev, 0.7) - 0.15, 0.7)
                        relations.append((tail, relation_rev, head, source_pdf, confidence))
        
        return relations
    
    def clean_entity(self, entity: str) -> str:
        """清洗实体名称"""
        # 移除标点符号
        entity = re.sub(r'[，。；！？、（）【】《》""''：]', '', entity)
        # 移除多余空格
        entity = entity.strip()
        # 限制长度
        if len(entity) > 50:
            return ""
        return entity
    
    def extract_all_relations(self, pdf_texts: Dict[str, str], 
                             entities_df: pd.DataFrame) -> pd.DataFrame:
        """从所有PDF中提取关系"""
        all_relations = []
        
        for pdf_name, text in tqdm(pdf_texts.items(), desc="提取关系"):
            # 模式匹配
            pattern_relations = self.extract_relations_by_pattern(text, entities_df, pdf_name)
            all_relations.extend(pattern_relations)
            
            # 共现关系
            cooccur_relations = self.extract_relations_by_cooccurrence(text, entities_df, pdf_name)
            all_relations.extend(cooccur_relations)
            
            print(f"✓ {pdf_name}: 提取了 {len(pattern_relations) + len(cooccur_relations)} 个关系")
        
        # 转换为DataFrame
        df = pd.DataFrame(all_relations, columns=['head', 'relation', 'tail', 'source_pdf', 'confidence'])
        
        print(f"\n总共提取了 {len(df)} 个关系")
        print("\n关系类型分布:")
        print(df['relation'].value_counts())
        
        return df


if __name__ == "__main__":
    import os
    
    # 读取提取的文本
    text_dir = "./output/extracted_texts"
    pdf_texts = {}
    
    for filename in os.listdir(text_dir):
        if filename.endswith('.txt'):
            with open(os.path.join(text_dir, filename), 'r', encoding='utf-8') as f:
                pdf_texts[filename.replace('.txt', '.pdf')] = f.read()
    
    # 读取实体
    entities_df = pd.read_csv("./output/entities.csv", encoding='utf-8-sig')
    
    # 提取关系
    extractor = RelationExtractor()
    relations_df = extractor.extract_all_relations(pdf_texts, entities_df)
    
    # 保存结果
    relations_df.to_csv("./output/relations.csv", index=False, encoding='utf-8-sig')
    print(f"\n关系数据已保存到: ./output/relations.csv")

