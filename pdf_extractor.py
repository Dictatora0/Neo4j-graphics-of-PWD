"""
PDF文本提取模块（Layout-Aware增强版）
使用智能文档解析工具提取PDF内容，解决乱序和表格丢失问题
支持结构化分块和精准参考文献剔除

整体处理流程(从原始 PDF 到清洗后的纯文本):
1) `extract_from_directory` 遍历目录下所有 `.pdf` → 逐个调用 `extract_text_from_pdf`；
2) `extract_text_from_pdf` 内部按优先级选择解析器:
   - 优先 Marker(如 GPU 可用) → 其次 pdfplumber → 最后 PyMuPDF(fitz) 基础解析;
3) 解析结果统一转换为结构化章节 `sections` → `_process_sections`:
   - `_remove_header_footer_sections` 剔除页眉/页脚;
   - `_remove_references` 剔除参考文献尾部;
   - 合并标题+正文并调用 `clean_text` 做控制字符/空行清洗;
4) 如启用 OCR 且文本长度 < 500, 认为可能是扫描版 PDF → 调用 `OCRProcessor` 尝试重新提取;
5) 最终得到的纯文本会写入内存缓存(SimpleCache), 供后续重复运行直接复用。
"""

import fitz  # PyMuPDF
import re
import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from tqdm import tqdm
# 移除 cache_manager 依赖（原项目未提供，用简单缓存逻辑替代）
# 移除 parallel_processor 依赖（原项目未提供，简化为串行处理）
import pandas as pd

# 智能文档解析支持
try:
    import marker  # Marker解析库（需要GPU）
    MARKER_AVAILABLE = True
except ImportError:
    MARKER_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# OCR支持（可选）
try:
    from ocr_processor import OCRProcessor
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


# 内置日志配置函数
def _get_logger(name: Optional[str] = None) -> logging.Logger:
    """内置日志配置，替代 logger_config.get_logger"""
    logger = logging.getLogger(name or __name__)
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    return logger


# 简化缓存类（替代 CacheManager，避免依赖缺失）
class SimpleCache:
    def __init__(self):
        self.cache = {}
    
    def get_pdf_cache(self, pdf_path: str) -> Optional[str]:
        return self.cache.get(pdf_path)
    
    def set_pdf_cache(self, pdf_path: str, text: str):
        self.cache[pdf_path] = text


