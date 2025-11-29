#!/usr/bin/env python3
"""
Multimodal Knowledge Extraction Module
多模态知识抽取模块 - 攻克 PDF 图表知识

核心功能:
1. 从 PDF 中提取图片 (显微镜照片、统计图表、分布地图)
2. 使用 VLM (Vision-Language Models) 生成图片描述
3. 从图片描述中抽取知识三元组
4. 将图片知识融合到知识图谱

支持的 VLM:
- Qwen2-VL-7B (本地 Ollama)
- LLaVA-Next (本地 Ollama)
- transformers (本地 GPU)
"""

import os
import io
import json
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import requests
from PIL import Image
import base64

logger = logging.getLogger(__name__)

# 尝试导入 PDF 库
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF 不可用,图片提取功能受限")

# 尝试导入 transformers (本地 VLM)
try:
    from transformers import AutoProcessor, AutoModelForVision2Seq
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers 不可用,本地 VLM 功能受限")


class ImageExtractor:
    """
    PDF 图片提取器
    
    功能:
    - 从 PDF 中提取所有图片
    - 过滤低质量图片 (尺寸过小、重复等)
    - 保存图片到指定目录
    """
    
    def __init__(self, output_dir: str = './output/pdf_images', 
                 min_width: int = 200, min_height: int = 200,
                 max_images_per_pdf: int = 25):
        """
        Args:
            output_dir: 图片保存目录
            min_width: 最小图片宽度
            min_height: 最小图片高度
            max_images_per_pdf: 每个 PDF 最多提取图片数
        """
        self.output_dir = output_dir
        self.min_width = min_width
        self.min_height = min_height
        self.max_images_per_pdf = max_images_per_pdf
        
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"图片提取器已初始化: 输出目录 {output_dir}")
    
    def extract_images_from_pdf(self, pdf_path: str) -> List[Dict]:
        """
        从 PDF 中提取图片
        
        Args:
            pdf_path: PDF 文件路径
        
        Returns:
            图片信息列表 [{'path': str, 'page': int, 'size': (w, h)}, ...]
        """
        if not PYMUPDF_AVAILABLE:
            logger.error("PyMuPDF 未安装,无法提取图片")
            return []
        
        pdf_name = Path(pdf_path).stem
        images_info = []
        
        try:
            doc = fitz.open(pdf_path)
            image_count = 0
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # 获取页面图片列表
                image_list = page.get_images(full=True)
                
                for img_index, img_info in enumerate(image_list):
                    if image_count >= self.max_images_per_pdf:
                        logger.info(f"达到最大图片数限制 ({self.max_images_per_pdf})")
                        break
                    
                    xref = img_info[0]
                    
                    # 提取图片数据
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # 加载图片检查尺寸
                    try:
                        image = Image.open(io.BytesIO(image_bytes))
                        width, height = image.size
                        
                        # 过滤小图片
                        if width < self.min_width or height < self.min_height:
                            logger.debug(f"跳过小图片: {width}x{height}")
                            continue
                        
                        # 保存图片
                        image_filename = f"{pdf_name}_p{page_num + 1}_img{img_index + 1}.{image_ext}"
                        image_path = os.path.join(self.output_dir, image_filename)
                        
                        with open(image_path, "wb") as f:
                            f.write(image_bytes)
                        
                        images_info.append({
                            'path': image_path,
                            'page': page_num + 1,
                            'size': (width, height),
                            'format': image_ext
                        })
                        
                        image_count += 1
                        logger.debug(f"提取图片: {image_filename} ({width}x{height})")
                    
                    except Exception as e:
                        logger.warning(f"图片加载失败: {e}")
                        continue
            
            doc.close()
            logger.info(f"从 {pdf_name} 提取 {len(images_info)} 张图片")
            
        except Exception as e:
            logger.error(f"PDF 图片提取失败: {e}")
        
        return images_info


