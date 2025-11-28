"""
PDF文本提取模块
使用PyMuPDF提取PDF正文内容，过滤页眉页脚和参考文献
支持OCR识别扫描版PDF
"""

import fitz  # PyMuPDF
import re
import os
from typing import Dict, List, Optional
from tqdm import tqdm
from logger_config import get_logger
from cache_manager import CacheManager
from parallel_processor import ParallelProcessor
from image_captioner import ImageCaptioner

# OCR支持（可选）
try:
    from ocr_processor import OCRProcessor
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


DEFAULT_IMAGE_PROMPT = (
    "你是一名熟悉松材线虫病的林业病理专家，请用中文描述图像，"
    "涵盖场景、关键实体、实验结论、文字/数值和任何与病害传播、防治、"
    "宿主或媒介相关的细节。"
)


class PDFExtractor:
    """PDF文本提取器"""
    
    def __init__(self, use_cache: bool = True, enable_parallel: bool = True, 
                 max_workers: int = None, enable_ocr: bool = False, ocr_engine: str = 'tesseract',
                 enable_image_captions: bool = False, image_output_dir: str = "./output/pdf_images",
                 max_images_per_pdf: Optional[int] = 25, caption_model: str = "Qwen/Qwen2-VL-7B-Instruct",
                 caption_provider: str = "transformers", caption_prompt: Optional[str] = None,
                 caption_device: Optional[str] = None):
        """
        Args:
            use_cache: 是否使用缓存
            enable_parallel: 是否启用并行处理
            max_workers: 并行进程数
            enable_ocr: 是否启用OCR（用于扫描版PDF）
            ocr_engine: OCR引擎 ('tesseract' 或 'paddle')
        """
        self.logger = get_logger('PDFExtractor')
        self.cache = CacheManager() if use_cache else None
        self.parallel_processor = ParallelProcessor(max_workers) if enable_parallel else None
        
        # OCR支持
        self.enable_ocr = enable_ocr and OCR_AVAILABLE
        if self.enable_ocr:
            try:
                self.ocr_processor = OCRProcessor(ocr_engine=ocr_engine)
                self.logger.info(f"OCR功能已启用: {ocr_engine}")
            except Exception as e:
                self.logger.warning(f"OCR初始化失败: {e}")
                self.ocr_processor = None
                self.enable_ocr = False
        else:
            self.ocr_processor = None
            if enable_ocr and not OCR_AVAILABLE:
                self.logger.warning("OCR功能不可用，请安装OCR依赖")
        
        self.enable_image_captions = enable_image_captions
        self.image_output_dir = image_output_dir
        self.max_images_per_pdf = max_images_per_pdf
        self.caption_model = caption_model
        self.caption_provider = caption_provider
        self.caption_prompt = caption_prompt or DEFAULT_IMAGE_PROMPT
        self.caption_device = caption_device
        self.image_captioner: Optional[ImageCaptioner] = None
        self.image_metadata: Dict[str, List[Dict]] = {}

        if self.enable_image_captions:
            try:
                os.makedirs(self.image_output_dir, exist_ok=True)
                self.image_captioner = ImageCaptioner(
                    model_name=self.caption_model,
                    provider=self.caption_provider,
                    prompt_prefix=self.caption_prompt,
                    device=self.caption_device
                )
                self.logger.info(f"图像描述已启用，模型: {self.caption_model}")
            except Exception as e:
                self.logger.warning(f"图像描述初始化失败，将禁用: {e}")
                self.enable_image_captions = False
                self.image_captioner = None

        self.reference_keywords = [
            '参考文献', 'References', 'REFERENCES', '引用文献',
            'Bibliography', 'Works Cited'
        ]
        self.header_footer_patterns = [
            re.compile(r'^第?\s*\d+\s*页$', re.IGNORECASE),
            re.compile(r'^Page\s+\d+', re.IGNORECASE),
            re.compile(r'^\d+\s*/\s*\d+$'),
            re.compile(r'^\s*版权所有'),
            re.compile(r'^\s*Copyright', re.IGNORECASE)
        ]
        self.metadata_keywords = ['作者', '单位', '收稿', '基金项目', '责任编辑']
        
        if self.cache:
            self.logger.info("PDF缓存已启用")
        if self.parallel_processor:
            self.logger.info(f"并行处理已启用: {self.parallel_processor.max_workers} 个工作进程")
        
    def clean_text(self, text: str) -> str:
        """清洗文本内容"""
        # 移除特殊字符
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)
        # 统一行结束符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        return text

    def remove_headers_and_footers(self, text: str) -> str:
        """尝试移除页眉页脚与噪声行"""
        cleaned_lines: List[str] = []
        for raw_line in text.split('\n'):
            line = raw_line.strip()
            if not line:
                continue
            if any(pattern.match(line) for pattern in self.header_footer_patterns):
                continue
            if len(line) <= 3 and line.isdigit():
                continue
            if any(keyword in line for keyword in self.metadata_keywords):
                continue
            cleaned_lines.append(line)
        return '\n'.join(cleaned_lines)

    def split_sentences(self, text: str) -> List[str]:
        """按中英文标点切分句子"""
        text = re.sub(r'\s+', ' ', text).strip()
        if not text:
            return []
        sentences = re.split(r'(?<=[。！？!?；;\.])\s+', text)
        result: List[str] = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) < 10:
                continue
            result.append(sentence)
        return result
    
    def is_reference_section(self, text: str) -> bool:
        """判断是否为参考文献部分"""
        for keyword in self.reference_keywords:
            if keyword in text[:50]:  # 检查前50个字符
                return True
        return False
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """从PDF中提取文本"""
        # 检查缓存
        if self.cache:
            cached_text = self.cache.get_pdf_cache(pdf_path)
            if cached_text:
                self.logger.info(f"使用缓存: {os.path.basename(pdf_path)}")
                return cached_text
        
        self.logger.info(f"开始提取: {os.path.basename(pdf_path)}")
        
        try:
            doc = fitz.open(pdf_path)
            pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
            full_text: List[str] = []
            reference_started = False
            total_pages = len(doc)
            self.image_metadata[pdf_path] = []
            saved_xrefs = set()
            image_counter = 0
            
            for page_num in range(total_pages):
                page = doc[page_num]
                text = page.get_text()
                
                # 检查是否进入参考文献部分
                if not reference_started and self.is_reference_section(text):
                    reference_started = True
                    continue
                
                # 如果已经进入参考文献部分，跳过
                if reference_started:
                    continue

                page_blocks = page.get_text("dict")
                for block in page_blocks.get("blocks", []):
                    block_type = block.get("type")
                    
                    if block_type == 0:
                        block_text = self._extract_block_text(block)
                        if not block_text.strip():
                            continue
                        cleaned_text = self.clean_text(block_text)
                        cleaned_text = self.remove_headers_and_footers(cleaned_text)
                        sentences = self.split_sentences(cleaned_text)
                        full_text.extend(sentences)
                    
                    elif block_type == 1 and self.enable_image_captions:
                        if self.max_images_per_pdf and image_counter >= self.max_images_per_pdf:
                            continue
                        xref = block.get("xref") or block.get("image")
                        if not xref or xref in saved_xrefs:
                            continue
                        saved_xrefs.add(xref)
                        image_sentence = self._process_image_block(
                            doc=doc,
                            pdf_name=pdf_name,
                            pdf_path=pdf_path,
                            page_num=page_num,
                            block=block,
                            xref=xref,
                            image_counter=image_counter
                        )
                        if image_sentence:
                            full_text.append(image_sentence)
                            image_counter += 1
            
            doc.close()
            result_text = '\n'.join(full_text)
            
            # 如果提取的文本很少，可能是扫描版PDF，尝试OCR
            if self.enable_ocr and self.ocr_processor and len(result_text) < 500:
                self.logger.info(f"文本量过少（{len(result_text)}字符），可能为扫描版PDF，尝试OCR...")
                try:
                    ocr_text = self.ocr_processor.extract_text_from_pdf(pdf_path)
                    if ocr_text and len(ocr_text) > len(result_text):
                        self.logger.info(f"OCR提取成功: {len(ocr_text)} 字符")
                        result_text = ocr_text
                    else:
                        self.logger.warning("OCR未能提取到更多文本")
                except Exception as e:
                    self.logger.warning(f"OCR提取失败: {e}")
            
            # 保存到缓存
            if self.cache and result_text:
                self.cache.set_pdf_cache(pdf_path, result_text)
            
            self.logger.info(f"提取完成: {os.path.basename(pdf_path)}, {len(result_text)} 字符")
            return result_text
        
        except Exception as e:
            self.logger.error(f"提取失败: {pdf_path}, 错误: {str(e)}")
            return ""
    
    def extract_from_directory(self, directory: str) -> Dict[str, str]:
        """从目录中提取所有PDF的文本"""
        pdf_texts = {}
        
        # 获取所有PDF文件
        pdf_files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
        
        self.logger.info(f"找到 {len(pdf_files)} 个PDF文件")
        print(f"找到 {len(pdf_files)} 个PDF文件")
        
        # 判断是否使用并行处理
        if self.parallel_processor and len(pdf_files) >= 3:
            return self._extract_parallel(directory, pdf_files)
        else:
            return self._extract_sequential(directory, pdf_files)
    
    def _extract_sequential(self, directory: str, pdf_files: List[str]) -> Dict[str, str]:
        """串行提取PDF文本"""
        self.logger.info("使用串行处理")
        pdf_texts = {}
        
        for pdf_file in tqdm(pdf_files, desc="提取PDF文本"):
            pdf_path = os.path.join(directory, pdf_file)
            text = self.extract_text_from_pdf(pdf_path)
            if text:
                pdf_texts[pdf_file] = text
                print(f"{pdf_file}: 提取了 {len(text)} 个字符")
            else:
                print(f"提取失败: {pdf_file}")
        
        return pdf_texts
    
    def _extract_parallel(self, directory: str, pdf_files: List[str]) -> Dict[str, str]:
        """并行提取PDF文本"""
        self.logger.info(f"使用并行处理: {self.parallel_processor.max_workers} 个进程")
        
        # 准备PDF路径列表
        pdf_paths = [os.path.join(directory, f) for f in pdf_files]
        
        # 并行处理
        results = self.parallel_processor.process_pdfs_parallel(
            pdf_paths,
            self.extract_text_from_pdf,
            desc="提取PDF文本"
        )
        
        # 构建结果字典
        pdf_texts = {}
        for pdf_file, text in zip(pdf_files, results):
            if text:
                pdf_texts[pdf_file] = text
                print(f"{pdf_file}: 提取了 {len(text)} 个字符")
            else:
                print(f"提取失败: {pdf_file}")
        
        return pdf_texts
    
    def _extract_block_text(self, block: Dict) -> str:
        """从文本块结构中提取文本"""
        lines = []
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = ''.join(span.get("text", "") for span in spans)
            if text.strip():
                lines.append(text)
        return '\n'.join(lines)
    
    def _process_image_block(
        self,
        doc,
        pdf_name: str,
        pdf_path: str,
        page_num: int,
        block: Dict,
        xref: int,
        image_counter: int
    ) -> Optional[str]:
        """保存图像并生成描述"""
        image_path = self._save_image_file(
            doc, pdf_name, page_num, xref, image_counter
        )
        if not image_path:
            return None
        
        caption = self._generate_image_caption(image_path)
        metadata = {
            "page": page_num + 1,
            "image_path": image_path,
            "caption": caption,
            "bbox": block.get("bbox"),
            "xref": xref
        }
        self.image_metadata.setdefault(pdf_path, []).append(metadata)
        
        if caption:
            return f"【图像描述|第{page_num + 1}页】{caption}"
        return None
    
    def _save_image_file(self, doc, pdf_name: str, page_num: int, xref: int, image_counter: int) -> Optional[str]:
        """将 PyMuPDF 图像引用保存为文件"""
        try:
            base_image = doc.extract_image(xref)
            image_bytes = base_image.get("image")
            image_ext = base_image.get("ext", "png")
            image_dir = os.path.join(self.image_output_dir, pdf_name)
            os.makedirs(image_dir, exist_ok=True)
            image_filename = f"{pdf_name}_p{page_num + 1}_img{image_counter + 1}.{image_ext}"
            image_path = os.path.join(image_dir, image_filename)
            with open(image_path, "wb") as img_file:
                img_file.write(image_bytes)
            return image_path
        except Exception as e:
            self.logger.warning(f"保存图像失败 (xref={xref}): {e}")
            return None
    
    def _generate_image_caption(self, image_path: str) -> str:
        """生成图像描述，若模型不可用则回退"""
        caption = ""
        if self.image_captioner:
            try:
                caption = self.image_captioner.caption_image(image_path)
            except Exception as e:
                self.logger.warning(f"图像描述失败 {os.path.basename(image_path)}: {e}")
        
        if not caption and self.ocr_processor:
            caption = self.ocr_processor.extract_text_from_image(image_path)
        
        if not caption:
            caption = f"图像内容详见 {os.path.basename(image_path)}"
        return caption.strip()
    
    def save_extracted_texts(self, pdf_texts: Dict[str, str], output_dir: str):
        """保存提取的文本"""
        os.makedirs(output_dir, exist_ok=True)
        
        for pdf_name, text in pdf_texts.items():
            # 生成文本文件名
            txt_name = pdf_name.replace('.pdf', '.txt')
            txt_path = os.path.join(output_dir, txt_name)
            
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(text)
        
        print(f"\n文本文件已保存到: {output_dir}")


if __name__ == "__main__":
    extractor = PDFExtractor()
    pdf_texts = extractor.extract_from_directory("./文献")
    extractor.save_extracted_texts(pdf_texts, "./output/extracted_texts")
    
    print(f"\n总共提取了 {len(pdf_texts)} 个PDF文件的文本")

