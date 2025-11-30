"""
OCR处理模块
支持扫描版PDF的文本提取和图表识别
"""

import os
import fitz  # PyMuPDF
from PIL import Image
import io
from typing import Dict, List, Tuple, Optional
from logger_config import get_logger

logger = get_logger('OCRProcessor')

# OCR 依赖作为可选
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
    logger.info("OCR功能可用 (pytesseract)")
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR功能不可用，请安装: pip install pytesseract pdf2image pillow")

# paddleocr 作为备选OCR引擎
try:
    from paddleocr import PaddleOCR
    PADDLE_OCR_AVAILABLE = True
    logger.info("PaddleOCR可用（推荐用于中文）")
except ImportError:
    PADDLE_OCR_AVAILABLE = False


class OCRProcessor:
    """扫描版PDF的OCR文本提取处理器
    
    使用场景：
    - 扫描版PDF（图片形式PDF）
    - 图片中的文字识别
    - 图表中的文字提取
    
    支持的OCR引擎：
    - Tesseract: 开源OCR，适合英文和简单中文
    - PaddleOCR: 百度开源，中文识别精度高（推荐）
    """
    
    def __init__(self, ocr_engine: str = 'tesseract', lang: str = 'chi_sim+eng'):
        """初始化OCR处理器
        
        Args:
            ocr_engine: OCR引擎 ('tesseract' 或 'paddle')
            lang: 识别语言 (tesseract格式: 'chi_sim+eng' 中英混合)
        
        注意：
        - Tesseract需要安装语言包：sudo apt-get install tesseract-ocr-chi-sim
        - PaddleOCR会自动下载模型文件，首次运行较慢
        """
        self.logger = get_logger('OCRProcessor')
        self.ocr_engine = ocr_engine
        self.lang = lang
        
        # 初始化OCR引擎
        if ocr_engine == 'paddle' and PADDLE_OCR_AVAILABLE:
            try:
                self.paddle_ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
                self.logger.info("PaddleOCR初始化成功")
            except Exception as e:
                self.logger.error(f"PaddleOCR初始化失败: {e}")
                self.paddle_ocr = None
        else:
            self.paddle_ocr = None
        
        if ocr_engine == 'tesseract' and not OCR_AVAILABLE:
            self.logger.error("Tesseract未安装，OCR功能不可用")
    
    def is_scanned_pdf(self, pdf_path: str, sample_pages: int = 3) -> bool:
        """检测PDF是否为扫描版（通过文本量和图像数判断）
        
        Args:
            pdf_path: PDF文件路径
            sample_pages: 采样检查的页数（默认3页，避免遍历所有页）
        
        Returns:
            True=扫描版，需要OCR；False=文本版，可直接提取
        
        判断标准：
        - 平均每页文本 < 50字符 且 存在图像 = 扫描版
        - 文本版PDF一般每页有数百到数千字符
        """
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            # 采样检查
            pages_to_check = min(sample_pages, total_pages)
            text_length_sum = 0
            image_count = 0
            
            for page_num in range(pages_to_check):
                page = doc[page_num]
                
                # 检查文本长度
                text = page.get_text()
                text_length_sum += len(text.strip())
                
                # 检查图像数量
                image_list = page.get_images()
                image_count += len(image_list)
            
            doc.close()
            
            # 判断标准：平均每页文本<50字符 且 存在图像
            # 这个阈值是经验值，可能需要根据实际情况调整
            avg_text_length = text_length_sum / pages_to_check
            
            is_scanned = avg_text_length < 50 and image_count > 0
            
            self.logger.info(f"PDF检测: {os.path.basename(pdf_path)}")
            self.logger.info(f"  平均文本长度: {avg_text_length:.0f} 字符/页")
            self.logger.info(f"  图像数量: {image_count} 个")
            self.logger.info(f"  判定为: {'扫描版' if is_scanned else '文本版'}")
            
            return is_scanned
        
        except Exception as e:
            self.logger.error(f"检测PDF类型失败: {pdf_path}, 错误: {e}")
            return False
    
    def extract_text_with_tesseract(self, pdf_path: str) -> str:
        """使用Tesseract OCR提取扫描版PDF的文本
        
        Args:
            pdf_path: PDF文件路径
        
        Returns:
            提取的文本（多页合并）
        
        处理流程：
        1. 将PDF转换为图像（dpi=300，高清模式）
        2. 逐页进行OCR识别
        3. 合并所有页面的文本
        
        性能：速度较慢，大文件可能需要数分钟
        """
        if not OCR_AVAILABLE:
            self.logger.error("Tesseract不可用")
            return ""
        
        try:
            self.logger.info(f"使用Tesseract OCR提取: {os.path.basename(pdf_path)}")
            
            # 将PDF转换为图像
            images = convert_from_path(pdf_path, dpi=300)
            
            all_text = []
            for i, image in enumerate(images, 1):
                self.logger.info(f"  处理第 {i}/{len(images)} 页...")
                
                # OCR识别
                text = pytesseract.image_to_string(image, lang=self.lang)
                
                if text.strip():
                    all_text.append(text.strip())
            
            result = '\n\n'.join(all_text)
            self.logger.info(f"OCR提取完成: {len(result)} 字符")
            
            return result
        
        except Exception as e:
            self.logger.error(f"Tesseract OCR失败: {pdf_path}, 错误: {e}")
            return ""
    
    def extract_text_with_paddleocr(self, pdf_path: str) -> str:
        """使用PaddleOCR提取扫描版PDF的文本
        
        Args:
            pdf_path: PDF文件路径
        
        Returns:
            提取的文本
        """
        if not self.paddle_ocr:
            self.logger.error("PaddleOCR不可用")
            return ""
        
        try:
            self.logger.info(f"使用PaddleOCR提取: {os.path.basename(pdf_path)}")
            
            # 将PDF转换为图像
            images = convert_from_path(pdf_path, dpi=300)
            
            all_text = []
            for i, image in enumerate(images, 1):
                self.logger.info(f"  处理第 {i}/{len(images)} 页...")
                
                # 转换为numpy数组
                import numpy as np
                img_array = np.array(image)
                
                # OCR识别
                result = self.paddle_ocr.ocr(img_array, cls=True)
                
                # 提取文本
                if result and result[0]:
                    page_text = []
                    for line in result[0]:
                        if len(line) >= 2:
                            text = line[1][0]  # 文本内容
                            conf = line[1][1]  # 置信度
                            if conf > 0.5:  # 只保留置信度>0.5的
                                page_text.append(text)
                    
                    if page_text:
                        all_text.append('\n'.join(page_text))
            
            result = '\n\n'.join(all_text)
            self.logger.info(f"PaddleOCR提取完成: {len(result)} 字符")
            
            return result
        
        except Exception as e:
            self.logger.error(f"PaddleOCR失败: {pdf_path}, 错误: {e}")
            return ""
    
    def extract_text_from_scanned_pdf(self, pdf_path: str) -> str:
        """从扫描版PDF提取文本（自动选择最佳OCR引擎）
        
        Args:
            pdf_path: PDF文件路径
        
        Returns:
            提取的文本
        """
        # 优先使用PaddleOCR（中文识别更好）
        if self.ocr_engine == 'paddle' and self.paddle_ocr:
            return self.extract_text_with_paddleocr(pdf_path)
        
        # 回退到Tesseract
        if OCR_AVAILABLE:
            return self.extract_text_with_tesseract(pdf_path)
        
        self.logger.error("没有可用的OCR引擎")
        return ""
    
    def extract_images_from_pdf(self, pdf_path: str, output_dir: str = None) -> List[str]:
        """从PDF中提取所有图像
        
        Args:
            pdf_path: PDF文件路径
            output_dir: 图像输出目录
        
        Returns:
            提取的图像文件路径列表
        """
        if output_dir is None:
            output_dir = "./output/extracted_images"
        
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            doc = fitz.open(pdf_path)
            image_paths = []
            
            pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_idx, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # 保存图像
                    image_filename = f"{pdf_name}_p{page_num+1}_img{img_idx+1}.{image_ext}"
                    image_path = os.path.join(output_dir, image_filename)
                    
                    with open(image_path, "wb") as img_file:
                        img_file.write(image_bytes)
                    
                    image_paths.append(image_path)
            
            doc.close()
            
            self.logger.info(f"从 {os.path.basename(pdf_path)} 提取了 {len(image_paths)} 个图像")
            
            return image_paths
        
        except Exception as e:
            self.logger.error(f"提取图像失败: {pdf_path}, 错误: {e}")
            return []
    
    def extract_text_from_image(self, image_path: str) -> str:
        """从图像文件提取文本
        
        Args:
            image_path: 图像文件路径
        
        Returns:
            提取的文本
        """
        if not OCR_AVAILABLE:
            return ""
        
        try:
            # 使用Tesseract
            text = pytesseract.image_to_string(Image.open(image_path), lang=self.lang)
            return text.strip()
        except Exception as e:
            self.logger.error(f"图像OCR失败: {image_path}, 错误: {e}")
            return ""
    
    def extract_tables_from_pdf(self, pdf_path: str) -> List[Dict]:
        """提取PDF中的表格（需要camelot或tabula）
        
        Args:
            pdf_path: PDF文件路径
        
        Returns:
            表格数据列表
        """
        tables = []
        
        # 尝试使用camelot
        try:
            import camelot
            
            self.logger.info(f"使用Camelot提取表格: {os.path.basename(pdf_path)}")
            camelot_tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
            
            for i, table in enumerate(camelot_tables):
                tables.append({
                    'page': table.page,
                    'data': table.df,
                    'text': table.df.to_string(),
                    'method': 'camelot'
                })
            
            self.logger.info(f"  提取了 {len(tables)} 个表格")
            return tables
        
        except ImportError:
            self.logger.debug("Camelot未安装")
        except Exception as e:
            self.logger.warning(f"Camelot提取失败: {e}")
        
        # 尝试使用tabula
        try:
            import tabula
            
            self.logger.info(f"使用Tabula提取表格: {os.path.basename(pdf_path)}")
            tabula_tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
            
            for i, table_df in enumerate(tabula_tables):
                tables.append({
                    'page': i + 1,
                    'data': table_df,
                    'text': table_df.to_string(),
                    'method': 'tabula'
                })
            
            self.logger.info(f"  提取了 {len(tables)} 个表格")
            return tables
        
        except ImportError:
            self.logger.debug("Tabula未安装")
        except Exception as e:
            self.logger.warning(f"Tabula提取失败: {e}")
        
        return tables
    
    def process_pdf_with_ocr(
        self,
        pdf_path: str,
        force_ocr: bool = False,
        extract_images: bool = False,
        extract_tables: bool = False
    ) -> Dict[str, any]:
        """完整的PDF OCR处理流程
        
        Args:
            pdf_path: PDF文件路径
            force_ocr: 是否强制使用OCR（即使是文本版PDF）
            extract_images: 是否提取图像
            extract_tables: 是否提取表格
        
        Returns:
            处理结果字典
        """
        result = {
            'filename': os.path.basename(pdf_path),
            'text': '',
            'is_scanned': False,
            'images': [],
            'tables': [],
            'method': 'unknown'
        }
        
        # 1. 检测是否为扫描版
        is_scanned = self.is_scanned_pdf(pdf_path)
        result['is_scanned'] = is_scanned
        
        # 2. 提取文本
        if is_scanned or force_ocr:
            # 使用OCR
            result['text'] = self.extract_text_from_scanned_pdf(pdf_path)
            result['method'] = 'ocr'
        else:
            # 常规提取
            try:
                doc = fitz.open(pdf_path)
                text_parts = []
                for page in doc:
                    text_parts.append(page.get_text())
                doc.close()
                result['text'] = '\n'.join(text_parts)
                result['method'] = 'text'
            except Exception as e:
                self.logger.error(f"文本提取失败: {e}")
        
        # 3. 提取图像
        if extract_images:
            result['images'] = self.extract_images_from_pdf(pdf_path)
        
        # 4. 提取表格
        if extract_tables:
            result['tables'] = self.extract_tables_from_pdf(pdf_path)
        
        return result


