"""
配置文件
集中管理系统参数
"""

# PDF提取配置
PDF_CONFIG = {
    'input_directory': './文献',
    'output_directory': './output/extracted_texts',
    'reference_keywords': [
        '参考文献', 'References', 'REFERENCES', '引用文献',
        'Bibliography', 'Works Cited'
    ]
}

# 实体识别配置
ENTITY_CONFIG = {
    'enable_tfidf': True,
    'enable_yake': True,
    'enable_keybert': True,
    'enable_spacy': True,
    'max_keywords_tfidf': 50,
    'max_keywords_yake': 30,
    'max_keywords_keybert': 30,
}

# 关系抽取配置
RELATION_CONFIG = {
    'enable_pattern_matching': True,
    'enable_cooccurrence': True,
    'cooccurrence_window': 100,  # 共现窗口大小（字符数）
}

# 数据清洗配置
CLEANING_CONFIG = {
    'confidence_threshold': 0.5,  # 置信度阈值
    'similarity_threshold': 0.85,  # 相似度阈值
    'min_entity_length': 2,
    'max_entity_length': 50,
}

# Neo4j配置
NEO4J_CONFIG = {
    'uri': 'bolt://localhost:7687',
    'user': 'neo4j',
    'password': '12345678',  
    'database': 'neo4j',
}
# 输出配置
OUTPUT_CONFIG = {
    'base_directory': './output',
    'entities_file': 'entities.csv',
    'relations_file': 'relations.csv',
    'entities_clean_file': 'entities_clean.csv',
    'relations_clean_file': 'relations_clean.csv',
    'neo4j_directory': 'neo4j_import',
    'statistics_file': 'statistics_report.txt',
}

# 实体类型定义
ENTITY_TYPES = [
    'Disease',           # 疾病
    'Pathogen',          # 病原体
    'Host',              # 宿主
    'Vector',            # 传播媒介
    'Symptom',           # 症状
    'ControlMeasure',    # 防控措施
    'Region',            # 地区
    'EnvironmentalFactor'  # 环境因素
]

# 关系类型定义
RELATION_TYPES = [
    'hasPathogen',      # 有病原体
    'hasHost',          # 有宿主
    'hasVector',        # 有传播媒介
    'hasSymptom',       # 有症状
    'controlledBy',     # 被控制
    'occursIn',         # 发生在
    'affectedBy',       # 受影响
    'transmits',        # 传播
    'infects',          # 感染
]

# 日志配置
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': './output/kg_builder.log',
}

