"""
实体消歧与链接模块
处理同名实体、代词指代、实体标准化等问题

整体流程总览(从原始实体列表到最终实体集):
原始实体列表
  ↓  (normalize_entity/merge_duplicate_entities 统一同义表达)
标准化实体 + 去重结果
  ↓  (resolve_coreference/resolve_pronouns_in_text 处理“该病/该虫”等代词引用)
消歧后的实体引用
  ↓  (identify_entity_clusters 在同类型内做字符串相似度聚类)
实体簇 + 代表实体
  ↓  (compute_entity_importance 根据连接数和类型打分)
带重要性得分的实体表
  ↓  (link_entities 统一调度上述步骤并返回最终实体/关系集)
最终可用于下游分析的实体集及其关系
"""

import re
import os
import pandas as pd
from typing import Dict, List, Set, Tuple, Optional
from difflib import SequenceMatcher
from logger_config import get_logger

logger = get_logger('EntityLinker')


class EntityLinker:
    """实体消歧与链接器"""
    
    def __init__(self):
        """初始化实体链接器"""
        self.logger = get_logger('EntityLinker')
        
        # 实体标准化映射（更全面的同义词表）
        self.standard_entities = {
            # 疾病标准化
            '松材线虫病': ['PWD', 'Pine Wilt Disease', 'pine wilt', 'pine wilt disease', 
                        '松树萎蔫病', '松树枯萎病', '松枯萎病', '松树疫病'],
            
            # 病原体标准化
            '松材线虫': ['Bursaphelenchus xylophilus', 'B. xylophilus', 
                       'pine wood nematode', '病原线虫', '松树线虫', '线虫病原'],
            
            # 宿主标准化
            '马尾松': ['Pinus massoniana', 'P. massoniana', 'masson pine'],
            '黑松': ['Pinus thunbergii', 'P. thunbergii', 'Japanese black pine', '日本黑松'],
            '赤松': ['Pinus densiflora', 'P. densiflora', 'Japanese red pine'],
            '油松': ['Pinus tabuliformis', 'P. tabuliformis', 'Chinese pine'],
            
            # 传播媒介标准化
            '松褐天牛': ['Monochamus alternatus', 'M. alternatus', '松天牛', '松墨天牛'],
            
            # 症状标准化
            '针叶变色': ['针叶褐变', '针叶黄化', '针叶枯黄'],
            '萎蔫': ['萎凋', '枯萎'],
            
            # 防治措施标准化
            '清理病死树': ['疫木除治', '病死木清理', '清除病木'],
            '化学防治': ['药物防治', '化学药剂防治'],
            
            # 地区标准化
            '浙江': ['浙江省', 'Zhejiang'],
            '江苏': ['江苏省', 'Jiangsu'],
            '山东': ['山东省', 'Shandong'],
        }
        
        # 构建反向索引: 把所有变体名称映射到统一的标准实体,后续标准化时只需一次查表
        self.entity_to_standard = {}
        for standard, variants in self.standard_entities.items():
            self.entity_to_standard[standard] = standard
            for variant in variants:
                self.entity_to_standard[variant.lower()] = standard
        
        # 代词映射（用于共指消解）
        self.pronouns = {
            '该病': '松材线虫病',
            '该虫': '松材线虫',
            '该树': '松树',
            '该天牛': '松褐天牛',
            'the disease': 'Pine Wilt Disease',
            'the nematode': 'Bursaphelenchus xylophilus',
            'PWD': '松材线虫病',
        }
        
        logger.info(f"实体链接器已初始化: {len(self.standard_entities)} 个标准实体")
    
    def normalize_entity(self, entity: str) -> str:
        """标准化实体名称
        
        Args:
            entity: 原始实体名称
        
        Returns:
            标准化后的实体名称
        """
        if not entity:
            return entity
        
        # 直接查找标准形式
        entity_lower = entity.lower().strip()
        
        if entity_lower in self.entity_to_standard:
            standard = self.entity_to_standard[entity_lower]
            if standard != entity:
                logger.debug(f"标准化: {entity} -> {standard}")
            return standard
        
        # 模糊匹配: 直接查表失败时才走相似度匹配,成本更高但能兜住大小写/拼写差异
        for standard, variants in self.standard_entities.items():
            all_forms = [standard] + variants
            for form in all_forms:
                if self._is_similar(entity_lower, form.lower(), threshold=0.9):
                    logger.debug(f"模糊匹配: {entity} -> {standard}")
                    return standard
        
        return entity
    
    def _is_similar(self, a: str, b: str, threshold: float = 0.9) -> bool:
        """判断两个字符串是否相似
        
        Args:
            a: 字符串A
            b: 字符串B
            threshold: 相似度阈值
        
        Returns:
            是否相似
        """
        return SequenceMatcher(None, a, b).ratio() >= threshold
    
    def resolve_coreference(self, text: str, entities: List[str]) -> Dict[str, str]:
        """共指消解：将代词映射到实际实体
        
        Args:
            text: 文本内容
            entities: 已识别的实体列表
        
        Returns:
            代词到实体的映射
        """
        coreference_map = {}
        
        for pronoun, default_entity in self.pronouns.items():
            if pronoun in text:
                # 查找上下文中最近的候选实体
                candidate = self._find_nearest_entity(text, pronoun, entities)
                
                if candidate:
                    coreference_map[pronoun] = candidate
                    logger.debug(f"共指消解: {pronoun} -> {candidate}")
                else:
                    # 找不到候选实体时使用预设默认映射,至少保证指代落在同一语义类别
                    coreference_map[pronoun] = default_entity
                    logger.debug(f"共指消解（默认）: {pronoun} -> {default_entity}")
        
        return coreference_map
    
    def _find_nearest_entity(
        self, 
        text: str, 
        pronoun: str, 
        entities: List[str]
    ) -> Optional[str]:
        """在文本中查找代词最近的实体
        
        Args:
            text: 文本内容
            pronoun: 代词
            entities: 候选实体列表
        
        Returns:
            最近的实体，如果没有找到则返回 None
        """
        pronoun_pos = text.find(pronoun)
        if pronoun_pos == -1:
            return None
        
        # 查找代词前的实体（往前查找200字符）
        context_before = text[max(0, pronoun_pos - 200):pronoun_pos]
        
        nearest_entity = None
        nearest_distance = float('inf')
        
        for entity in entities:
            pos = context_before.rfind(entity)
            if pos != -1:
                distance = len(context_before) - pos
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_entity = entity
        
        return nearest_entity
    
    def disambiguate_entities(
        self, 
        entities_df: pd.DataFrame,
        context_texts: Dict[str, str] = None
    ) -> pd.DataFrame:
        """实体消歧：处理多义实体
        
        Args:
            entities_df: 实体DataFrame
            context_texts: 实体出现的上下文文本（可选）
        
        Returns:
            消歧后的实体DataFrame
        """
        logger.info("开始实体消歧...")
        
        # 1. 标准化所有实体名称,为后续去重与重新编号打基础
        original_count = len(entities_df)
        entities_df['normalized_name'] = entities_df['name'].apply(self.normalize_entity)
        
        # 2. 统计标准化后的变化
        changed = entities_df[entities_df['name'] != entities_df['normalized_name']]
        logger.info(f"  标准化了 {len(changed)} 个实体名称")
        
        # 3. 用标准化名称替换原名称
        entities_df['name'] = entities_df['normalized_name']
        entities_df = entities_df.drop(columns=['normalized_name'])
        
        # 4. 去重（标准化后可能产生重复）
        entities_df = entities_df.drop_duplicates(subset=['name', 'type'], keep='first')
        
        # 5. 重新分配ID
        entities_df = entities_df.reset_index(drop=True)
        entities_df['id'] = range(1, len(entities_df) + 1)
        
        final_count = len(entities_df)
        logger.info(f"消歧完成: {original_count} -> {final_count} 个实体")
        
        return entities_df
    
    def link_entities_with_kb(
        self, 
        entities_df: pd.DataFrame,
        kb_file: str = './config/entity_kb.json'
    ) -> pd.DataFrame:
        """链接实体到外部知识库
        
        Args:
            entities_df: 实体DataFrame
            kb_file: 知识库文件路径
        
        Returns:
            添加了知识库链接的实体DataFrame
        """
        import json
        
        if not os.path.exists(kb_file):
            logger.warning(f"知识库文件不存在: {kb_file}")
            entities_df['kb_id'] = None
            return entities_df
        
        try:
            with open(kb_file, 'r', encoding='utf-8') as f:
                kb = json.load(f)
            
            logger.info(f"已加载知识库: {kb_file}, {len(kb)} 个条目")
            
            # 为每个实体查找知识库ID
            kb_ids = []
            for _, row in entities_df.iterrows():
                kb_id = kb.get(row['name'], {}).get('id')
                kb_ids.append(kb_id)
            
            entities_df['kb_id'] = kb_ids
            
            linked_count = sum(1 for kid in kb_ids if kid is not None)
            logger.info(f"  链接成功: {linked_count}/{len(entities_df)} 个实体")
            
            return entities_df
        
        except Exception as e:
            logger.error(f"链接知识库失败: {e}")
            entities_df['kb_id'] = None
            return entities_df
    
    def merge_duplicate_entities(
        self,
        entities_df: pd.DataFrame,
        relations_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """合并重复实体并更新关系
        
        Args:
            entities_df: 实体DataFrame
            relations_df: 关系DataFrame
        
        Returns:
            (更新后的实体DataFrame, 更新后的关系DataFrame)
        """
        logger.info("开始合并重复实体...")
        
        # 1. 构建实体映射（旧名称 -> 新名称）
        entity_map = {}
        
        for _, row in entities_df.iterrows():
            original_name = row['name']
            normalized_name = self.normalize_entity(original_name)
            
            if original_name != normalized_name:
                entity_map[original_name] = normalized_name
        
        logger.info(f"  构建了 {len(entity_map)} 个实体映射")
        
        # 2. 更新关系中的实体名称
        if entity_map:
            relations_df['head'] = relations_df['head'].apply(
                lambda x: entity_map.get(x, x)
            )
            relations_df['tail'] = relations_df['tail'].apply(
                lambda x: entity_map.get(x, x)
            )
            logger.info("  已更新关系中的实体引用")
        
        # 3. 去除可能产生的重复关系
        original_rel_count = len(relations_df)
        relations_df = relations_df.drop_duplicates(subset=['head', 'relation', 'tail'])
        removed_rel_count = original_rel_count - len(relations_df)
        
        if removed_rel_count > 0:
            logger.info(f"  移除了 {removed_rel_count} 个重复关系")
        
        # 4. 标准化实体名称
        entities_df = self.disambiguate_entities(entities_df)
        
        return entities_df, relations_df
    
    def extract_entity_context(
        self,
        text: str,
        entity: str,
        window_size: int = 100
    ) -> List[str]:
        """提取实体的上下文
        
        Args:
            text: 文本内容
            entity: 实体名称
            window_size: 上下文窗口大小（字符数）
        
        Returns:
            包含该实体的上下文片段列表
        """
        contexts = []
        
        # 查找所有出现位置
        pattern = re.escape(entity)
        for match in re.finditer(pattern, text):
            start = max(0, match.start() - window_size)
            end = min(len(text), match.end() + window_size)
            context = text[start:end]
            contexts.append(context)
        
        return contexts
    
    def compute_entity_importance(
        self,
        entities_df: pd.DataFrame,
        relations_df: pd.DataFrame
    ) -> pd.DataFrame:
        """计算实体重要性得分
        
        Args:
            entities_df: 实体DataFrame
            relations_df: 关系DataFrame
        
        Returns:
            添加了重要性得分的实体DataFrame
        """
        logger.info("计算实体重要性...")
        
        # 计算每个实体的度数（关系数量）
        entity_degree = {}
        
        for _, row in relations_df.iterrows():
            head = row['head']
            tail = row['tail']
            
            entity_degree[head] = entity_degree.get(head, 0) + 1
            entity_degree[tail] = entity_degree.get(tail, 0) + 1
        
        # 添加重要性得分
        importance_scores = []
        for _, row in entities_df.iterrows():
            name = row['name']
            degree = entity_degree.get(name, 0)
            
            # 重要性 = 度数 + 类型权重: 疾病/病原等类型先天给更高基线,即使连接数不多也不会被埋没
            type_weight = {
                'Disease': 10,
                'Pathogen': 8,
                'Host': 7,
                'Vector': 7,
                'Symptom': 5,
                'ControlMeasure': 5,
                'Region': 3,
                'EnvironmentalFactor': 4
            }
            
            base_weight = type_weight.get(row['type'], 1)
            importance = degree + base_weight
            importance_scores.append(importance)
        
        entities_df['importance'] = importance_scores
        entities_df['degree'] = entities_df['name'].map(lambda x: entity_degree.get(x, 0))
        
        # 排序
        entities_df = entities_df.sort_values('importance', ascending=False)
        entities_df = entities_df.reset_index(drop=True)
        
        logger.info(f"  计算完成，平均重要性: {entities_df['importance'].mean():.2f}")
        
        return entities_df
    
    def identify_entity_clusters(
        self,
        entities_df: pd.DataFrame,
        similarity_threshold: float = 0.85
    ) -> Dict[str, List[str]]:
        """识别相似实体簇
        
        Args:
            entities_df: 实体DataFrame
            similarity_threshold: 相似度阈值
        
        Returns:
            实体簇字典 {代表实体: [相似实体列表]}
        """
        logger.info("识别实体簇...")
        
        clusters = {}
        processed = set()
        
        # 按类型分组处理: 只在同类型内做字符串相似度聚类,避免跨类型实体被误合并
        for entity_type in entities_df['type'].unique():
            type_entities = entities_df[entities_df['type'] == entity_type]['name'].tolist()
            
            for i, entity1 in enumerate(type_entities):
                if entity1 in processed:
                    continue
                
                cluster = [entity1]
                processed.add(entity1)
                
                for entity2 in type_entities[i+1:]:
                    if entity2 in processed:
                        continue
                    
                    # 计算相似度
                    similarity = SequenceMatcher(None, entity1.lower(), entity2.lower()).ratio()
                    
                    if similarity >= similarity_threshold:
                        cluster.append(entity2)
                        processed.add(entity2)
                
                if len(cluster) > 1:
                    # 选择最短的作为代表
                    representative = min(cluster, key=len)
                    clusters[representative] = cluster
                    logger.debug(f"  簇: {representative} <- {cluster}")
        
        logger.info(f"  识别到 {len(clusters)} 个实体簇")
        
        return clusters
    
    def resolve_pronouns_in_text(self, text: str) -> str:
        """在文本中解析代词引用
        
        Args:
            text: 原始文本
        
        Returns:
            替换代词后的文本
        """
        resolved_text = text
        
        for pronoun, entity in self.pronouns.items():
            if pronoun in resolved_text:
                # 只替换明确的代词引用
                pattern = r'\b' + re.escape(pronoun) + r'\b'
                resolved_text = re.sub(pattern, entity, resolved_text)
        
        return resolved_text
    
    def link_entities(
        self,
        entities_df: pd.DataFrame,
        relations_df: pd.DataFrame,
        enable_normalization: bool = True,
        enable_clustering: bool = True,
        enable_importance: bool = True
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """完整的实体链接流程
        
        Args:
            entities_df: 实体DataFrame
            relations_df: 关系DataFrame
            enable_normalization: 是否启用标准化
            enable_clustering: 是否启用聚类
            enable_importance: 是否计算重要性
        
        Returns:
            (链接后的实体DataFrame, 更新后的关系DataFrame)
        """
        logger.info("="*60)
        logger.info("开始实体链接处理")
        logger.info("="*60)
        
        original_entity_count = len(entities_df)
        original_relation_count = len(relations_df)
        
        # 1. 标准化和消歧: 可通过 enable_normalization 控制,调试阶段可以临时关闭
        if enable_normalization:
            entities_df, relations_df = self.merge_duplicate_entities(
                entities_df, relations_df
            )
        
        # 2. 识别实体簇
        if enable_clustering:
            clusters = self.identify_entity_clusters(entities_df)
            logger.info(f"  识别到 {len(clusters)} 个实体簇")
        
        # 3. 计算重要性
        if enable_importance:
            entities_df = self.compute_entity_importance(entities_df, relations_df)
        
        final_entity_count = len(entities_df)
        final_relation_count = len(relations_df)
        
        logger.info("实体链接完成:")
        logger.info(f"  实体: {original_entity_count} -> {final_entity_count}")
        logger.info(f"  关系: {original_relation_count} -> {final_relation_count}")
        
        return entities_df, relations_df


if __name__ == "__main__":
    # 测试实体链接器
    linker = EntityLinker()
    
    # 测试标准化
    test_entities = [
        'PWD', 'pine wilt', '松材线虫病',
        'Bursaphelenchus xylophilus', 'B. xylophilus',
        '马尾松', 'Pinus massoniana'
    ]
    
    print("实体标准化测试:")
    for entity in test_entities:
        normalized = linker.normalize_entity(entity)
        print(f"  {entity} -> {normalized}")
    
    # 测试共指消解
    text = "松材线虫病是一种严重的病害。该病由松材线虫引起。"
    print(f"\n原文: {text}")
    
    entities = ['松材线虫病', '松材线虫']
    coref_map = linker.resolve_coreference(text, entities)
    print(f"共指消解: {coref_map}")
    
    # 测试实体簇识别
    test_df = pd.DataFrame({
        'id': range(1, 7),
        'name': ['松材线虫病', 'PWD', 'pine wilt', '松材线虫', 'B. xylophilus', '马尾松'],
        'type': ['Disease', 'Disease', 'Disease', 'Pathogen', 'Pathogen', 'Host'],
        'source_pdf': ['test.pdf'] * 6
    })
    
    clusters = linker.identify_entity_clusters(test_df)
    print(f"\n实体簇: {clusters}")