class ImageAnalyzer:
    """图像分析器（用于图表、示意图等的分析）"""
    
    def __init__(self):
        """初始化图像分析器"""
        self.logger = get_logger('ImageAnalyzer')
        
        # 检查是否有可用的视觉模型
        self.vision_model = None
        
        # 尝试加载 CLIP 模型（可选）
        try:
            from transformers import CLIPProcessor, CLIPModel
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.logger.info("CLIP视觉模型已加载")
        except ImportError:
            self.logger.debug("CLIP模型不可用")
        except Exception as e:
            self.logger.warning(f"CLIP模型加载失败: {e}")
    
    def classify_image(self, image_path: str, categories: List[str]) -> Tuple[str, float]:
        """分类图像内容
        
        Args:
            image_path: 图像路径
            categories: 候选类别列表
        
        Returns:
            (最可能的类别, 置信度)
        """
        if not self.clip_processor or not self.clip_model:
            self.logger.warning("视觉模型不可用，无法分类图像")
            return ("unknown", 0.0)
        
        try:
            import torch
            from PIL import Image
            
            image = Image.open(image_path)
            
            # 准备输入
            inputs = self.clip_processor(
                text=categories,
                images=image,
                return_tensors="pt",
                padding=True
            )
            
            # 推理
            with torch.no_grad():
                outputs = self.clip_model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)
            
            # 获取最可能的类别
            max_idx = probs.argmax().item()
            confidence = probs[0][max_idx].item()
            category = categories[max_idx]
            
            self.logger.info(f"图像分类: {os.path.basename(image_path)} -> {category} ({confidence:.2f})")
            
            return (category, confidence)
        
        except Exception as e:
            self.logger.error(f"图像分类失败: {image_path}, 错误: {e}")
            return ("unknown", 0.0)
    
    def detect_chart_type(self, image_path: str) -> str:
        """检测图表类型
        
        Args:
            image_path: 图像路径
        
        Returns:
            图表类型 (bar_chart, line_chart, pie_chart, table, diagram, photo, other)
        """
        categories = [
            "a bar chart",
            "a line chart", 
            "a pie chart",
            "a table",
            "a diagram or flowchart",
            "a photograph",
            "other image"
        ]
        
        category, confidence = self.classify_image(image_path, categories)
        
        # 映射到简化类型
        type_map = {
            "a bar chart": "bar_chart",
            "a line chart": "line_chart",
            "a pie chart": "pie_chart",
            "a table": "table",
            "a diagram or flowchart": "diagram",
            "a photograph": "photo",
            "other image": "other"
        }
        
        return type_map.get(category, "other")
    
    def extract_text_from_chart(self, image_path: str) -> str:
        """从图表中提取文本信息
        
        Args:
            image_path: 图像路径
        
        Returns:
            提取的文本
        """
        if not OCR_AVAILABLE:
            return ""
        
        try:
            # 使用OCR提取图表中的文字
            text = pytesseract.image_to_string(
                Image.open(image_path),
                lang='chi_sim+eng'
            )
            
            return text.strip()
        
        except Exception as e:
            self.logger.error(f"图表文本提取失败: {image_path}, 错误: {e}")
            return ""


