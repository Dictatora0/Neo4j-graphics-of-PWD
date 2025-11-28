"""
配置加载模块
从 YAML 文件加载系统配置
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from logger_config import get_logger

logger = get_logger('ConfigLoader')


class Config:
    """配置类"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        """初始化配置
        
        Args:
            config_dict: 配置字典
        """
        self._config = config_dict
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键，支持点号分隔的路径，如 'pdf.input_directory'
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """设置配置值
        
        Args:
            key: 配置键，支持点号分隔的路径
            value: 配置值
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            配置字典
        """
        return self._config.copy()
    
    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any):
        """支持字典式设置"""
        self.set(key, value)


def load_config(config_file: str = './config/config.yaml') -> Config:
    """加载配置文件
    
    Args:
        config_file: 配置文件路径
    
    Returns:
        配置对象
    """
    config_path = Path(config_file)
    
    if not config_path.exists():
        logger.warning(f"配置文件不存在: {config_file}，使用默认配置")
        return Config(get_default_config())
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
        
        logger.info(f"配置文件已加载: {config_file}")
        return Config(config_dict)
    
    except Exception as e:
        logger.error(f"加载配置文件失败: {config_file}, 错误: {e}")
        logger.warning("使用默认配置")
        return Config(get_default_config())


def save_config(config: Config, config_file: str = './config/config.yaml'):
    """保存配置到文件
    
    Args:
        config: 配置对象
        config_file: 配置文件路径
    """
    config_path = Path(config_file)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config.to_dict(), f, allow_unicode=True, default_flow_style=False)
        
        logger.info(f"配置已保存: {config_file}")
    
    except Exception as e:
        logger.error(f"保存配置文件失败: {config_file}, 错误: {e}")


def get_default_config() -> Dict[str, Any]:
    """获取默认配置
    
    Returns:
        默认配置字典
    """
    return {
        'pdf': {
            'input_directory': './文献',
            'output_directory': './output/extracted_texts',
            'enable_cache': True,
            'parallel_workers': 4,
            'enable_ocr': False,
            'ocr_engine': 'tesseract',
            'image_extraction': {
                'enable': False,
                'output_directory': './output/pdf_images',
                'max_images_per_pdf': 25,
                'caption_model': 'Qwen/Qwen2-VL-7B-Instruct',
                'caption_provider': 'transformers'
            }
        },
        'entity': {
            'enable_tfidf': True,
            'enable_yake': True,
            'enable_keybert': True,
            'max_keywords_tfidf': 50,
            'min_entity_length': 2,
            'max_entity_length': 30,
        },
        'relation': {
            'enable_pattern_matching': True,
            'enable_cooccurrence': True,
            'window_size': 100,
        },
        'cleaning': {
            'confidence_threshold': 0.65,
            'similarity_threshold': 0.85,
            'min_frequency': 2,
        },
        'output': {
            'base_directory': './output',
        },
        'logging': {
            'level': 'INFO',
            'file': './output/kg_builder.log',
        },
        'system': {
            'enable_cache': True,
            'enable_parallel': True,
        }
    }


# 创建全局配置实例
_global_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例
    
    Returns:
        全局配置对象
    """
    global _global_config
    
    if _global_config is None:
        _global_config = load_config()
    
    return _global_config


if __name__ == "__main__":
    # 测试配置加载
    config = load_config()
    
    print("PDF配置:")
    print(f"  输入目录: {config.get('pdf.input_directory')}")
    print(f"  启用缓存: {config.get('pdf.enable_cache')}")
    
    print("\n实体识别配置:")
    print(f"  启用TF-IDF: {config.get('entity.enable_tfidf')}")
    print(f"  最小实体长度: {config.get('entity.min_entity_length')}")
    
    print("\n清洗配置:")
    print(f"  置信度阈值: {config.get('cleaning.confidence_threshold')}")