class VisionLanguageModel:
    """
    视觉-语言模型接口
    
    支持两种模式:
    1. Ollama 模式: 使用本地 Ollama 服务的 VLM (如 llava, qwen2-vl)
    2. Transformers 模式: 使用 Hugging Face transformers 本地加载 VLM
    """
    
    def __init__(self, provider: str = 'ollama', model: str = 'llava',
                 ollama_host: str = 'http://localhost:11434'):
        """
        Args:
            provider: 'ollama' 或 'transformers'
            model: 模型名称
            ollama_host: Ollama 服务地址
        """
        self.provider = provider.lower()
        self.model = model
        self.ollama_host = ollama_host
        
        if self.provider == 'transformers':
            self._init_transformers_model()
        elif self.provider == 'ollama':
            self._verify_ollama_vlm()
        else:
            raise ValueError(f"不支持的 provider: {provider}")
    
    def _init_transformers_model(self):
        """初始化 transformers VLM"""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers 未安装,请运行: pip install transformers torch")
        
        try:
            logger.info(f"加载 transformers VLM: {self.model}")
            self.processor = AutoProcessor.from_pretrained(self.model)
            self.vlm_model = AutoModelForVision2Seq.from_pretrained(
                self.model,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto"
            )
            logger.info("VLM 加载成功")
        except Exception as e:
            logger.error(f"VLM 加载失败: {e}")
            raise
    
    def _verify_ollama_vlm(self):
        """验证 Ollama VLM 可用性"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '').split(':')[0] for m in models]
                
                if self.model not in model_names:
                    logger.warning(f"Ollama 中未找到模型 {self.model}")
                    logger.warning(f"可用模型: {', '.join(model_names)}")
                else:
                    logger.info(f"Ollama VLM 已就绪: {self.model}")
            else:
                raise ConnectionError(f"Ollama 返回状态 {response.status_code}")
        except Exception as e:
            logger.error(f"Ollama 连接失败: {e}")
            raise
    
    def generate_caption(self, image_path: str, prompt: str = None) -> Optional[str]:
        """
        为图片生成描述
        
        Args:
            image_path: 图片路径
            prompt: 自定义提示词 (可选)
        
        Returns:
            图片描述文本
        """
        if self.provider == 'ollama':
            return self._generate_with_ollama(image_path, prompt)
        elif self.provider == 'transformers':
            return self._generate_with_transformers(image_path, prompt)
    
    def _generate_with_ollama(self, image_path: str, prompt: str = None) -> Optional[str]:
        """使用 Ollama VLM 生成描述"""
        if prompt is None:
            prompt = """请详细描述这张图片中与松材线虫病相关的内容:
