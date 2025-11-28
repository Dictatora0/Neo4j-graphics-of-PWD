"""
缓存管理模块
提供文件哈希计算和缓存管理功能
"""

import hashlib
import pickle
from pathlib import Path
from typing import Any, Optional
from logger_config import get_logger

logger = get_logger('CacheManager')


import numpy as np

class CacheManager:
    """缓存管理器，支持向量维度校验和失效"""
    def __init__(self, cache_dir: str = "./output/cache", embedding_dim: int = 1024):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_dim = embedding_dim  # BGE-M3 默认 1024 维
        logger.info(f"缓存目录: {self.cache_dir}, 期望向量维度: {self.embedding_dim}")
    
    def get_file_hash(self, file_path: str) -> str:
        """计算文件的 MD5 哈希值
        
        Args:
            file_path: 文件路径
        
        Returns:
            文件的 MD5 哈希值
        """
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            return file_hash
        except Exception as e:
            logger.error(f"计算文件哈希失败: {file_path}, 错误: {e}")
            return ""
    
    def get_cache(self, key: str) -> Optional[Any]:
        """获取缓存数据，并校验向量维度（如为embedding缓存）"""
        cache_file = self.cache_dir / f"{key}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                # 如果是embedding缓存，校验维度
                if isinstance(data, np.ndarray) and data.ndim == 2:
                    if data.shape[1] != self.embedding_dim:
                        logger.warning(f"缓存向量维度不符({data.shape[1]}!={self.embedding_dim})，自动失效: {key}")
                        cache_file.unlink()
                        return None
                logger.debug(f"缓存命中: {key}")
                return data
            except Exception as e:
                logger.warning(f"读取缓存失败: {key}, 错误: {e}")
                return None
        return None
    
    def set_cache(self, key: str, data: Any) -> bool:
        """设置缓存数据，若为embedding则校验维度"""
        cache_file = self.cache_dir / f"{key}.pkl"
        try:
            # 若为embedding，校验维度
            if isinstance(data, np.ndarray) and data.ndim == 2:
                if data.shape[1] != self.embedding_dim:
                    logger.error(f"尝试缓存的向量维度({data.shape[1]})与期望({self.embedding_dim})不符: {key}")
                    return False
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            logger.debug(f"缓存已保存: {key}")
            return True
        except Exception as e:
            logger.error(f"保存缓存失败: {key}, 错误: {e}")
            return False
    
    def is_pdf_cached(self, pdf_path: str) -> bool:
        """检查 PDF 文件是否已缓存
        
        Args:
            pdf_path: PDF 文件路径
        
        Returns:
            是否已缓存
        """
        file_hash = self.get_file_hash(pdf_path)
        if not file_hash:
            return False
        return self.get_cache(f"pdf_{file_hash}") is not None
    
    def get_pdf_cache(self, pdf_path: str) -> Optional[str]:
        """获取 PDF 的缓存文本
        
        Args:
            pdf_path: PDF 文件路径
        
        Returns:
            缓存的文本，如果不存在则返回 None
        """
        file_hash = self.get_file_hash(pdf_path)
        if not file_hash:
            return None
        return self.get_cache(f"pdf_{file_hash}")
    
    def set_pdf_cache(self, pdf_path: str, text: str) -> bool:
        """设置 PDF 的缓存文本
        
        Args:
            pdf_path: PDF 文件路径
            text: 提取的文本
        
        Returns:
            是否成功设置缓存
        """
        file_hash = self.get_file_hash(pdf_path)
        if not file_hash:
            return False
        return self.set_cache(f"pdf_{file_hash}", text)
    
    def clear_cache(self) -> int:
        """清空所有缓存"""
        count = 0
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                cache_file.unlink()
                count += 1
            except Exception as e:
                logger.warning(f"删除缓存文件失败: {cache_file}, 错误: {e}")
        logger.info(f"已清空 {count} 个缓存文件")
        return count

    def clear_embedding_cache(self):
        """仅清除embedding维度不符的缓存"""
        removed = 0
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                if isinstance(data, np.ndarray) and data.ndim == 2:
                    if data.shape[1] != self.embedding_dim:
                        cache_file.unlink()
                        removed += 1
            except Exception:
                continue
        logger.info(f"已清除 {removed} 个embedding维度不符的缓存")
        return removed
    
    def get_cache_size(self) -> int:
        """获取缓存目录大小（字节）
        
        Returns:
            缓存目录总大小
        """
        total_size = 0
        for cache_file in self.cache_dir.glob("*.pkl"):
            total_size += cache_file.stat().st_size
        return total_size
    
    def get_cache_info(self) -> dict:
        """获取缓存信息
        
        Returns:
            包含缓存统计信息的字典
        """
        cache_files = list(self.cache_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'cache_dir': str(self.cache_dir),
            'file_count': len(cache_files),
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024)
        }


if __name__ == "__main__":
    # 测试缓存管理器
    cache = CacheManager()
    
    # 测试基本缓存操作
    cache.set_cache("test_key", {"data": "test_value"})
    result = cache.get_cache("test_key")
    print(f"缓存测试: {result}")
    
    # 显示缓存信息
    info = cache.get_cache_info()
    print(f"缓存信息: {info}")

