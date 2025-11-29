#!/usr/bin/env python3
"""
Enhanced Pipeline with Checkpoint Support
带断点续传和增量保存的安全版本

新功能：
1. 每 N 个文本块自动保存 checkpoint
2. 支持断点续传（程序重启后继续）
3. 异常捕获自动保存
4. 最多损失 N 个块的进度（约 3-5 分钟）
"""

import os
import logging
from typing import Dict, List, Tuple
import pandas as pd
from datetime import datetime
from tqdm import tqdm

from pdf_extractor import PDFExtractor
from concept_extractor import ConceptExtractor, ContextualProximityAnalyzer
from concept_deduplicator import (
    ConceptDeduplicator,
    RelationshipDeduplicator,
    ConceptImportanceFilter,
    SentenceTransformerEmbedding,
    BGE_M3_Embedder
)
from config_loader import load_config
from logger_config import get_logger
from checkpoint_manager import CheckpointManager

logger = get_logger('SafePipeline')


class EnhancedKnowledgeGraphPipelineSafe:
    """
    安全版知识图谱构建管道
    
    新增特性：
    - 增量保存：每 N 个块保存一次
    - 断点续传：自动跳过已处理的块
    - 异常保护：Ctrl+C 或崩溃时自动保存
    """
    
    def __init__(self, config: Dict = None, checkpoint_interval: int = 10):
        """
        初始化安全管道
        
        Args:
            config: 配置字典
            checkpoint_interval: 每处理多少个块保存一次（默认 10）
        """
        if config is None:
            config = load_config()
        
        self.config = config
        self.output_dir = config.get('output.base_directory', './output')
        self.ollama_model = config.get('llm.model', 'mistral')
        self.ollama_host = config.get('llm.ollama_host', 'http://localhost:11434')
        self.similarity_threshold = config.get('deduplication.similarity_threshold', 0.85)
        self.min_concept_importance = config.get('filtering.min_importance', 2)
        self.min_connections = config.get('filtering.min_connections', 1)
        self.max_chunks = config.get('llm.max_chunks', 100)
        
        # Checkpoint 设置
        self.checkpoint_interval = checkpoint_interval
        self.checkpoint_manager = CheckpointManager()
        
        # 初始化组件
        self.concept_extractor = None
        self.deduplicator = None
        self.proximity_analyzer = ContextualProximityAnalyzer()
        
        self._initialize_components()
        
        logger.info(f"Safe pipeline initialized with checkpoint interval: {checkpoint_interval}")
    
    def _initialize_components(self):
        """初始化 LLM 和嵌入组件"""
        try:
            logger.info("Initializing concept extractor...")
            self.concept_extractor = ConceptExtractor(
                model=self.ollama_model,
                ollama_host=self.ollama_host
            )
            logger.info("Concept extractor initialized")
        except Exception as e:
            logger.error(f"Failed to initialize concept extractor: {e}")
            logger.error("Make sure Ollama is running: ollama serve")
            raise
        
        try:
            logger.info("Initializing concept deduplicator...")
            use_bge_m3 = self.config.get('deduplication.use_bge_m3', True)
            
            if use_bge_m3:
                logger.info("Using BGE-M3 for hybrid dense+sparse retrieval")
                embedding_model = self.config.get('deduplication.embedding_model', 'BAAI/bge-m3')
                embedding_provider = BGE_M3_Embedder(model_name=embedding_model)
            else:
                logger.info("Using default SentenceTransformer embedding")
                embedding_provider = SentenceTransformerEmbedding()
            
            self.deduplicator = ConceptDeduplicator(
                embedding_provider=embedding_provider,
                similarity_threshold=self.similarity_threshold
            )
            logger.info("Concept deduplicator initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize embeddings: {e}")
            logger.warning("Deduplication will be skipped")
            self.deduplicator = None
    
    def run(self, pdf_dir: str, resume: bool = True, clear_checkpoint: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        运行安全管道（支持断点续传）
        
        Args:
            pdf_dir: PDF 文件目录
            resume: 是否从上次中断处继续（默认 True）
            clear_checkpoint: 是否清除旧的 checkpoint（开始新任务时设为 True）
        
        Returns:
            (concepts_df, relationships_df)
        """
        logger.info("="*60)
        logger.info("Starting Safe Enhanced Pipeline with Checkpoint Support")
        logger.info("="*60)
        
        # 清除旧 checkpoint（如果需要）
        if clear_checkpoint:
            logger.info("Clearing old checkpoints...")
            self.checkpoint_manager.clear()
        
        # 检查是否有未完成的任务
        if resume:
            summary = self.checkpoint_manager.get_summary()
            if summary['processed_chunks'] > 0:
                logger.info("="*60)
                logger.info("RESUMING from previous checkpoint:")
                logger.info(f"  - Processed chunks: {summary['processed_chunks']}")
                logger.info(f"  - Total concepts: {summary['total_concepts']}")
                logger.info(f"  - Total relationships: {summary['total_relationships']}")
                logger.info("="*60)
        
        start_time = datetime.now()
        
        try:
            # Step 1: 提取 PDF 文本
            logger.info("\n[Step 1/6] Extracting text from PDFs...")
            pdf_texts = self._extract_pdf_texts(pdf_dir)
            
            if not pdf_texts:
                logger.error("No PDF texts extracted")
                return pd.DataFrame(), pd.DataFrame()
            
            # Step 2: 分块
            logger.info("\n[Step 2/6] Splitting texts into chunks...")
            chunks = self._create_chunks(pdf_texts)
            logger.info(f"Created {len(chunks)} chunks")
            
            # 过滤已处理的块（断点续传）
            if resume:
                processed_chunks = self.checkpoint_manager.get_processed_chunks()
                original_count = len(chunks)
                chunks = [c for c in chunks if c['chunk_id'] not in processed_chunks]
                skipped = original_count - len(chunks)
                
                if skipped > 0:
                    logger.info(f"Skipping {skipped} already processed chunks")
                    logger.info(f"Remaining chunks to process: {len(chunks)}")
            
            # Step 3: LLM 抽取（带增量保存）
            logger.info("\n[Step 3/6] Extracting concepts with checkpoint support...")
            concepts_df, llm_relationships_df = self._extract_with_checkpoints(chunks)
            
            # Step 4: 近邻关系
            logger.info("\n[Step 4/6] Analyzing contextual proximity...")
            proximity_relationships_df = self._extract_proximity_relationships(chunks, concepts_df)
            logger.info(f"Extracted {len(proximity_relationships_df)} proximity relationships")
            
            # Step 5: 去重
            logger.info("\n[Step 5/6] Merging and deduplicating concepts...")
            concepts_df, relationships_df = self._merge_and_deduplicate(
                concepts_df, llm_relationships_df, proximity_relationships_df
            )
            
            # Step 6: 过滤
            logger.info("\n[Step 6/6] Filtering and finalizing...")
            concepts_df, relationships_df = self._filter_and_finalize(concepts_df, relationships_df)
            
            # 最终保存
            self._save_results(concepts_df, relationships_df)
            
            # 清除 checkpoint（任务完成）
            logger.info("\nCleaning up checkpoints...")
            # self.checkpoint_manager.clear()  # 保留 checkpoint 以备查看
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info("\n" + "="*60)
            logger.info("Safe Pipeline completed successfully")
            logger.info("="*60)
            logger.info(f"Duration: {duration}")
            logger.info(f"Final concepts: {len(concepts_df)}")
            logger.info(f"Final relationships: {len(relationships_df)}")
            
            return concepts_df, relationships_df
        
        except KeyboardInterrupt:
            logger.warning("\n" + "="*60)
            logger.warning("⚠️  User interrupted (Ctrl+C)")
            logger.warning("="*60)
            logger.info("Checkpoint已自动保存，下次运行将从中断处继续")
            logger.info(f"进度保存位置: {self.checkpoint_manager.checkpoint_dir}")
            raise
        
        except Exception as e:
            logger.error("\n" + "="*60)
            logger.error(f"❌ Error occurred: {e}")
            logger.error("="*60)
            logger.info("Checkpoint已自动保存，可尝试重新运行恢复")
            logger.info(f"进度保存位置: {self.checkpoint_manager.checkpoint_dir}")
            raise
    
    def _extract_with_checkpoints(self, chunks: List[Dict]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        带 checkpoint 的 LLM 抽取
        
        核心改进：
        - 每 N 个块保存一次
        - 实时更新进度文件
        - 异常时已处理数据不丢失
        """
        all_concepts = []
        all_relationships = []
        
        logger.info(f"Processing {len(chunks)} chunks with checkpoint interval: {self.checkpoint_interval}")
        
        for i, chunk in enumerate(tqdm(chunks, desc="Extracting concepts")):
            text = chunk.get('text', '')
            chunk_id = chunk.get('chunk_id', '')
            
            if not text or len(text.strip()) < 20:
                continue
            
            # LLM 抽取
            try:
                concepts, relationships = self.concept_extractor.extract_concepts_and_relationships(
                    text, chunk_id
                )
                
                if concepts:
                    all_concepts.extend(concepts)
                if relationships:
                    all_relationships.extend(relationships)
                
                # 保存到 checkpoint
                self.checkpoint_manager.save_chunk_results(chunk_id, concepts, relationships)
                
                # 定期保存完整 checkpoint
                if (i + 1) % self.checkpoint_interval == 0:
                    temp_concepts_df = pd.DataFrame(all_concepts) if all_concepts else pd.DataFrame()
                    temp_relationships_df = pd.DataFrame(all_relationships) if all_relationships else pd.DataFrame()
                    
                    self.checkpoint_manager.save_checkpoint(
                        i + 1, temp_concepts_df, temp_relationships_df
                    )
                    
                    logger.info(f"✓ Checkpoint: {i+1}/{len(chunks)} chunks processed")
            
            except Exception as e:
                logger.error(f"Failed to process chunk {chunk_id}: {e}")
                continue
        
        # 最终数据
        concepts_df = pd.DataFrame(all_concepts) if all_concepts else pd.DataFrame()
        relationships_df = pd.DataFrame(all_relationships) if all_relationships else pd.DataFrame()
        
        logger.info(f"Extraction complete: {len(concepts_df)} concepts, {len(relationships_df)} relationships")
        
        return concepts_df, relationships_df
    
    def _extract_pdf_texts(self, pdf_dir: str) -> Dict[str, str]:
        """提取 PDF 文本"""
        extractor = PDFExtractor(
            use_cache=self.config.get('system.enable_cache', True),
            enable_parallel=self.config.get('system.enable_parallel', True)
        )
        return extractor.extract_from_directory(pdf_dir)
    
    def _create_chunks(self, pdf_texts: Dict[str, str], chunk_size: int = 3000,
                      overlap: int = 300) -> List[Dict]:
        """分块"""
        chunks = []
        chunk_id_counter = 0
        
        for pdf_name, text in pdf_texts.items():
            for i in range(0, len(text), chunk_size - overlap):
                chunk_text = text[i:i + chunk_size]
                
                if len(chunk_text.strip()) > 50:
                    chunks.append({
                        'text': chunk_text,
                        'chunk_id': f"{pdf_name}_{chunk_id_counter}",
                        'source_pdf': pdf_name,
                        'concepts': []
                    })
                    chunk_id_counter += 1
        
        return chunks
    
    def _extract_proximity_relationships(self, chunks: List[Dict],
                                        concepts_df: pd.DataFrame) -> pd.DataFrame:
        """提取近邻关系"""
        concept_map = {}
        for _, row in concepts_df.iterrows():
            chunk_id = row.get('chunk_id', '')
            if chunk_id not in concept_map:
                concept_map[chunk_id] = []
            concept_map[chunk_id].append(row['entity'])
        
        for chunk in chunks:
            chunk['concepts'] = concept_map.get(chunk['chunk_id'], [])
        
        return self.proximity_analyzer.extract_proximity_relationships(chunks)
    
    def _merge_and_deduplicate(self, concepts_df: pd.DataFrame,
                              llm_relationships_df: pd.DataFrame,
                              proximity_relationships_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """合并和去重"""
        relationships_df = self.proximity_analyzer.merge_relationships(
            llm_relationships_df, proximity_relationships_df
        )
        logger.info(f"Merged relationships: {len(relationships_df)}")
        
        if self.deduplicator and not concepts_df.empty:
            concepts_df, concept_mapping = self.deduplicator.deduplicate_concepts(concepts_df)
            
            if not relationships_df.empty:
                relationships_df = RelationshipDeduplicator.update_relationships(
                    relationships_df, concept_mapping
                )
                logger.info(f"Updated relationships after deduplication: {len(relationships_df)}")
        
        return concepts_df, relationships_df
    
    def _filter_and_finalize(self, concepts_df: pd.DataFrame,
                            relationships_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """过滤"""
        filtered_concepts = ConceptImportanceFilter.filter_concepts(
            concepts_df, relationships_df,
            min_importance=self.min_concept_importance,
            min_connections=self.min_connections
        )
        
        if not filtered_concepts.empty:
            valid_concepts = set(filtered_concepts['entity'].unique())
            filtered_relationships = relationships_df[
                (relationships_df['node_1'].isin(valid_concepts)) &
                (relationships_df['node_2'].isin(valid_concepts))
            ]
        else:
            filtered_relationships = relationships_df
        
        logger.info(f"Final concepts: {len(filtered_concepts)}")
        logger.info(f"Final relationships: {len(filtered_relationships)}")
        
        return filtered_concepts, filtered_relationships
    
    def _save_results(self, concepts_df: pd.DataFrame, relationships_df: pd.DataFrame):
        """保存最终结果"""
        os.makedirs(self.output_dir, exist_ok=True)
        
        concepts_path = f"{self.output_dir}/concepts.csv"
        concepts_df.to_csv(concepts_path, index=False, encoding='utf-8-sig')
        logger.info(f"Saved concepts to {concepts_path}")
        
        relationships_path = f"{self.output_dir}/relationships.csv"
        relationships_df.to_csv(relationships_path, index=False, encoding='utf-8-sig')
        logger.info(f"Saved relationships to {relationships_path}")


def run_safe_pipeline(pdf_dir: str = None, config: Dict = None,
                     checkpoint_interval: int = 10,
                     resume: bool = True,
                     clear_checkpoint: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    运行安全管道（便捷函数）
    
    Args:
        pdf_dir: PDF 目录
        config: 配置字典
        checkpoint_interval: checkpoint 间隔（默认 10 个块）
        resume: 是否断点续传（默认 True）
        clear_checkpoint: 是否清除旧 checkpoint（默认 False）
    
    Returns:
        (concepts_df, relationships_df)
    """
    if config is None:
        config = load_config()
    
    if pdf_dir is None:
        pdf_dir = config.get('pdf.input_directory', './文献')
    
    pipeline = EnhancedKnowledgeGraphPipelineSafe(
        config, checkpoint_interval=checkpoint_interval
    )
    return pipeline.run(pdf_dir, resume=resume, clear_checkpoint=clear_checkpoint)


if __name__ == "__main__":
    import sys
    
    # 支持命令行参数
    clear = '--clear' in sys.argv  # 是否清除旧进度
    no_resume = '--no-resume' in sys.argv  # 是否禁用断点续传
    
    print("\n" + "="*60)
    print("Safe Enhanced Pipeline - 带断点续传的安全版本")
    print("="*60)
    print(f"断点续传: {'禁用' if no_resume else '启用'}")
    print(f"清除旧进度: {'是' if clear else '否'}")
    print("="*60 + "\n")
    
    # 运行
    concepts_df, relationships_df = run_safe_pipeline(
        resume=not no_resume,
        clear_checkpoint=clear
    )
    
    print("\n" + "="*60)
    print("Pipeline Results")
    print("="*60)
    print(f"Concepts: {len(concepts_df)}")
    print(f"Relationships: {len(relationships_df)}")
    
    if not concepts_df.empty:
        print("\nTop 10 Concepts by Importance:")
        print(concepts_df.nlargest(10, 'importance')[['entity', 'importance', 'category']])
    
    if not relationships_df.empty:
        print("\nTop 10 Relationships by Weight:")
        print(relationships_df.nlargest(10, 'weight')[['node_1', 'node_2', 'edge', 'weight']])
