#!/usr/bin/env python3
"""Enhanced Pipeline with Checkpoint Support
带断点续传和增量保存的安全版本

本文件实现了 安全版知识图谱构建主流水线, 在原有增强管道基础上增加:
- 按块增量保存(CheckpointManager) → 单块/单次失败不丢全局结果;
- 断点续传(根据 .progress.json 跳过已处理的 chunk);
- `Ctrl+C`/异常时自动保存当前进度, 下次可以继续跑;
- 最多只损失最近 N 个块的结果(由 `checkpoint_interval` 控制, 典型约 3-5 分钟)。

高层执行流程(与 README 中的“程序运行流程”对应):
1) `run_safe_pipeline` / `__main__` 作为统一入口, 读取配置与命令行参数;
2) `EnhancedKnowledgeGraphPipelineSafe.run` 依次执行 6 个步骤:
   - Step1: `_extract_pdf_texts` → 调用 `PDFExtractor` 完成 PDF 文本提取与清洗;
   - Step2: `_create_chunks` → 按固定窗口+重叠切分文本, 生成带 `chunk_id` 的块列表;
   - Step3: `_extract_with_checkpoints` → 对每个块调用 LLM 抽取 concepts/relationships, 同时增量保存;
   - Step4: `_extract_proximity_relationships` → 基于共现生成 W2 近邻关系;
   - Step5: `_merge_and_deduplicate` → 合并 W1/W2 关系, 对概念做语义去重并更新关系端点;
   - Step6: `_filter_and_finalize` → 按重要性和连接度过滤概念, 得到最终子图;
3) `_save_results` 将最终 `concepts.csv` / `relationships.csv` 落盘, 供 Neo4j 导入和后续分析使用。
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
    """安全版知识图谱构建管道(带 Checkpoint)

    角色可以理解为“整个知识图谱构建流程的总调度中心”, 主要职责:

    - 按配置初始化各个功能组件: `PDFExtractor`、`ConceptExtractor`、`ConceptDeduplicator` 等;
    - 串联从 **PDF → 文本 → chunk → 概念/关系(W1,W2) → 去重/过滤 → CSV** 的完整数据流;
    - 通过 `CheckpointManager` 在 LLM 抽取阶段做**增量保存和进度追踪**, 支持断点续传;
    - 在发生异常或用户 `Ctrl+C` 时, 尽量保证“已经算出来的东西都写到磁盘上”。
    """
    
    def __init__(self, config: Dict = None, checkpoint_interval: int = 5):
        """初始化安全管道

        参数:
            config: 配置字典, 一般来自 `config/config.yaml`, 不传则自动加载;
            checkpoint_interval: 每处理多少个文本块写一次完整 checkpoint 快照(默认 5)。

        说明:
        - 与无 Checkpoint 版本相比, 这里会额外维护 `CheckpointManager`,
          在 LLM 抽取阶段把**每个 chunk 的结果**和**阶段性全量快照**写入 `output/checkpoints/`;
        - `checkpoint_interval` 越小, 容错越强(丢失的进度越少), 但写盘次数略多; 一般 5~10 之间即可。
        """
        if config is None:
            # 默认从 config/config.yaml 加载一整套配置，便于统一管理
            config = load_config()
        
        self.config = config
        # 输出目录，用于存放最终 concepts.csv / relationships.csv
        self.output_dir = config.get('output.base_directory', './output')
        # LLM 相关配置：模型名称和 Ollama 服务地址
        self.ollama_model = config.get('llm.model', 'mistral')
        self.ollama_host = config.get('llm.ollama_host', 'http://localhost:11434')
        # 去重与过滤相关阈值，从配置中拿，方便之后按项目需求微调
        self.similarity_threshold = config.get('deduplication.similarity_threshold', 0.85)
        self.min_concept_importance = config.get('filtering.min_importance', 2)
        self.min_connections = config.get('filtering.min_connections', 1)
        # 最多处理多少个文本块，便于做小规模试跑或限流
        self.max_chunks = config.get('llm.max_chunks', 100)
        # LLM 超时时间统一从配置读取，和概念抽取模块保持一致
        self.llm_timeout = config.get('llm.timeout', 600)
        
        # Checkpoint 设置：每处理多少个块写一次完整快照
        self.checkpoint_interval = checkpoint_interval
        # 进度管理器负责增量 CSV + .progress.json 的读写
        self.checkpoint_manager = CheckpointManager()
        
        # 初始化各个功能组件，抽取 / 去重 / 近邻分析
        self.concept_extractor = None
        self.deduplicator = None
        self.proximity_analyzer = ContextualProximityAnalyzer()
        
        self._initialize_components()
        
        logger.info(f"Safe pipeline initialized with checkpoint interval: {checkpoint_interval}")
    
    def _initialize_components(self):
        """初始化 LLM 抽取器与概念去重组件

        - 概念/关系抽取: 使用 `ConceptExtractor`, 封装了对 Ollama(Qwen2.5-Coder 等) 的调用,
          并内置了 JSON Schema、重试和超时控制;
        - 概念去重: 根据配置决定使用 BGE-M3(`BGE_M3_Embedder`) 或 MiniLM(`SentenceTransformerEmbedding`)
          作为嵌入提供者, 交给 `ConceptDeduplicator` 计算相似度矩阵并做聚类。

        如初始化失败(例如 Ollama 未启动、模型未拉取), 会直接抛异常, 让上层尽早感知问题。
        """
        try:
            logger.info("Initializing concept extractor...")
            # LLM 模型和 Ollama 服务地址从配置中读取
            self.concept_extractor = ConceptExtractor(
                model=self.ollama_model,
                ollama_host=self.ollama_host,
                timeout=self.llm_timeout
            )
            logger.info(f"Concept extractor initialized (timeout: {self.llm_timeout}s)")
        except Exception as e:
            logger.error(f"Failed to initialize concept extractor: {e}")
            logger.error("Make sure Ollama is running: ollama serve")
            raise
        
        try:
            logger.info("Initializing concept deduplicator...")
            # 去重相关配置从配置中读取
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
        """运行安全管道(支持断点续传)

        参数:
            pdf_dir: 待处理 PDF 所在目录(通常为 `./文献`);
            resume: 是否从上次中断处继续(默认 True, 会根据 `.progress.json` 跳过已处理块);
            clear_checkpoint: 是否清除旧的 checkpoint(如需“从头再跑一遍”或更换配置时建议设为 True)。

        返回:
            (concepts_df, relationships_df):
            - concepts_df: 去重+过滤后的概念表;
            - relationships_df: 合并 W1/W2、更新端点、过滤后的关系表。

        整体阶段划分(对应日志中的 Step 1~6):
        1. 从 `pdf_dir` 提取并清洗所有 PDF 文本;
        2. 对清洗文本做分块, 生成带 `chunk_id` 的块列表;
        3. 逐块调用 LLM 抽取概念/关系, 同时写入增量 checkpoint;
        4. 基于 chunk 内共现关系生成 W2, 并准备与 W1 合并;
        5. 合并关系并对概念做语义去重, 更新关系端点;
        6. 按重要性与连接度过滤, 得到最终子图并落盘。
        """
        logger.info("="*60)
        logger.info("Starting Safe Enhanced Pipeline with Checkpoint Support")
        logger.info("="*60)
        
        # 清除旧 checkpoint（如果需要）
        if clear_checkpoint:
            logger.info("Clearing old checkpoints...")
            # 一般在“重头再跑一遍”或更换配置时才会打开该开关
            self.checkpoint_manager.clear()
        
        # 检查是否有未完成的任务
        if resume:
            # 从 .progress.json 里读一个简要摘要，用于在日志中给出“续跑提示”
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
                # 从 checkpoint 中拿到已经处理过的 chunk_id 集合，只处理剩余部分
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
            logger.warning("User interrupted (Ctrl+C)")
            logger.warning("="*60)
            logger.info("Checkpoint已自动保存，下次运行将从中断处继续")
            logger.info(f"进度保存位置: {self.checkpoint_manager.checkpoint_dir}")
            raise
        
        except Exception as e:
            logger.error("\n" + "="*60)
            logger.error(f"Error occurred: {e}")
            logger.error("="*60)
            logger.info("Checkpoint已自动保存，可尝试重新运行恢复")
            logger.info(f"进度保存位置: {self.checkpoint_manager.checkpoint_dir}")
            raise
    
    def _extract_with_checkpoints(self, chunks: List[Dict]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        带 checkpoint 的 LLM 抽取阶段

        核心改进(相对简单 for-loop 抽取):
        - **每 N 个块保存一次完整快照**: 方便中途查看“当前全局结果”, 也降低单次故障影响范围;
        - **每个块结束后立即增量写入**: `save_chunk_results(chunk_id, concepts, relationships)`,
          即使进程中断, 已处理块的结果也都在增量 CSV 中;
        - **出错不终止主循环**: 单块抽取异常只记录日志并 `continue`, 管道整体可以跑完。
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
                
                # 无论当前块是否抽取成功，都会把结果写入 checkpoint，保证进度单调前进
                self.checkpoint_manager.save_chunk_results(chunk_id, concepts, relationships)
                
                # 定期保存完整 checkpoint，方便中途查看“当前全局效果”
                if (i + 1) % self.checkpoint_interval == 0:
                    temp_concepts_df = pd.DataFrame(all_concepts) if all_concepts else pd.DataFrame()
                    temp_relationships_df = pd.DataFrame(all_relationships) if all_relationships else pd.DataFrame()
                    
                    self.checkpoint_manager.save_checkpoint(
                        i + 1, temp_concepts_df, temp_relationships_df
                    )
                    
                    logger.info(f"Checkpoint: {i+1}/{len(chunks)} chunks processed")
            
            except Exception as e:
                # 单个文本块失败不会中断整个流程，只记录错误并继续下一个
                logger.error(f"Failed to process chunk {chunk_id}: {e}")
                continue
        
        # 最终数据
        concepts_df = pd.DataFrame(all_concepts) if all_concepts else pd.DataFrame()
        relationships_df = pd.DataFrame(all_relationships) if all_relationships else pd.DataFrame()
        
        logger.info(f"Extraction complete: {len(concepts_df)} concepts, {len(relationships_df)} relationships")
        
        return concepts_df, relationships_df
    
    def _extract_pdf_texts(self, pdf_dir: str) -> Dict[str, str]:
        """提取 PDF 文本

        封装对 `PDFExtractor` 的调用, 按配置决定是否启用缓存/并行(当前实现内部统一串行),
        返回 `{pdf_name: cleaned_text}` 形式的字典, 供后续分块使用。
        """
        extractor = PDFExtractor(
            use_cache=self.config.get('system.enable_cache', True),
            enable_parallel=self.config.get('system.enable_parallel', True)
        )
        return extractor.extract_from_directory(pdf_dir)
    
    def _create_chunks(self, pdf_texts: Dict[str, str], chunk_size: int = 3000,
                      overlap: int = 300) -> List[Dict]:
        """将每篇 PDF 文本切分为多个 chunk

        参数:
            pdf_texts: `{pdf_name: text}` 形式的清洗后文本字典;
            chunk_size: 每个块的目标长度(字符数, 默认 3000);
            overlap: 相邻块之间的重叠长度(默认 300), 保障跨块语境连续性。

        说明:
        - 按 `chunk_size - overlap` 的步长滑动窗口截取文本;
        - 过滤过短片段(长度 < 50), 避免把页眉/脚或噪声当作有效块;
        - 为每个块生成唯一 `chunk_id = {pdf_name}_{counter}` 作为后续追踪的主键。
        """
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
        """基于共现的近邻关系提取(W2)

        步骤:
        1. 根据概念表 `concepts_df` 构建 `{chunk_id: [entity,...]}` 的概念列表映射;
        2. 将这些列表写回 `chunks` 中的 `chunk['concepts']` 字段;
        3. 调用 `ContextualProximityAnalyzer.extract_proximity_relationships` 生成 W2 关系 DataFrame。

        返回:
            只包含共现关系的 DataFrame, 后续会与 LLM 抽取的 W1 关系在 `_merge_and_deduplicate` 中合并。
        """
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
        """合并关系并进行概念去重

        处理顺序:
        1. 使用 `ContextualProximityAnalyzer.merge_relationships` 将 W1 与 W2 合并成统一的
           `relationships_df`, 对同一 `(node_1,node_2)` 的多条边累加权重并归一化;
        2. 若配置成功初始化了 `self.deduplicator` 且概念表非空, 调用 `deduplicate_concepts`:
           - 在向量空间中识别语义相近的概念簇;
           - 为每簇选择一个“规范名”并构建 `concept_mapping`;
        3. 若存在关系数据, 使用 `RelationshipDeduplicator.update_relationships` 将关系两端
           的概念名称替换为上述规范名, 并去除自环关系。
        """
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
        """根据重要性与连通度过滤概念, 并同步裁剪关系

        过滤逻辑:
        - 首先调用 `ConceptImportanceFilter.filter_concepts`:
          - 去掉配置中的通用/泛化概念(如“因素/机制/过程”等);
          - 丢弃 `importance` 低于阈值的概念;
          - 如提供关系表, 还会按参与关系条数(`connections`)过滤弱连接节点;
        - 然后只保留两端都在 `filtered_concepts` 中的关系, 确保最终关系只链接保留下来的概念。
        """
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
        """保存最终结果到 CSV 文件

        - 输出目录由配置项 `output.base_directory` 控制, 默认 `./output`;
        - 使用 UTF-8-SIG 编码, 便于在 Excel 中直接打开不会出现中文乱码;
        - 文件名固定为 `concepts.csv` 和 `relationships.csv`, 供 Neo4j 导入脚本和
          后续分析工具(如 GraphRAG、统计脚本)直接使用。
        """
        os.makedirs(self.output_dir, exist_ok=True)
        
        concepts_path = f"{self.output_dir}/concepts.csv"
        concepts_df.to_csv(concepts_path, index=False, encoding='utf-8-sig')
        logger.info(f"Saved concepts to {concepts_path}")
        
        relationships_path = f"{self.output_dir}/relationships.csv"
        relationships_df.to_csv(relationships_path, index=False, encoding='utf-8-sig')
        logger.info(f"Saved relationships to {relationships_path}")


def run_safe_pipeline(pdf_dir: str = None, config: Dict = None,
                     checkpoint_interval: int = 5,
                     resume: bool = True,
                     clear_checkpoint: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """安全版知识图谱构建管道的便捷入口

    一般不直接实例化 `EnhancedKnowledgeGraphPipelineSafe`, 而是通过此函数在脚本中调用,
    例如在 `start.sh` 或其他上层调度中统一复用。

    参数:
        pdf_dir: PDF 目录, 不传则从配置 `pdf.input_directory` 读取(默认 `./文献`);
        config: 配置字典, 不传则自动从 `config/config.yaml` 加载;
        checkpoint_interval: 写入完整 checkpoint 的间隔(块数, 默认 5);
        resume: 是否启用断点续传(默认 True);
        clear_checkpoint: 是否在本次运行前清除旧 checkpoint(默认 False)。

    返回:
        (concepts_df, relationships_df): 与 `EnhancedKnowledgeGraphPipelineSafe.run` 一致。
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
