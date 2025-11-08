"""
实体识别模块
使用多策略识别实体：关键词提取 + spaCy NER + 领域规则
"""

import re
import jieba
import pandas as pd
import yake
import json
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import Dict, List, Tuple, Set
import spacy
from tqdm import tqdm
from logger_config import get_logger

# KeyBERT 作为可选依赖
try:
    from keybert import KeyBERT
    KEYBERT_AVAILABLE = True
except ImportError:
    KEYBERT_AVAILABLE = False
    print("警告: KeyBERT 未安装或导入失败，将跳过 KeyBERT 关键词提取")


class EntityRecognizer:
    """实体识别器"""
    
    def __init__(self, domain_dict_file: str = './config/domain_dict.json',
                 stopwords_file: str = './config/stopwords.txt'):
        self.logger = get_logger('EntityRecognizer')
        
        # 实体类型定义
        self.entity_types = [
            'Disease', 'Pathogen', 'Host', 'Vector', 
            'Symptom', 'ControlMeasure', 'Region', 'EnvironmentalFactor'
        ]
        
        # 领域知识库（种子词）
        self.domain_knowledge = {
            'Disease': [
                '松材线虫病', 'PWD', 'Pine Wilt Disease', '松树萎蔫病',
                '松树枯萎病', '松树死亡', '松枯萎病', 'pine wilt',
                'pine wilt disease', '松树疫病', '松树萎黄病'
            ],
            'Pathogen': [
                '松材线虫', 'Bursaphelenchus xylophilus', '伴生细菌',
                '病原线虫', '松树线虫', '松褐天牛', 'B. xylophilus',
                'pine wood nematode', '线虫病原'
            ],
            'Host': [
                '马尾松', 'Pinus massoniana', '黑松', 'Pinus thunbergii',
                '赤松', '油松', '湿地松', '华山松', '云南松', '思茅松',
                '松树', 'Pine', 'Pinus', '日本黑松', '湿地松林'
            ],
            'Vector': [
                '松褐天牛', 'Monochamus alternatus', '天牛', 'Beetle',
                '云斑天牛', '松天牛', '媒介昆虫', '传播媒介',
                '松墨天牛', 'Monochamus', '天牛幼虫'
            ],
            'Symptom': [
                '针叶变色', '萎蔫', '枯死', '树脂分泌停止', '针叶褐变',
                '针叶黄化', '枝条枯萎', '整株枯死', '树干失水',
                '材色变化', '蓝变'
            ],
            'ControlMeasure': [
                '清理病死树', '化学防治', '生物防治', '疫木除治',
                '喷洒农药', '诱捕器', '隔离带', '检疫', '监测',
                '除害处理', '焚烧', '粉碎', '熏蒸', '注干',
                '天敌释放', '营林措施', '抗性品种'
            ],
            'Region': [
                '浙江', '江苏', '安徽', '山东', '福建', '广东',
                '江西', '湖南', '湖北', '四川', '重庆', '贵州',
                '云南', '台湾', '中国', '日本', '韩国', '泰山',
                '黄山', '南京', '杭州'
            ],
            'EnvironmentalFactor': [
                '温度', '湿度', '降雨', '气候', '海拔', '坡向',
                '土壤', '林分密度', '郁闭度', '森林类型',
                '植被覆盖', '气象因子'
            ]
        }

        self.stopwords: Set[str] = set([
            '研究', '分析', '表明', '结果', '数据', '模型', '方法', '指标',
            '影响', '发生', '主要', '以及', '之间', '不同', '进行', '具有',
            '以及其', 'the', 'and', 'of', 'in', 'for', 'with', 'on', 'by',
            'from', 'to', 'between', 'analysis', 'results', 'study', 'data',
            'model', 'method', 'effect'
        ])
        
        # 加载外部领域词典
        self._load_domain_dict(domain_dict_file)
        
        # 加载外部停用词
        self._load_stopwords(stopwords_file)
        
        # 初始化工具
        try:
            self.zh_nlp = spacy.load('zh_core_web_sm')
        except Exception:
            print("警告: 未安装中文spaCy模型，NER功能受限")
            self.zh_nlp = None
        
        try:
            self.en_nlp = spacy.load('en_core_web_sm')
        except Exception:
            print("警告: 未安装英文spaCy模型，NER功能受限")
            self.en_nlp = None
        
        # 初始化 KeyBERT（如果可用）
        if KEYBERT_AVAILABLE:
            try:
                self.kw_model = KeyBERT()
            except Exception as e:
                print(f"警告: KeyBERT 初始化失败: {e}")
                self.kw_model = None
        else:
            self.kw_model = None
    
    def _load_domain_dict(self, dict_file: str):
        """加载外部领域词典"""
        if not os.path.exists(dict_file):
            self.logger.warning(f"领域词典文件不存在: {dict_file}，使用内置词典")
            return
        
        try:
            with open(dict_file, 'r', encoding='utf-8') as f:
                external_dict = json.load(f)
            
            # 合并外部词典
            for entity_type, keywords in external_dict.items():
                if entity_type in self.domain_knowledge:
                    # 合并并去重
                    combined = list(set(self.domain_knowledge[entity_type] + keywords))
                    self.domain_knowledge[entity_type] = combined
                else:
                    self.domain_knowledge[entity_type] = keywords
            
            self.logger.info(f"已加载外部领域词典: {dict_file}")
            for entity_type in external_dict.keys():
                count = len(self.domain_knowledge[entity_type])
                self.logger.info(f"  - {entity_type}: {count} 个种子词")
        
        except Exception as e:
            self.logger.error(f"加载领域词典失败: {dict_file}, 错误: {e}")
    
    def _load_stopwords(self, stopwords_file: str):
        """加载外部停用词列表"""
        if not os.path.exists(stopwords_file):
            self.logger.warning(f"停用词文件不存在: {stopwords_file}，使用内置停用词")
            return
        
        try:
            with open(stopwords_file, 'r', encoding='utf-8') as f:
                external_stopwords = set(line.strip() for line in f if line.strip())
            
            # 合并停用词
            original_count = len(self.stopwords)
            self.stopwords.update(external_stopwords)
            added_count = len(self.stopwords) - original_count
            
            self.logger.info(f"已加载外部停用词: {stopwords_file}")
            self.logger.info(f"  新增 {added_count} 个停用词，总计 {len(self.stopwords)} 个")
        
        except Exception as e:
            self.logger.error(f"加载停用词失败: {stopwords_file}, 错误: {e}")
        
    def is_valid_candidate(self, term: str) -> bool:
        """筛选有效候选词"""
        if not term:
            return False
        term = term.strip()
        if term.lower() in self.stopwords:
            return False
        if len(term) < 2 or len(term) > 30:
            return False
        if term.count(' ') > 2:
            return False
        punct_count = len(re.findall(r'[，。！？,.；;:]', term))
        if punct_count > 1:
            return False
        digits = sum(c.isdigit() for c in term)
        if digits and digits / len(term) > 0.3:
            return False
        if any(word in term for word in ['研究', '分析', '结果', '数据', '模型']):
            return False
        return True

    def extract_keywords_tfidf(self, texts: Dict[str, str], top_n: int = 50) -> List[str]:
        """使用TF-IDF提取关键词"""
        # 中文分词
        segmented_texts = []
        for text in texts.values():
            words = jieba.cut(text)
            segmented_texts.append(' '.join(words))
        
        # TF-IDF
        vectorizer = TfidfVectorizer(max_features=top_n)
        vectorizer.fit(segmented_texts)
        
        candidates = vectorizer.get_feature_names_out().tolist()
        return [word for word in candidates if self.is_valid_candidate(word)]
    
    def extract_keywords_yake(self, text: str, top_n: int = 20) -> List[str]:
        """使用YAKE提取关键词"""
        kw_extractor = yake.KeywordExtractor(
            lan="zh", n=3, dedupLim=0.9, top=top_n
        )
        keywords = kw_extractor.extract_keywords(text)
        filtered = []
        for kw, _ in keywords:
            if self.is_valid_candidate(kw):
                filtered.append(kw)
        return filtered
    
    def extract_keywords_keybert(self, text: str, top_n: int = 20) -> List[str]:
        """使用KeyBERT提取关键词"""
        if not self.kw_model:
            return []
        
        try:
            keywords = self.kw_model.extract_keywords(
                text, keyphrase_ngram_range=(1, 3), 
                stop_words=None, top_n=top_n
            )
            results = []
            for kw, _ in keywords:
                if self.is_valid_candidate(kw):
                    results.append(kw)
            return results
        except Exception as e:
            print(f"KeyBERT提取失败: {e}")
            return []
    
    def match_entity_type(self, term: str) -> str:
        """根据领域知识匹配实体类型"""
        term_lower = term.lower()
        
        for entity_type, keywords in self.domain_knowledge.items():
            for keyword in keywords:
                if keyword.lower() in term_lower or term_lower in keyword.lower():
                    return entity_type
        
        # 使用规则判断
        if any(x in term for x in ['病', 'disease', '枯', '萎']):
            return 'Disease'
        elif any(x in term for x in ['线虫', '细菌', '病原', 'pathogen']):
            return 'Pathogen'
        elif any(x in term for x in ['松', 'pine', 'pinus', '树']):
            return 'Host'
        elif any(x in term for x in ['天牛', 'beetle', '昆虫', '媒介']):
            return 'Vector'
        elif any(x in term for x in ['变色', '黄化', '褐变', '枯死', '萎蔫']):
            return 'Symptom'
        elif any(x in term for x in ['防治', '除治', '监测', '检疫', '清理', '防控']):
            return 'ControlMeasure'
        elif any(x in term for x in ['省', '市', '县', '区', '山', '中国', '日本']):
            return 'Region'
        elif any(x in term for x in ['温度', '湿度', '气候', '降雨', '海拔', '土壤']):
            return 'EnvironmentalFactor'
        
        return 'Unknown'
    
    def extract_entities_from_text(self, text: str, source_pdf: str) -> List[Tuple[str, str, str]]:
        """从文本中提取实体"""
        entities = []
        
        # 1. 提取关键词
        yake_keywords = self.extract_keywords_yake(text, top_n=30)
        keybert_keywords = self.extract_keywords_keybert(text, top_n=30)
        
        all_keywords = set(yake_keywords + keybert_keywords)
        
        # 2. 添加领域知识库中的实体
        for entity_type, keywords in self.domain_knowledge.items():
            for keyword in keywords:
                if keyword in text:
                    entities.append((keyword, entity_type, source_pdf))
        
        # 3. 对提取的关键词进行类型匹配
        for keyword in all_keywords:
            entity_type = self.match_entity_type(keyword)
            if entity_type != 'Unknown':
                entities.append((keyword, entity_type, source_pdf))
        
        # 4. 使用spaCy NER
        if self.zh_nlp:
            doc = self.zh_nlp(text[:1000000])  # 限制长度
            for ent in doc.ents:
                entity_type = self.match_entity_type(ent.text)
                if entity_type != 'Unknown':
                    entities.append((ent.text, entity_type, source_pdf))
        
        return entities
    
    def extract_all_entities(self, pdf_texts: Dict[str, str]) -> pd.DataFrame:
        """从所有PDF中提取实体"""
        all_entities = []
        
        for pdf_name, text in tqdm(pdf_texts.items(), desc="提取实体"):
            entities = self.extract_entities_from_text(text, pdf_name)
            all_entities.extend(entities)
            print(f"✓ {pdf_name}: 提取了 {len(entities)} 个实体")
        
        # 转换为DataFrame
        df = pd.DataFrame(all_entities, columns=['name', 'type', 'source_pdf'])
        
        # 添加ID
        df['id'] = range(1, len(df) + 1)
        df = df[['id', 'name', 'type', 'source_pdf']]
        
        print(f"\n总共提取了 {len(df)} 个实体")
        print("\n实体类型分布:")
        print(df['type'].value_counts())
        
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
    
    # 提取实体
    recognizer = EntityRecognizer()
    entities_df = recognizer.extract_all_entities(pdf_texts)
    
    # 保存结果
    os.makedirs("./output", exist_ok=True)
    entities_df.to_csv("./output/entities.csv", index=False, encoding='utf-8-sig')
    print("\n实体数据已保存到: ./output/entities.csv")

