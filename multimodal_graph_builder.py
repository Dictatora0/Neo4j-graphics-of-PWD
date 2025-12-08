#!/usr/bin/env python3
"""
多模态知识图谱构建模块

功能:
1. 创建 :Image 节点，存储图片路径和 Caption
2. 建立 (:Concept)-[:ILLUSTRATED_BY]->(:Image) 关系
3. 支持 Graph RAG 时召回关联图片
"""

import logging
from typing import List, Dict, Tuple, Optional
import pandas as pd
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class MultimodalGraphBuilder:
    """
    多模态知识图谱构建器
    
    功能:
    - 将图片信息整合到知识图谱中
    - 建立概念与图片的关联关系
    - 支持基于概念检索相关图片
    """
    
    def __init__(self, image_dir: str = "./output/pdf_images"):
        """
        Args:
            image_dir: 图片存储目录
        """
        self.image_dir = Path(image_dir)
        logger.info(f"MultimodalGraphBuilder initialized with image_dir: {image_dir}")
    
    def load_image_captions(self, caption_file: str = "output/image_captions.json") -> pd.DataFrame:
        """
        加载图片描述文件
        
        Args:
            caption_file: 图片描述 JSON 文件路径
        
        Returns:
            DataFrame with columns: [image_path, caption, source_pdf, page_num]
        """
        try:
            with open(caption_file, 'r', encoding='utf-8') as f:
                captions_data = json.load(f)
            
            images_df = pd.DataFrame(captions_data)
            logger.info(f"Loaded {len(images_df)} image captions")
            
            return images_df
        
        except FileNotFoundError:
            logger.warning(f"Caption file not found: {caption_file}")
            return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Failed to load image captions: {e}")
            return pd.DataFrame()
    
    def extract_concepts_from_captions(self, images_df: pd.DataFrame,
                                      concept_extractor) -> pd.DataFrame:
        """
        从图片描述中提取概念
        
        Args:
            images_df: 图片 DataFrame
            concept_extractor: ConceptExtractor 实例
        
        Returns:
            DataFrame with columns: [image_path, concepts]
        """
        if images_df.empty:
            return pd.DataFrame()
        
        logger.info("Extracting concepts from image captions...")
        
        image_concepts = []
        
        for _, row in images_df.iterrows():
            caption = row.get('caption', '')
            image_path = row.get('image_path', '')
            
            if not caption or len(caption.strip()) < 10:
                continue
            
            # 使用 LLM 从 caption 中提取概念
            try:
                concepts, _ = concept_extractor.extract_concepts_and_relationships(
                    caption,
                    chunk_id=f"image_{Path(image_path).stem}"
                )
                
                if concepts:
                    concept_names = [c['entity'] for c in concepts]
                    image_concepts.append({
                        'image_path': image_path,
                        'concepts': concept_names,
                        'caption': caption
                    })
            
            except Exception as e:
                logger.warning(f"Failed to extract concepts from image {image_path}: {e}")
                continue
        
        result_df = pd.DataFrame(image_concepts)
        logger.info(f"Extracted concepts from {len(result_df)} images")
        
        return result_df
    
    def build_image_concept_relationships(self, 
                                         image_concepts_df: pd.DataFrame,
                                         concepts_df: pd.DataFrame) -> pd.DataFrame:
        """
        构建图片与概念的关系
        
        Args:
            image_concepts_df: 图片概念 DataFrame
            concepts_df: 主概念 DataFrame
        
        Returns:
            DataFrame with columns: [concept, image_path, caption, relationship_type]
        """
        if image_concepts_df.empty or concepts_df.empty:
            return pd.DataFrame()
        
        logger.info("Building image-concept relationships...")
        
        relationships = []
        valid_concepts = set(concepts_df['entity'].str.lower())
        
        for _, row in image_concepts_df.iterrows():
            image_path = row['image_path']
            caption = row['caption']
            concepts = row.get('concepts', [])
            
            for concept in concepts:
                concept_lower = concept.lower()
                
                # 只关联已存在于知识图谱中的概念
                if concept_lower in valid_concepts:
                    relationships.append({
                        'concept': concept_lower,
                        'image_path': image_path,
                        'caption': caption,
                        'relationship_type': 'ILLUSTRATED_BY'
                    })
        
        result_df = pd.DataFrame(relationships)
        logger.info(f"Built {len(result_df)} image-concept relationships")
        
        return result_df
    
    def generate_neo4j_import_statements(self, 
                                        images_df: pd.DataFrame,
                                        image_concept_rels_df: pd.DataFrame) -> List[str]:
        """
        生成 Neo4j 导入语句
        
        Args:
            images_df: 图片 DataFrame
            image_concept_rels_df: 图片-概念关系 DataFrame
        
        Returns:
            Cypher 语句列表
        """
        statements = []
        
        # 1. 创建 :Image 节点
        logger.info("Generating Image node creation statements...")
        
        for _, row in images_df.iterrows():
            image_path = row['image_path']
            caption = row.get('caption', '').replace("'", "\\'")  # 转义单引号
            source_pdf = row.get('source_pdf', '')
            page_num = row.get('page_num', 0)
            
            cypher = f"""
CREATE (img:Image {{
    path: '{image_path}',
    caption: '{caption}',
    source_pdf: '{source_pdf}',
    page_num: {page_num},
    created_at: datetime()
}})
"""
            statements.append(cypher.strip())
        
        # 2. 创建 (:Concept)-[:ILLUSTRATED_BY]->(:Image) 关系
        logger.info("Generating ILLUSTRATED_BY relationship statements...")
        
        for _, row in image_concept_rels_df.iterrows():
            concept = row['concept'].replace("'", "\\'")
            image_path = row['image_path']
            
            cypher = f"""
MATCH (c:Concept {{name: '{concept}'}})
MATCH (img:Image {{path: '{image_path}'}})
CREATE (c)-[:ILLUSTRATED_BY]->(img)
"""
            statements.append(cypher.strip())
        
        logger.info(f"Generated {len(statements)} Cypher statements")
        
        return statements
    
    def export_to_csv(self, 
                     images_df: pd.DataFrame,
                     image_concept_rels_df: pd.DataFrame,
                     output_dir: str = "output"):
        """
        导出为 CSV 文件
        
        Args:
            images_df: 图片 DataFrame
            image_concept_rels_df: 图片-概念关系 DataFrame
            output_dir: 输出目录
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 导出图片节点
        images_csv = output_path / "images.csv"
        images_df.to_csv(images_csv, index=False, encoding='utf-8')
        logger.info(f"Exported images to {images_csv}")
        
        # 导出图片-概念关系
        rels_csv = output_path / "image_concept_relationships.csv"
        image_concept_rels_df.to_csv(rels_csv, index=False, encoding='utf-8')
        logger.info(f"Exported relationships to {rels_csv}")


class MultimodalRetriever:
    """
    多模态检索器 - 用于 Graph RAG
    
    功能:
    - 根据概念检索相关图片
    - 支持 Local Search 时召回图片
    """
    
    def __init__(self, image_concept_rels_df: pd.DataFrame):
        """
        Args:
            image_concept_rels_df: 图片-概念关系 DataFrame
        """
        self.image_concept_rels_df = image_concept_rels_df
        
        # 构建概念到图片的索引
        self.concept_to_images = {}
        for _, row in image_concept_rels_df.iterrows():
            concept = row['concept']
            image_path = row['image_path']
            caption = row['caption']
            
            if concept not in self.concept_to_images:
                self.concept_to_images[concept] = []
            
            self.concept_to_images[concept].append({
                'path': image_path,
                'caption': caption
            })
        
        logger.info(f"MultimodalRetriever initialized with {len(self.concept_to_images)} concepts")
    
    def retrieve_images_for_concepts(self, concepts: List[str], 
                                    max_images_per_concept: int = 3) -> List[Dict]:
        """
        根据概念列表检索相关图片
        
        Args:
            concepts: 概念列表
            max_images_per_concept: 每个概念最多返回的图片数
        
        Returns:
            图片信息列表 [{'path': ..., 'caption': ..., 'related_concept': ...}, ...]
        """
        retrieved_images = []
        seen_paths = set()
        
        for concept in concepts:
            concept_lower = concept.lower()
            
            if concept_lower in self.concept_to_images:
                images = self.concept_to_images[concept_lower][:max_images_per_concept]
                
                for img in images:
                    if img['path'] not in seen_paths:
                        retrieved_images.append({
                            'path': img['path'],
                            'caption': img['caption'],
                            'related_concept': concept
                        })
                        seen_paths.add(img['path'])
        
        logger.info(f"Retrieved {len(retrieved_images)} images for {len(concepts)} concepts")
        
        return retrieved_images


if __name__ == "__main__":
    # 测试示例
    print("="*80)
    print("多模态知识图谱构建器测试")
    print("="*80)
    
    # 创建构建器
    builder = MultimodalGraphBuilder()
    
    # 加载图片描述
    images_df = builder.load_image_captions()
    
    if not images_df.empty:
        print(f"\n加载了 {len(images_df)} 张图片")
        print(images_df.head())
    else:
        print("\n未找到图片描述文件，请先运行图片提取流程")