class PDFExtractor:
    """Layout-Aware PDF文本提取器

    特点:
    - 解析优先级: Marker(结构+Markdown) > pdfplumber(文本+表格) > PyMuPDF(基础文本);
    - 在结构化层面对页眉/页脚与参考文献做剔除, 输出更接近“正文语料”；
    - 可选 OCR 回退, 对扫描版 PDF 再做一次文本提取尝试;
    - 内置简单缓存, 避免对同一 PDF 反复解析。
    """
    
    def __init__(self, use_cache: bool = True, enable_parallel: bool = False,  # 禁用并行（无依赖）
                 max_workers: int = None, enable_ocr: bool = False, 
                 ocr_engine: str = 'tesseract', use_marker: bool = True):
        """
        Args:
            use_cache: 是否使用缓存（用内置 SimpleCache 替代）
            enable_parallel: 是否启用并行处理（默认禁用，无依赖）
            max_workers: 并行进程数（无用，保留参数兼容）
            enable_ocr: 是否启用OCR（用于扫描版PDF）
            ocr_engine: OCR引擎 ('tesseract' 或 'paddle')
            use_marker: 是否使用Marker进行智能解析（需要GPU）
        """
        # 这里不依赖全局 logger_config，而是使用模块内的简易 logger
        self.logger = _get_logger(__name__)
        # 简单内存缓存：同一 PDF 第二次解析时可以直接复用结果，节省时间
        self.cache = SimpleCache() if use_cache else None
        # 并行相关参数仅保留接口兼容，目前统一走串行路径
        self.enable_parallel = enable_parallel  # 强制禁用，避免依赖
        
        # 智能解析配置 - 新增GPU检测
        self.use_marker = use_marker and MARKER_AVAILABLE and self._check_gpu()
        if self.use_marker:
            self.logger.info("启用Marker进行Layout-Aware解析（GPU可用）")
        elif PDFPLUMBER_AVAILABLE:
            self.logger.info("使用pdfplumber进行表格提取和优化解析")
        else:
            self.logger.warning("未检测到pdfplumber，表格提取功能受限")
        
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
        
        # 结构化解析相关配置
        self.reference_keywords = [
            '参考文献', 'References', 'REFERENCES', '引用文献',
            'Bibliography', 'Works Cited', '文献引用'
        ]
        self.header_levels = ['# ', '## ', '### ', '#### ', '##### ', '###### ']  # Markdown标题格式
        self.metadata_keywords = ['作者', '单位', '收稿', '基金项目', '责任编辑']
        
        if self.cache:
            self.logger.info("PDF缓存已启用（内置简单缓存）")
        if self.enable_parallel:
            self.logger.warning("并行处理依赖 parallel_processor，已自动禁用")

    def _check_gpu(self) -> bool:
        """检查GPU是否可用（支持Marker）"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            self.logger.warning("未检测到PyTorch，无法使用GPU加速")
            return False
        except Exception as e:
            self.logger.warning(f"GPU检测失败: {e}")
            return False
    
    def _convert_table_to_text(self, table: List[List[str]]) -> str:
        """将表格数据转换为自然语言描述"""
        if not table or len(table) < 2:
            return ""
            
        # 尝试识别表头
        header = table[0]
        rows = table[1:]
        
        # 简单表格转换为描述性文本
        table_text = []
        for row in rows:
            row_desc = []
            for col_idx, cell in enumerate(row):
                if col_idx < len(header) and header[col_idx] and cell:
                    row_desc.append(f"{header[col_idx]}为{cell}")
            if row_desc:
                table_text.append("；".join(row_desc) + "。")
        
        # 如果转换结果太短，尝试其他格式
        if len(table_text) < max(2, len(rows)//3):
            df = pd.DataFrame(table)
            return f"表格内容：{df.to_string()}\n"
        
        return "\n".join(table_text) + "\n"
    
    def _parse_with_marker(self, pdf_path: str) -> Tuple[str, List[Dict]]:
        """使用Marker进行智能解析（保留结构信息）"""
        try:
            # 生成Markdown和结构化元数据
            markdown, metadata = marker.convert(pdf_path)
            
            # 提取段落结构信息
            sections = []
            current_section = {
                'level': 0,
                'title': '',
                'content': [],
                'page': 0
            }
            
            for line in markdown.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # 识别标题级别
                header_level = None
                for i, level_prefix in enumerate(self.header_levels):
                    if line.startswith(level_prefix):
                        header_level = i + 1
                        title = line[len(level_prefix):].strip()
                        break
                        
                if header_level is not None:
                    # 保存当前章节
                    if current_section['content'] or current_section['title']:
                        sections.append(current_section)
                    # 开始新章节
                    current_section = {
                        'level': header_level,
                        'title': title,
                        'content': [],
                        'page': self._get_page_for_content(metadata, line)  # 从metadata获取页码
                    }
                else:
                    current_section['content'].append(line)
            
            # 添加最后一个章节
            if current_section['content'] or current_section['title']:
                sections.append(current_section)
                
            return markdown, sections
            
        except Exception as e:
            # Marker 依赖较多（GPU/模型等），失败时不终止流程而是回退到 pdfplumber
            self.logger.error(f"Marker解析失败: {e}，将回退到pdfplumber")
            return self._parse_with_pdfplumber(pdf_path)
    
    def _parse_with_pdfplumber(self, pdf_path: str) -> Tuple[str, List[Dict]]:
        """使用pdfplumber进行解析（优化表格提取）"""
        if not PDFPLUMBER_AVAILABLE:
            return self._parse_with_fitz(pdf_path)
            
        sections = []
        full_text = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # 提取页面元素（优化布局顺序）
                    elements = []
                    
                    # 提取文本段落（优化位置参数）
                    text = page.extract_text(x_tolerance=5, y_tolerance=3)
                    if text:
                        elements.append({
                            'type': 'text',
                            'content': text,
                            'page': page_num
                        })
                    
                    # 提取表格并转换为文本
                    tables = page.extract_tables()
                    for table in tables:
                        table_text = self._convert_table_to_text(table)
                        if table_text:
                            elements.append({
                                'type': 'table',
                                'content': table_text,
                                'page': page_num
                            })
                    
                    # 构建页面章节
                    page_section = {
                        'level': 0,
                        'title': f'Page {page_num}',
                        'content': [elem['content'] for elem in elements],
                        'page': page_num
                    }
                    sections.append(page_section)
                    full_text.extend([elem['content'] for elem in elements])
            
            return '\n\n'.join(full_text), sections
            
        except Exception as e:
            self.logger.error(f"pdfplumber解析失败: {e}，将回退到基础解析")
            return self._parse_with_fitz(pdf_path)
    
    def _parse_with_fitz(self, pdf_path: str) -> Tuple[str, List[Dict]]:
        """使用PyMuPDF进行基础解析"""
        try:
            doc = fitz.open(pdf_path)
            sections = []
            full_text = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text:
                    full_text.append(text)
                    sections.append({
                        'level': 0,
                        'title': f'Page {page_num + 1}',
                        'content': [text],
                        'page': page_num + 1
                    })
            
            doc.close()
            return '\n\n'.join(full_text), sections
            
        except Exception as e:
            self.logger.error(f"基础解析失败: {e}")
            return "", []
    
    def _get_page_for_content(self, metadata: Dict, content: str) -> int:
        """从metadata中获取内容所在页码（简化实现）"""
        # 实际实现需要根据marker的metadata格式进行调整
        return metadata.get('page', 1)
    
    def clean_text(self, text: str) -> str:
        """清洗文本内容

        当前做的清洗步骤包括:
        - 去除不可见控制字符(ASCII 0x00-0x1F 中常见的格式控制符);
        - 统一行结束符为 `\n`, 兼容 Windows/Unix 不同换行风格;
        - 将 3 行以上连续空行压缩为最多 2 行, 避免段落间出现大片空白。
        """
        # 移除特殊字符
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)
        # 统一行结束符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # 移除多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
    
    def _is_header_footer(self, text: str, section: Dict) -> bool:
        """基于结构信息判断是否为页眉页脚"""
        # 页眉页脚通常在页面顶部/底部且不属于任何章节
        if section['level'] == 0 and section['title'].startswith('Page'):
            # 检查常见页眉页脚模式
            patterns = [
                re.compile(r'^第?\s*\d+\s*页$', re.IGNORECASE),
                re.compile(r'^Page\s+\d+', re.IGNORECASE),
                re.compile(r'^\d+\s*/\s*\d+$'),
                re.compile(r'^\s*版权所有'),
                re.compile(r'^\s*Copyright', re.IGNORECASE)
            ]
            return any(pattern.match(text.strip()) for pattern in patterns)
        return False
    
    def _remove_header_footer_sections(self, sections: List[Dict]) -> List[Dict]:
        """基于结构信息移除页眉页脚章节"""
        cleaned_sections = []
        for section in sections:
            # 过滤页眉页脚内容
            cleaned_content = []
            for content in section['content']:
                if not self._is_header_footer(content, section):
                    cleaned_content.append(content)
            
            if cleaned_content:
                cleaned_section = section.copy()
                cleaned_section['content'] = cleaned_content
                cleaned_sections.append(cleaned_section)
        
        return cleaned_sections
    
    def _find_reference_section_index(self, sections: List[Dict]) -> int:
        """找到参考文献部分的起始索引"""
        for idx, section in enumerate(sections):
            # 检查章节标题
            if any(keyword in section['title'] for keyword in self.reference_keywords):
                return idx
            
            # 检查章节内容
            if section['content']:
                combined_content = ' '.join(section['content'][:2])  # 检查前两段
                if any(keyword in combined_content for keyword in self.reference_keywords):
                    return idx
        
        return -1
    
    def _remove_references(self, sections: List[Dict]) -> List[Dict]:
        """移除参考文献部分"""
        ref_idx = self._find_reference_section_index(sections)
        if ref_idx != -1:
            self.logger.info(f"检测到参考文献部分，从第{ref_idx + 1}节开始移除")
            return sections[:ref_idx]
        return sections
    
    def split_sentences(self, text: str) -> List[str]:
        """按中英文标点切分句子"""
        text = re.sub(r'\s+', ' ', text).strip()
        if not text:
            return []
        # 改进的句子切分正则，处理更多情况
        sentences = re.split(r'(?<=[。！？!?；;\.])\s+', text)
        result: List[str] = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            # 调整短句过滤阈值，保留表格转换的短句
            if len(sentence) < 5:
                continue
            result.append(sentence)
        return result
    
    def _process_sections(self, sections: List[Dict]) -> str:
        """处理结构化章节，生成最终文本"""
        # 1. 移除页眉页脚
        cleaned_sections = self._remove_header_footer_sections(sections)
        
        # 2. 移除参考文献
        cleaned_sections = self._remove_references(cleaned_sections)
        
        # 3. 合并内容并清洗
        full_content = []
        for section in cleaned_sections:
            # 添加章节标题（如果有）
            if section['title'] and section['level'] > 0:
                full_content.append(f"{'#' * section['level']} {section['title']}")
            
            # 添加章节内容
            full_content.extend(section['content'])
        
        combined_text = '\n\n'.join(full_content)
        return self.clean_text(combined_text)
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """从单个 PDF 文件中提取清洗后的文本（Layout-Aware增强版）

        关键步骤概览:
        1. 命中缓存: 若 SimpleCache 中已有该 pdf_path 的结果, 直接返回;
        2. 解析选择: 按 Marker → pdfplumber → PyMuPDF 的顺序选择可用解析器获取 `sections`;
        3. 结构化清洗: `_process_sections` 统一做页眉/页脚剔除、参考文献裁剪与 Markdown 标题合并;
        4. OCR 回退: 若启用 OCR 且文本长度 < 500 字符, 认为可能是扫描版 PDF, 调用 `OCRProcessor` 覆盖文本;
        5. 写入缓存并记录日志: 将最终文本写入缓存, 输出字符数统计, 便于后续调优。
        """
        # 检查缓存：长文献多次调试时可以直接命中，避免重复解析
        if self.cache:
            cached_text = self.cache.get_pdf_cache(pdf_path)
            if cached_text:
                self.logger.info(f"使用缓存: {os.path.basename(pdf_path)}")
                return cached_text
        
        self.logger.info(f"开始提取: {os.path.basename(pdf_path)}")
        
        try:
            # 选择解析方式：优先使用 Marker，其次 pdfplumber，最后回退到 PyMuPDF 基础解析
            if self.use_marker:
                raw_text, sections = self._parse_with_marker(pdf_path)
            elif PDFPLUMBER_AVAILABLE:
                raw_text, sections = self._parse_with_pdfplumber(pdf_path)
            else:
                raw_text, sections = self._parse_with_fitz(pdf_path)
            
            # 处理结构化内容：统一做页眉页脚/参考文献剔除和 Markdown 合并
            processed_text = self._process_sections(sections)
            
            # 如果提取的文本很少，认为可能是扫描版 PDF，再退一步尝试 OCR
            if self.enable_ocr and self.ocr_processor and len(processed_text) < 500:
                self.logger.info(f"文本量过少（{len(processed_text)}字符），可能为扫描版PDF，尝试OCR...")
                try:
                    ocr_text = self.ocr_processor.extract_text_from_pdf(pdf_path)
                    if ocr_text and len(ocr_text) > len(processed_text):
                        self.logger.info(f"OCR提取成功: {len(ocr_text)} 字符")
                        processed_text = ocr_text
                    else:
                        self.logger.warning("OCR未能提取到更多文本")
                except Exception as e:
                    self.logger.warning(f"OCR提取失败: {e}")
            
            # 保存到缓存
            if self.cache and processed_text:
                self.cache.set_pdf_cache(pdf_path, processed_text)
            
            self.logger.info(f"提取完成: {os.path.basename(pdf_path)}, {len(processed_text)} 字符")
            return processed_text
        
        except Exception as e:
            self.logger.error(f"提取失败: {pdf_path}, 错误: {str(e)}")
            return ""
    
    def extract_from_directory(self, directory: str) -> Dict[str, str]:
        """从目录中提取所有PDF的文本（简化为串行处理）"""
        pdf_texts = {}
        
        # 获取所有PDF文件
        pdf_files = [f for f in os.listdir(directory) if f.lower().endswith('.pdf')]
        
        self.logger.info(f"找到 {len(pdf_files)} 个PDF文件")
        print(f"找到 {len(pdf_files)} 个PDF文件")
        
        # 强制使用串行处理（无 parallel_processor 依赖）
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
    # 示例：使用Marker解析（需要GPU）
    extractor = PDFExtractor(use_marker=True)
    pdf_texts = extractor.extract_from_directory("./文献")
    extractor.save_extracted_texts(pdf_texts, "./output/extracted_texts")