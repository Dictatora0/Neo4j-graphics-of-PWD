#!/usr/bin/env python3
"""
Enhanced Knowledge Graph Pipeline
Integrates LLM-based concept extraction with embedding-based deduplication
"""

import os
import logging
from typing import Dict, List, Tuple
import pandas as pd
from datetime import datetime

from pdf_extractor import PDFExtractor
from concept_extractor import ConceptExtractor, ContextualProximityAnalyzer
from concept_deduplicator import (
    ConceptDeduplicator, 
    RelationshipDeduplicator,
    ConceptImportanceFilter,
    SentenceTransformerEmbedding
)
from data_cleaner import DataCleaner
from neo4j_generator import Neo4jGenerator
from config_loader import load_config
from logger_config import get_logger

logger = get_logger('EnhancedPipeline')


class EnhancedKnowledgeGraphPipeline:
    """
    Enhanced pipeline combining:
    1. LLM-based concept extraction (vs traditional NER)
    2. Semantic relationship extraction with weighting
    3. Contextual proximity analysis
    4. Embedding-based deduplication
    5. Importance filtering
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize enhanced pipeline
        
        Args:
            config: Configuration dictionary
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
        self.max_chunks = config.get('llm.max_chunks', 100)  # Limit chunks for faster processing
        
        # Initialize components
        self.concept_extractor = None
        self.deduplicator = None
        self.proximity_analyzer = ContextualProximityAnalyzer()
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize LLM and embedding components"""
        try:
            logger.info("Initializing concept extractor...")
            self.concept_extractor = ConceptExtractor(
                model=self.ollama_model,
                ollama_host=self.ollama_host
            )
            logger.info("✓ Concept extractor initialized")
        except Exception as e:
            logger.error(f"Failed to initialize concept extractor: {e}")
            logger.error("Make sure Ollama is running: ollama serve")
            raise
        
        try:
            logger.info("Initializing concept deduplicator...")
            embedding_provider = SentenceTransformerEmbedding()
            self.deduplicator = ConceptDeduplicator(
                embedding_provider=embedding_provider,
                similarity_threshold=self.similarity_threshold
            )
            logger.info("✓ Concept deduplicator initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize embeddings: {e}")
            logger.warning("Deduplication will be skipped")
            self.deduplicator = None
    
    def run(self, pdf_dir: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Run complete enhanced pipeline
        
        Args:
            pdf_dir: Directory containing PDF files
        
        Returns:
            Tuple of (concepts_df, relationships_df)
        """
        logger.info("="*60)
        logger.info("Starting Enhanced Knowledge Graph Pipeline")
        logger.info("="*60)
        
        start_time = datetime.now()
        
        # Step 1: Extract text from PDFs
        logger.info("\n[Step 1/6] Extracting text from PDFs...")
        pdf_texts = self._extract_pdf_texts(pdf_dir)
        
        if not pdf_texts:
            logger.error("No PDF texts extracted")
            return pd.DataFrame(), pd.DataFrame()
        
        # Step 2: Split into chunks
        logger.info("\n[Step 2/6] Splitting texts into chunks...")
        chunks = self._create_chunks(pdf_texts)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Step 3: Extract concepts and relationships using LLM
        logger.info("\n[Step 3/6] Extracting concepts and relationships using LLM...")
        logger.info(f"Processing limit: {self.max_chunks if self.max_chunks else 'ALL'} chunks")
        concepts_df, llm_relationships_df = self.concept_extractor.extract_from_chunks(chunks, max_chunks=self.max_chunks)
        logger.info(f"Extracted {len(concepts_df)} concepts and {len(llm_relationships_df)} LLM relationships")
        
        # Step 4: Extract contextual proximity relationships
        logger.info("\n[Step 4/6] Analyzing contextual proximity...")
        proximity_relationships_df = self._extract_proximity_relationships(chunks, concepts_df)
        logger.info(f"Extracted {len(proximity_relationships_df)} proximity relationships")
        
        # Step 5: Merge and deduplicate
        logger.info("\n[Step 5/6] Merging and deduplicating concepts...")
        concepts_df, relationships_df = self._merge_and_deduplicate(
            concepts_df, llm_relationships_df, proximity_relationships_df
        )
        
        # Step 6: Filter and finalize
        logger.info("\n[Step 6/6] Filtering and finalizing...")
        concepts_df, relationships_df = self._filter_and_finalize(concepts_df, relationships_df)
        
        # Save intermediate results
        self._save_results(concepts_df, relationships_df)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info("\n" + "="*60)
        logger.info("✓ Enhanced Pipeline Completed Successfully!")
        logger.info("="*60)
        logger.info(f"Duration: {duration}")
        logger.info(f"Final concepts: {len(concepts_df)}")
        logger.info(f"Final relationships: {len(relationships_df)}")
        
        return concepts_df, relationships_df
    
    def _extract_pdf_texts(self, pdf_dir: str) -> Dict[str, str]:
        """Extract texts from PDFs"""
        extractor = PDFExtractor(
            use_cache=self.config.get('system.enable_cache', True),
            enable_parallel=self.config.get('system.enable_parallel', True)
        )
        return extractor.extract_from_directory(pdf_dir)
    
    def _create_chunks(self, pdf_texts: Dict[str, str], chunk_size: int = 3000, 
                      overlap: int = 300) -> List[Dict]:
        """
        Split texts into chunks
        
        Args:
            pdf_texts: Dictionary of PDF texts
            chunk_size: Size of each chunk
            overlap: Overlap between chunks
        
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        chunk_id_counter = 0
        
        for pdf_name, text in pdf_texts.items():
            # Split text into chunks with overlap
            for i in range(0, len(text), chunk_size - overlap):
                chunk_text = text[i:i + chunk_size]
                
                if len(chunk_text.strip()) > 50:  # Skip very small chunks
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
        """
        Extract relationships based on contextual proximity
        
        Concepts that appear in the same chunk are related by proximity
        """
        # Add extracted concepts to chunks for proximity analysis
        concept_map = {}
        for _, row in concepts_df.iterrows():
            chunk_id = row.get('chunk_id', '')
            if chunk_id not in concept_map:
                concept_map[chunk_id] = []
            concept_map[chunk_id].append(row['entity'])
        
        # Update chunks with concepts
        for chunk in chunks:
            chunk['concepts'] = concept_map.get(chunk['chunk_id'], [])
        
        # Extract proximity relationships
        return self.proximity_analyzer.extract_proximity_relationships(chunks)
    
    def _merge_and_deduplicate(self, concepts_df: pd.DataFrame,
                              llm_relationships_df: pd.DataFrame,
                              proximity_relationships_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Merge relationships and deduplicate concepts
        
        Returns:
            Tuple of (deduplicated_concepts_df, merged_relationships_df)
        """
        # Merge relationships
        relationships_df = self.proximity_analyzer.merge_relationships(
            llm_relationships_df, proximity_relationships_df
        )
        logger.info(f"Merged relationships: {len(relationships_df)}")
        
        # Deduplicate concepts if deduplicator is available
        if self.deduplicator and not concepts_df.empty:
            concepts_df, concept_mapping = self.deduplicator.deduplicate_concepts(concepts_df)
            
            # Update relationships with canonical concept names (only if relationships exist)
            if not relationships_df.empty:
                relationships_df = RelationshipDeduplicator.update_relationships(
                    relationships_df, concept_mapping
                )
                logger.info(f"Updated relationships after deduplication: {len(relationships_df)}")
        
        return concepts_df, relationships_df
    
    def _filter_and_finalize(self, concepts_df: pd.DataFrame,
                            relationships_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Filter concepts by importance and connectivity
        
        Returns:
            Tuple of (filtered_concepts_df, filtered_relationships_df)
        """
        # Filter concepts
        filtered_concepts = ConceptImportanceFilter.filter_concepts(
            concepts_df, relationships_df,
            min_importance=self.min_concept_importance,
            min_connections=self.min_connections
        )
        
        # Filter relationships to only include remaining concepts
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
        """Save intermediate results"""
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Save concepts
        concepts_path = f"{self.output_dir}/concepts.csv"
        concepts_df.to_csv(concepts_path, index=False, encoding='utf-8-sig')
        logger.info(f"✓ Saved concepts to {concepts_path}")
        
        # Save relationships
        relationships_path = f"{self.output_dir}/relationships.csv"
        relationships_df.to_csv(relationships_path, index=False, encoding='utf-8-sig')
        logger.info(f"✓ Saved relationships to {relationships_path}")


def run_enhanced_pipeline(pdf_dir: str = None, config: Dict = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convenience function to run enhanced pipeline
    
    Args:
        pdf_dir: Directory containing PDFs (uses config if not provided)
        config: Configuration dictionary
    
    Returns:
        Tuple of (concepts_df, relationships_df)
    """
    if config is None:
        config = load_config()
    
    if pdf_dir is None:
        pdf_dir = config.get('pdf.input_directory', './文献')
    
    pipeline = EnhancedKnowledgeGraphPipeline(config)
    return pipeline.run(pdf_dir)


if __name__ == "__main__":
    # Example usage
    concepts_df, relationships_df = run_enhanced_pipeline()
    
    print("\n" + "="*60)
    print("Enhanced Pipeline Results")
    print("="*60)
    print(f"Concepts: {len(concepts_df)}")
    print(f"Relationships: {len(relationships_df)}")
    
    if not concepts_df.empty:
        print("\nTop 10 Concepts by Importance:")
        print(concepts_df.nlargest(10, 'importance')[['entity', 'importance', 'category']])
    
    if not relationships_df.empty:
        print("\nTop 10 Relationships by Weight:")
        print(relationships_df.nlargest(10, 'weight')[['node_1', 'node_2', 'edge', 'weight']])
