"""
并行处理模块
支持多进程并行处理PDF文件，提升处理速度
"""

import os
from multiprocessing import Pool, cpu_count
from typing import Dict, List, Callable, Any
from functools import partial
from tqdm import tqdm
from scripts.utils.logger_config import get_logger

logger = get_logger('ParallelProcessor')


class ParallelProcessor:
    """并行处理器"""
    
    def __init__(self, max_workers: int = None):
        """初始化并行处理器
        
        Args:
            max_workers: 最大工作进程数，None 则自动设置为 CPU 核心数
        """
        if max_workers is None:
            max_workers = min(cpu_count(), 4)  # 限制最大为4，避免资源占用过多
        
        self.max_workers = max_workers
        logger.info(f"并行处理器已初始化: {self.max_workers} 个工作进程")
    
    def process_pdfs_parallel(
        self, 
        pdf_files: List[str], 
        process_func: Callable[[str], Any],
        desc: str = "处理PDF"
    ) -> List[Any]:
        """并行处理PDF文件
        
        Args:
            pdf_files: PDF文件路径列表
            process_func: 处理单个PDF的函数
            desc: 进度条描述
        
        Returns:
            处理结果列表
        """
        if not pdf_files:
            logger.warning("没有文件需要处理")
            return []
        
        logger.info(f"开始并行处理 {len(pdf_files)} 个文件，使用 {self.max_workers} 个进程")
        
        # 如果文件数量少，使用串行处理
        if len(pdf_files) < 3:
            logger.info("文件数量较少，使用串行处理")
            results = []
            for pdf_file in tqdm(pdf_files, desc=desc):
                try:
                    result = process_func(pdf_file)
                    results.append(result)
                except Exception as e:
                    logger.error(f"处理文件失败: {pdf_file}, 错误: {e}")
                    results.append(None)
            return results
        
        # 并行处理
        try:
            with Pool(processes=self.max_workers) as pool:
                results = list(tqdm(
                    pool.imap(process_func, pdf_files),
                    total=len(pdf_files),
                    desc=desc
                ))
            
            success_count = sum(1 for r in results if r is not None)
            logger.info(f"并行处理完成: 成功 {success_count}/{len(pdf_files)}")
            
            return results
        
        except Exception as e:
            logger.error(f"并行处理失败: {e}，回退到串行处理")
            # 回退到串行处理
            results = []
            for pdf_file in tqdm(pdf_files, desc=desc):
                try:
                    result = process_func(pdf_file)
                    results.append(result)
                except Exception as e:
                    logger.error(f"处理文件失败: {pdf_file}, 错误: {e}")
                    results.append(None)
            return results
    
    def batch_process(
        self,
        items: List[Any],
        process_func: Callable[[Any], Any],
        batch_size: int = 100,
        desc: str = "批处理"
    ) -> List[Any]:
        """批量并行处理
        
        Args:
            items: 待处理项目列表
            process_func: 处理函数
            batch_size: 批次大小
            desc: 进度条描述
        
        Returns:
            处理结果列表
        """
        if not items:
            return []
        
        logger.info(f"批量处理 {len(items)} 个项目，批次大小: {batch_size}")
        
        results = []
        
        # 分批处理
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(items) + batch_size - 1) // batch_size
            
            logger.info(f"处理批次 {batch_num}/{total_batches}")
            
            # 并行处理当前批次
            try:
                with Pool(processes=self.max_workers) as pool:
                    batch_results = list(tqdm(
                        pool.imap(process_func, batch),
                        total=len(batch),
                        desc=f"{desc} (批次 {batch_num}/{total_batches})"
                    ))
                results.extend(batch_results)
            except Exception as e:
                logger.error(f"批次 {batch_num} 处理失败: {e}")
                # 回退到串行
                for item in batch:
                    try:
                        result = process_func(item)
                        results.append(result)
                    except Exception as e:
                        logger.error(f"处理项目失败: {e}")
                        results.append(None)
        
        return results


def process_pdf_wrapper(args: tuple) -> tuple:
    """PDF处理包装函数，用于并行处理
    
    Args:
        args: (pdf_path, extractor_class, extractor_kwargs)
    
    Returns:
        (pdf_filename, extracted_text)
    """
    pdf_path, extract_func = args
    
    try:
        text = extract_func(pdf_path)
        filename = os.path.basename(pdf_path)
        return (filename, text)
    except Exception as e:
        logger.error(f"提取失败: {pdf_path}, 错误: {e}")
        return (os.path.basename(pdf_path), "")


if __name__ == "__main__":
    # 测试并行处理器
    processor = ParallelProcessor(max_workers=2)
    
    # 测试函数
    def test_process(item):
        import time
        time.sleep(0.1)
        return item * 2
    
    items = list(range(10))
    results = processor.batch_process(items, test_process, batch_size=5, desc="测试处理")
    
    print(f"处理结果: {results}")