class HybridPDFProcessor:
    """混合PDF处理器（结合常规提取和OCR）"""
    
    def __init__(self, use_ocr: bool = True, ocr_engine: str = 'tesseract'):
        """初始化混合处理器
        
        Args:
            use_ocr: 是否启用OCR
            ocr_engine: OCR引擎类型
        """
        self.logger = get_logger('HybridPDFProcessor')
        self.use_ocr = use_ocr
        
        if use_ocr:
            self.ocr_processor = OCRProcessor(ocr_engine=ocr_engine)
        else:
            self.ocr_processor = None
            self.logger.info("OCR功能已禁用")
    
    def extract_text(self, pdf_path: str) -> str:
        """智能提取PDF文本（自动选择方法）
        
        Args:
            pdf_path: PDF文件路径
        
        Returns:
            提取的文本
        """
        if not self.use_ocr or not self.ocr_processor:
            # 常规提取
            return self._extract_text_normal(pdf_path)
        
        # 检测PDF类型
        is_scanned = self.ocr_processor.is_scanned_pdf(pdf_path)
        
        if is_scanned:
            # 扫描版，使用OCR
            self.logger.info(f"检测为扫描版，使用OCR: {os.path.basename(pdf_path)}")
            return self.ocr_processor.extract_text_from_scanned_pdf(pdf_path)
        else:
            # 文本版，常规提取
            self.logger.info(f"检测为文本版，使用常规提取: {os.path.basename(pdf_path)}")
            return self._extract_text_normal(pdf_path)
    
    def _extract_text_normal(self, pdf_path: str) -> str:
        """常规文本提取
        
        Args:
            pdf_path: PDF文件路径
        
        Returns:
            提取的文本
        """
        try:
            doc = fitz.open(pdf_path)
            text_parts = []
            
            for page in doc:
                text = page.get_text()
                if text.strip():
                    text_parts.append(text)
            
            doc.close()
            
            return '\n\n'.join(text_parts)
        
        except Exception as e:
            self.logger.error(f"常规提取失败: {pdf_path}, 错误: {e}")
            return ""
    
    def extract_with_images_and_tables(
        self,
        pdf_path: str,
        extract_images: bool = True,
        extract_tables: bool = True
    ) -> Dict[str, any]:
        """完整提取（文本+图像+表格）
        
        Args:
            pdf_path: PDF文件路径
            extract_images: 是否提取图像
            extract_tables: 是否提取表格
        
        Returns:
            完整提取结果
        """
        result = {
            'filename': os.path.basename(pdf_path),
            'text': self.extract_text(pdf_path),
            'images': [],
            'tables': [],
            'image_texts': []
        }
        
        if not self.ocr_processor:
            return result
        
        # 提取图像
        if extract_images:
            image_paths = self.ocr_processor.extract_images_from_pdf(pdf_path)
            result['images'] = image_paths
            
            # 从图像中提取文本
            analyzer = ImageAnalyzer()
            for img_path in image_paths:
                img_text = analyzer.extract_text_from_chart(img_path)
                if img_text:
                    result['image_texts'].append(img_text)
        
        # 提取表格
        if extract_tables:
            tables = self.ocr_processor.extract_tables_from_pdf(pdf_path)
            result['tables'] = tables
            
            # 将表格内容添加到文本中
            for table in tables:
                if 'text' in table:
                    result['text'] += f"\n\n[表格]\n{table['text']}\n"
        
        return result


if __name__ == "__main__":
    # 测试OCR处理器
    print("测试OCR处理器...")
    
    if OCR_AVAILABLE:
        print("Tesseract 可用")
    else:
        print("Tesseract 不可用")
    
    if PADDLE_OCR_AVAILABLE:
        print("PaddleOCR 可用")
    else:
        print("PaddleOCR 不可用")
    
    # 测试PDF类型检测
    test_pdf = "./文献/JItW6-1762148810582-中国森林保护学科发展历程研究_曾凡勇.pdf"
    if os.path.exists(test_pdf):
        ocr = OCRProcessor()
        is_scanned = ocr.is_scanned_pdf(test_pdf)
        print(f"\n测试文件: {test_pdf}")
        print(f"是否扫描版: {is_scanned}")
    else:
        print(f"\n测试文件不存在: {test_pdf}")
    
   