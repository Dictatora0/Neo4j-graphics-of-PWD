"""
数据清洗和规范化模块
对提取的实体和关系进行去重、同义词合并、质量过滤
"""

import pandas as pd
import re
from typing import Dict, Set
from difflib import SequenceMatcher
from logger_config import get_logger


class DataCleaner:
    """数据清洗器"""
    
    def __init__(self, confidence_threshold: float = 0.65):
        self.logger = get_logger('DataCleaner')
        self.confidence_threshold = confidence_threshold
        self.min_entity_length = 2
        self.max_entity_length = 30
        self.max_spaces = 2
        self.max_digit_ratio = 0.3
        self.chinese_punct_pattern = re.compile(r'[，。；！？、【】《》“”『』「」：；…]')
        self.invalid_token_pattern = re.compile(r'^[\W_]+$')
        
        self.valid_relation_pairs = {
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
        
        # 同义词映射表
        self.synonym_map = {
            '松材线虫病': ['PWD', 'Pine Wilt Disease', '松树萎蔫病', '松树枯萎病', '松枯萎病'],
            '松材线虫': ['Bursaphelenchus xylophilus', '病原线虫', '松树线虫'],
            '松褐天牛': ['Monochamus alternatus', '松天牛'],
            '马尾松': ['Pinus massoniana'],
            '黑松': ['Pinus thunbergii'],
            '针叶变色': ['针叶褐变', '针叶黄化'],
            '清理病死树': ['疫木除治', '病死木清理'],
        }
        
        # 构建反向映射
        self.reverse_synonym_map = {}
        for standard_term, synonyms in self.synonym_map.items():
            self.reverse_synonym_map[standard_term] = standard_term
            for synonym in synonyms:
                self.reverse_synonym_map[synonym] = standard_term
    
    def normalize_entity_name(self, name: str) -> str:
        """规范化实体名称"""
        # 查找同义词
        if name in self.reverse_synonym_map:
            return self.reverse_synonym_map[name]
        
        # 清理无效字符
        name = re.sub(r'["“”‘’]', '', name)
        name = name.replace('·', '').replace('_', ' ').replace('—', ' ')
        name = re.sub(r'\s+', ' ', name).strip()
        if len(name) > self.max_entity_length:
            name = name[:self.max_entity_length].strip()
        return name

    def is_valid_entity(self, name: str) -> bool:
        if not name:
            return False
        if len(name) < self.min_entity_length or len(name) > self.max_entity_length:
            return False
        if name.count(' ') > self.max_spaces:
            return False
        if self.chinese_punct_pattern.search(name):
            return False
        if self.invalid_token_pattern.match(name):
            return False
        digits = sum(c.isdigit() for c in name)
        if digits and digits / len(name) > self.max_digit_ratio:
            return False
        return True
    
    def similarity(self, a: str, b: str) -> float:
        """计算字符串相似度"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def merge_similar_entities(self, entities_df: pd.DataFrame, 
                               threshold: float = 0.85) -> pd.DataFrame:
        """合并相似实体"""
        temp_df = entities_df.copy()
        temp_df['normalized_name'] = temp_df['name'].apply(self.normalize_entity_name)
        frequency_map = temp_df.groupby(['type', 'normalized_name']).size().to_dict()
        merged_entities = []
        
        for entity_type in temp_df['type'].unique():
            type_entities = temp_df[temp_df['type'] == entity_type].copy()
            
            # 去重
            type_entities = type_entities.drop_duplicates(subset=['normalized_name', 'type'])
            type_entities = type_entities[type_entities['normalized_name'].apply(self.is_valid_entity)]
            
            # 查找相似实体
            processed = set()
            
            for idx1, row1 in type_entities.iterrows():
                if row1['normalized_name'] in processed:
                    continue
                
                group = [row1['normalized_name']]
                processed.add(row1['normalized_name'])
                
                for idx2, row2 in type_entities.iterrows():
                    if idx1 >= idx2 or row2['normalized_name'] in processed:
                        continue
                    
                    if self.similarity(row1['normalized_name'], row2['normalized_name']) >= threshold:
                        group.append(row2['normalized_name'])
                        processed.add(row2['normalized_name'])
                
                # 选择出现频次最高且长度较短的名称作为代表
                representative = max(
                    group,
                    key=lambda name: (frequency_map.get((entity_type, name), 0), -len(name))
                )
                
                for name in group:
                    matched_rows = type_entities[type_entities['normalized_name'] == name]
                    for _, row in matched_rows.iterrows():
                        merged_entities.append({
                            'id': row['id'],
                            'name': representative,
                            'original_name': row['name'],
                            'type': row['type'],
                            'source_pdf': row['source_pdf']
                        })
        
        result_df = pd.DataFrame(merged_entities)
        
        # 重新分配ID
        result_df = result_df.drop_duplicates(subset=['name', 'type'])
        result_df = result_df.reset_index(drop=True)
        result_df['id'] = range(1, len(result_df) + 1)
        result_df = result_df[['id', 'name', 'type', 'source_pdf']]
        
        return result_df
    
    def clean_entities(self, entities_df: pd.DataFrame) -> pd.DataFrame:
        """清洗实体数据"""
        self.logger.info("开始清洗实体数据...")
        print("开始清洗实体数据...")
        
        original_count = len(entities_df)
        
        # 1. 移除空名称
        entities_df = entities_df[entities_df['name'].notna()]
        entities_df = entities_df[entities_df['name'].str.strip() != '']
        self.logger.info(f"  移除空名称后: {len(entities_df)} 个实体")
        
        # 2. 移除过长或过短的实体
        entities_df = entities_df[entities_df['name'].str.len() >= self.min_entity_length]
        entities_df = entities_df[entities_df['name'].str.len() <= self.max_entity_length]
        self.logger.info(f"  长度过滤后: {len(entities_df)} 个实体")
        
        # 3. 移除纯数字或纯符号的实体
        entities_df = entities_df[~entities_df['name'].str.match(r'^[\d\W]+$')]
        self.logger.info(f"  符号过滤后: {len(entities_df)} 个实体")
        
        # 4. 规范化实体名称
        entities_df['name'] = entities_df['name'].apply(self.normalize_entity_name)
        entities_df = entities_df[entities_df['name'].apply(self.is_valid_entity)]
        self.logger.info(f"  规范化后: {len(entities_df)} 个实体")
        
        # 5. 合并相似实体
        entities_df = self.merge_similar_entities(entities_df)
        
        final_count = len(entities_df)
        removed_count = original_count - final_count
        self.logger.info(f"清洗完成: 保留 {final_count} 个实体，移除 {removed_count} 个 ({removed_count/original_count*100:.1f}%)")
        
        print(f"清洗后保留 {len(entities_df)} 个实体")
        print("\n清洗后实体类型分布:")
        print(entities_df['type'].value_counts())
        
        return entities_df
    
    def clean_relations(self, relations_df: pd.DataFrame, 
                       entities_df: pd.DataFrame) -> pd.DataFrame:
        """清洗关系数据"""
        self.logger.info("开始清洗关系数据...")
        print("\n开始清洗关系数据...")
        
        original_count = len(relations_df)
        
        # 1. 规范化实体名称（先规范化关系中的实体）
        relations_df = relations_df.copy()
        relations_df['head'] = relations_df['head'].apply(self.normalize_entity_name)
        relations_df['tail'] = relations_df['tail'].apply(self.normalize_entity_name)
        
        self.logger.info(f"规范化后: {len(relations_df)} 个关系")
        
        # 2. 获取有效实体集合和类型映射（使用清洗后的实体）
        valid_entities = set(entities_df['name'].unique())
        entity_type_map = dict(zip(entities_df['name'], entities_df['type']))
        
        self.logger.info(f"有效实体数: {len(valid_entities)}")
        self.logger.info(f"实体类型映射数: {len(entity_type_map)}")
        
        # 3. 过滤置信度低的关系
        before_conf = len(relations_df)
        relations_df = relations_df[relations_df['confidence'] >= self.confidence_threshold]
        self.logger.info(f"置信度过滤 (>={self.confidence_threshold}): {len(relations_df)} 个关系 (移除 {before_conf - len(relations_df)})")
        
        # 4. 移除自环关系
        before_self = len(relations_df)
        relations_df = relations_df[relations_df['head'] != relations_df['tail']]
        self.logger.info(f"移除自环: {len(relations_df)} 个关系 (移除 {before_self - len(relations_df)})")
        
        # 5. 只保留有效实体的关系
        before_valid = len(relations_df)
        relations_df = relations_df[
            relations_df['head'].isin(valid_entities) & 
            relations_df['tail'].isin(valid_entities)
        ]
        self.logger.info(f"实体有效性过滤: {len(relations_df)} 个关系 (移除 {before_valid - len(relations_df)})")
        
        # 5. 验证关系方向
        def is_valid_relation(row) -> bool:
            head_type = entity_type_map.get(row['head'])
            tail_type = entity_type_map.get(row['tail'])
            expected = self.valid_relation_pairs.get((head_type, tail_type))
            if expected and expected != row['relation']:
                return False
            if row['relation'] in ['hasPathogen', 'hasHost', 'hasVector', 'hasSymptom', 'controlledBy', 'occursIn'] and head_type != 'Disease':
                return False
            if row['relation'] == 'affectedBy' and head_type != 'Disease':
                return False
            if row['relation'] == 'transmits' and head_type not in ['Pathogen', 'Vector']:
                return False
            if row['relation'] == 'infects' and head_type not in ['Pathogen', 'Vector']:
                return False
            return True

        relations_df = relations_df[relations_df.apply(is_valid_relation, axis=1)]
        
        self.logger.info(f"关系方向验证后: {len(relations_df)} 个关系")
        
        # 检查 DataFrame 结构
        if len(relations_df) == 0:
            self.logger.warning("关系验证后 DataFrame 为空")
            return pd.DataFrame(columns=['head', 'relation', 'tail', 'source_pdf', 'confidence'])
        
        # 确保DataFrame有正确的列
        required_cols = ['head', 'relation', 'tail', 'source_pdf', 'confidence']
        missing_cols = [col for col in required_cols if col not in relations_df.columns]
        if missing_cols:
            self.logger.error(f"DataFrame缺少必需列: {missing_cols}")
            self.logger.error(f"实际列: {list(relations_df.columns)}")
            raise ValueError(f"DataFrame缺少必需列: {missing_cols}")
        
        self.logger.info(f"DataFrame列名: {list(relations_df.columns)}")
        self.logger.info(f"DataFrame形状: {relations_df.shape}")

        # 6. 低频过滤（保留高置信度）
        try:
            combo_counts = relations_df.groupby(['head', 'relation', 'tail']).size().to_dict()
        except KeyError as e:
            self.logger.error(f"分组操作失败: {e}")
            self.logger.error(f"DataFrame列: {list(relations_df.columns)}")
            self.logger.error(f"DataFrame前5行:\n{relations_df.head()}")
            raise
        def filter_low_frequency(row):
            freq = combo_counts.get((row['head'], row['relation'], row['tail']), 0)
            if freq >= 2:
                return True
            return row['confidence'] >= 0.75

        relations_df = relations_df[relations_df.apply(filter_low_frequency, axis=1)]

        # 7. 去重
        relations_df = relations_df.drop_duplicates(subset=['head', 'relation', 'tail', 'source_pdf'])
        
        # 8. 重置索引
        relations_df = relations_df.reset_index(drop=True)
        
        final_count = len(relations_df)
        removed_count = original_count - final_count
        self.logger.info(f"清洗完成: 保留 {final_count} 个关系，移除 {removed_count} 个 ({removed_count/original_count*100:.1f}%)")
        
        print(f"清洗后保留 {len(relations_df)} 个关系")
        print("\n清洗后关系类型分布:")
        print(relations_df['relation'].value_counts())
        
        return relations_df


if __name__ == "__main__":
    import os
    
    # 读取原始数据
    entities_df = pd.read_csv("./output/entities.csv", encoding='utf-8-sig')
    relations_df = pd.read_csv("./output/relations.csv", encoding='utf-8-sig')
    
    # 清洗数据
    cleaner = DataCleaner(confidence_threshold=0.65)
    
    entities_clean = cleaner.clean_entities(entities_df)
    relations_clean = cleaner.clean_relations(relations_df, entities_clean)
    
    # 保存清洗后的数据
    os.makedirs("./output", exist_ok=True)
    entities_clean.to_csv("./output/entities_clean.csv", index=False, encoding='utf-8-sig')
    relations_clean.to_csv("./output/relations_clean.csv", index=False, encoding='utf-8-sig')
    
    print("\n清洗后的数据已保存:")
    print("  - ./output/entities_clean.csv")
    print("  - ./output/relations_clean.csv")