1. 如果是显微镜照片,描述线虫或天牛的形态特征
2. 如果是统计图表,描述数据趋势和关键数值
3. 如果是地图,描述病害分布区域和地理特征
4. 提取图中出现的关键实体和数值信息"""
        
        try:
            # 读取并编码图片
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # 调用 Ollama VLM API
            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [image_base64],
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_ctx": 4096
                }
            }
            
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json=payload,
                timeout=180
            )
            response.raise_for_status()
            
            result = response.json()
            caption = result.get('response', '').strip()
            
            logger.debug(f"图片描述生成成功: {len(caption)} 字符")
            return caption
        
        except Exception as e:
            logger.error(f"Ollama VLM 生成失败: {e}")
            return None
    
    def _generate_with_transformers(self, image_path: str, prompt: str = None) -> Optional[str]:
        """使用 transformers VLM 生成描述"""
        if prompt is None:
            prompt = "Describe this image in detail, focusing on biological features, data trends, or geographical information related to pine wilt disease."
        
        try:
            # 加载图片
            image = Image.open(image_path).convert('RGB')
            
            # 处理输入
            inputs = self.processor(images=image, text=prompt, return_tensors="pt")
            
            # 移动到 GPU (如果可用)
            if torch.cuda.is_available():
                inputs = {k: v.to('cuda') for k, v in inputs.items()}
            
            # 生成
            with torch.no_grad():
                outputs = self.vlm_model.generate(**inputs, max_new_tokens=200)
            
            # 解码
            caption = self.processor.decode(outputs[0], skip_special_tokens=True)
            
            logger.debug(f"图片描述生成成功: {len(caption)} 字符")
            return caption
        
        except Exception as e:
            logger.error(f"transformers VLM 生成失败: {e}")
            return None


class MultimodalExtractor:
    """
    多模态知识抽取器 - 整合图片提取和知识抽取
    
    工作流程:
    1. 从 PDF 中提取图片
    2. 使用 VLM 为每张图片生成描述
    3. 将图片描述作为文本块加入到知识抽取流程
    4. 抽取图片中的概念和关系
    """
    
    def __init__(self, image_extractor: ImageExtractor, vlm: VisionLanguageModel):
        self.image_extractor = image_extractor
        self.vlm = vlm
        logger.info("多模态抽取器已初始化")
    
    def extract_from_pdf(self, pdf_path: str) -> List[Dict]:
        """
        从 PDF 的图片中抽取知识
        
        Args:
            pdf_path: PDF 文件路径
        
        Returns:
            图片知识块列表 [{'text': str, 'chunk_id': str, 'image_path': str, 'page': int}, ...]
        """
        # 1. 提取图片
        images_info = self.image_extractor.extract_images_from_pdf(pdf_path)
        
        if not images_info:
            logger.warning(f"未从 {pdf_path} 提取到图片")
            return []
        
        # 2. 为每张图片生成描述
        image_chunks = []
        
        for i, img_info in enumerate(images_info, 1):
            logger.info(f"处理图片 {i}/{len(images_info)}: {img_info['path']}")
            
            caption = self.vlm.generate_caption(img_info['path'])
            
            if caption:
                chunk_id = f"{Path(pdf_path).stem}_image_{i}"
                
                image_chunks.append({
                    'text': caption,
                    'chunk_id': chunk_id,
                    'image_path': img_info['path'],
                    'page': img_info['page'],
                    'source_type': 'image',
                    'concepts': []  # 用于后续概念抽取
                })
                
                logger.debug(f"图片描述: {caption[:100]}...")
            else:
                logger.warning(f"图片 {img_info['path']} 描述生成失败")
        
        logger.info(f"多模态抽取完成: {len(image_chunks)} 个图片块")
        return image_chunks
    
    def extract_from_directory(self, pdf_dir: str) -> Dict[str, List[Dict]]:
        """
        从目录中所有 PDF 的图片抽取知识
        
        Args:
            pdf_dir: PDF 目录路径
        
        Returns:
            {pdf_name: [image_chunks]}
        """
        pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
        
        logger.info(f"找到 {len(pdf_files)} 个 PDF 文件")
        
        all_image_chunks = {}
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(pdf_dir, pdf_file)
            
            logger.info(f"处理 PDF: {pdf_file}")
            image_chunks = self.extract_from_pdf(pdf_path)
            
            if image_chunks:
                all_image_chunks[pdf_file] = image_chunks
        
        logger.info(f"多模态抽取完成: 共 {sum(len(v) for v in all_image_chunks.values())} 个图片块")
        
        return all_image_chunks


def create_multimodal_extractor(config: Dict = None) -> Optional[MultimodalExtractor]:
    """
    工厂函数: 根据配置创建多模态抽取器
    
    Args:
        config: 配置字典
    
    Returns:
        MultimodalExtractor 实例或 None (如果未启用)
    """
    if config is None:
        config = {}
    
    # 检查是否启用
    enable_image_captions = config.get('pdf.enable_image_captions', False)
    
    if not enable_image_captions:
        logger.info("多模态功能未启用 (配置: pdf.enable_image_captions=false)")
        return None
    
    # 读取配置
    image_output_dir = config.get('pdf.image_output_dir', './output/pdf_images')
    max_images_per_pdf = config.get('pdf.max_images_per_pdf', 25)
    caption_provider = config.get('pdf.caption_provider', 'ollama')
    caption_model = config.get('pdf.caption_model', 'llava')
    ollama_host = config.get('llm.ollama_host', 'http://localhost:11434')
    
    try:
        # 创建图片提取器
        image_extractor = ImageExtractor(
            output_dir=image_output_dir,
            max_images_per_pdf=max_images_per_pdf
        )
        
        # 创建 VLM
        vlm = VisionLanguageModel(
            provider=caption_provider,
            model=caption_model,
            ollama_host=ollama_host
        )
        
        # 创建多模态抽取器
        return MultimodalExtractor(image_extractor, vlm)
    
    except Exception as e:
        logger.error(f"多模态抽取器初始化失败: {e}")
        return None


if __name__ == "__main__":
    # 测试多模态抽取
    import sys
    
    # 配置
    test_config = {
        'pdf.enable_image_captions': True,
        'pdf.image_output_dir': './output/test_images',
        'pdf.max_images_per_pdf': 5,
        'pdf.caption_provider': 'ollama',
        'pdf.caption_model': 'llava',  # 或 'qwen2-vl'
        'llm.ollama_host': 'http://localhost:11434'
    }
    
    # 创建抽取器
    extractor = create_multimodal_extractor(test_config)
    
    if extractor:
        # 测试 PDF (需要提供真实路径)
        if len(sys.argv) > 1:
            test_pdf = sys.argv[1]
            
            print(f"\n=== 测试多模态抽取: {test_pdf} ===")
            image_chunks = extractor.extract_from_pdf(test_pdf)
            
            print(f"\n提取到 {len(image_chunks)} 个图片块:")
            for chunk in image_chunks:
                print(f"\n[{chunk['chunk_id']}] 页码: {chunk['page']}")
                print(f"描述: {chunk['text'][:200]}...")
        else:
            print("用法: python multimodal_extractor.py <PDF文件路径>")
    else:
        print("多模态抽取器初始化失败")
