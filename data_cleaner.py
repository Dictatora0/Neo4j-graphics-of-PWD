"""
数据清洗模块（Markdown结构适配版）
针对Layout-Aware解析生成的Markdown格式内容进行结构化清洗
支持智能分块、参考文献剔除、表格文本优化
"""

import re
import json
import os
import logging
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
from tqdm import tqdm
# 移除logger_config依赖，内置日志配置
import jieba
import zhconv

# 尝试导入中文分句工具
try:
    import pysbd
    SBD_AVAILABLE = True
except ImportError:
    SBD_AVAILABLE = False

try:
    from zhsegment import segment_sentences  # 自定义中文分句工具
    ZHSEGMENT_AVAILABLE = True
except ImportError:
    ZHSEGMENT_AVAILABLE = False


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


class MarkdownDataCleaner:
    """适配Markdown结构的PDF文本清洗器"""
    
    def __init__(self, 
                 remove_references: bool = True,
                 clean_tables: bool = True,
                 normalize_chinese: bool = True,
                 remove_headers_footers: bool = True,
                 min_sentence_length: int = 5,
                 max_sentence_length: int = 500):
        """
        初始化清洗器
        Args:
            remove_references: 是否移除参考文献部分
            clean_tables: 是否优化表格转换的文本
            normalize_chinese: 是否归一化中文（繁转简、全半角等）
            remove_headers_footers: 是否移除页眉页脚
            min_sentence_length: 最小句子长度（字符数）
            max_sentence_length: 最大句子长度（字符数）
        """
        self.logger = _get_logger(__name__)
        
        # 配置参数
        self.remove_references = remove_references
        self.clean_tables = clean_tables
        self.normalize_chinese = normalize_chinese
        self.remove_headers_footers = remove_headers_footers
        self.min_sentence_length = min_sentence_length
        self.max_sentence_length = max_sentence_length
        
        # 参考文献关键词（多语言支持）
        self.reference_keywords = {
            'zh': ['参考文献', '引用文献', '文献引用', '参考资料'],
            'en': ['References', 'REFERENCES', 'Bibliography', 'Works Cited', 
                   'Cited Works', 'Literature Cited', 'Citations']
        }
        
        # 页眉页脚特征模式
        self.header_footer_patterns = [
            # 页码模式
            re.compile(r'^\s*第?\s*\d+\s*页\s*$', re.IGNORECASE),
            re.compile(r'^\s*Page\s+\d+(/\d+)?\s*$', re.IGNORECASE),
            re.compile(r'^\s*\d+\s*/\s*\d+\s*$'),
            # 版权/水印模式
            re.compile(r'^\s*版权所有\s*@?\s*\d{4}', re.IGNORECASE),
            re.compile(r'^\s*Copyright\s*@?\s*\d{4}', re.IGNORECASE),
            re.compile(r'^\s*All Rights Reserved\s*$', re.IGNORECASE),
            # 期刊/出版社信息
            re.compile(r'^\s*[\u4e00-\u9fa5]+学报\s*$'),
            re.compile(r'^\s*[\u4e00-\u9fa5]+出版社\s*$'),
            re.compile(r'^\s*Journal\s+of\s+[\w\s]+$', re.IGNORECASE),
            # 空行/短行
            re.compile(r'^\s*$'),
            re.compile(r'^\s*[-=*_]{3,}\s*$')
        ]
        
        # Markdown结构特征
        self.markdown_patterns = {
            'headers': re.compile(r'^(#{1,6})\s+(.+)$'),  # 标题
            'tables': re.compile(r'\|.*\|'),  # 原始表格
            'code_blocks': re.compile(r'```[\s\S]*?```'),  # 代码块
            'math_blocks': re.compile(r'\$\$[\s\S]*?\$\$'),  # 数学公式块
            'inline_math': re.compile(r'\$[^$]+\$'),  # 行内公式
            'links': re.compile(r'\[([^\]]+)\]\([^)]+\)'),  # 链接
            'images': re.compile(r'!\[([^\]]*)\]\([^)]+\)'),  # 图片
        }
        
        # 初始化分句工具
        self._init_sentence_segmenter()
        
        # 加载停用词
        self.stopwords = self._load_stopwords()
        
        self.logger.info("Markdown数据清洗器初始化完成")
    
    def _init_sentence_segmenter(self):
        """初始化分句工具"""
        if SBD_AVAILABLE:
            self.zh_segmenter = pysbd.Segmenter(language="zh", clean=False)
            self.en_segmenter = pysbd.Segmenter(language="en", clean=False)
            self.logger.info("使用pysbd进行分句")
        elif ZHSEGMENT_AVAILABLE:
            self.logger.info("使用自定义中文分句工具")
        else:
            self.logger.warning("未检测到专业分句工具，将使用基础正则分句")
    
    def _load_stopwords(self) -> Set[str]:
        """加载停用词表"""
        stopwords = set()
        try:
            stopword_files = [
                'stopwords_zh.txt',
                os.path.join(os.path.dirname(__file__), 'stopwords_zh.txt')
            ]
            
            for filepath in stopword_files:
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for line in f:
                            word = line.strip()
                            if word:
                                stopwords.add(word)
                    break
        except Exception as e:
            self.logger.warning(f"加载停用词失败: {e}")
        
        return stopwords
    
    def normalize_text(self, text: str) -> str:
        """文本归一化"""
        if not text:
            return ""
        
        # 1. 繁转简
        if self.normalize_chinese:
            text = zhconv.convert(text, 'zh-cn')
        
        # 2. 全半角转换
        text = self._full_to_half(text)
        
        # 3. 统一空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 4. 移除控制字符
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        # 5. 移除特殊符号（保留常用标点）
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s，。！？；：""''（）()【】[]《》<>、·…—\-+=]', '', text)
        
        return text.strip()
    
    def _full_to_half(self, text: str) -> str:
        """全角转半角"""
        result = []
        for char in text:
            code = ord(char)
            # 全角空格
            if code == 0x3000:
                result.append(' ')
            # 全角字符（除空格）
            elif 0xFF01 <= code <= 0xFF5E:
                result.append(chr(code - 0xFEE0))
            else:
                result.append(char)
        return ''.join(result)
    
    def _is_reference_section(self, line: str, line_num: int, total_lines: int) -> bool:
        """判断是否为参考文献部分"""
        # 参考文献通常出现在文档末尾（后20%）
        if line_num / total_lines < 0.8:
            return False
        
        # 检查关键词
        line_lower = line.lower()
        for lang_keywords in self.reference_keywords.values():
            for keyword in lang_keywords:
                if keyword in line:
                    return True
        
        # 检查参考文献格式特征
        ref_patterns = [
            re.compile(r'^\s*\[\d+\]\s+'),  # [1] 引用格式
            re.compile(r'^\s*\d+\.\s+[A-Z][a-zA-Z]+\s+,'),  # 英文参考文献格式
            re.compile(r'^\s*[\u4e00-\u9fa5]+\s+，\s*[\u4e00-\u9fa5]+'),  # 中文参考文献格式
        ]
        
        return any(pattern.match(line) for pattern in ref_patterns)
    
    def _clean_table_text(self, text: str) -> str:
        """优化表格转换的文本"""
        if not self.clean_tables or not text:
            return text
        
        # 移除表格标记
        text = re.sub(r'^\|.*\|$', '', text, flags=re.MULTILINE)
        
        # 清理表格转换后的冗余描述
        text = re.sub(r'表格内容：\s*', '', text)
        
        # 优化表格数据描述
        # 匹配 "X为Y；A为B。" 格式
        table_pattern = re.compile(r'([^；。]+)为([^；。]+)(；|。)')
        matches = table_pattern.findall(text)
        
        # 如果匹配到表格数据，重构更自然的描述
        if matches and len(matches) > 1:
            table_data = []
            for key, value, sep in matches:
                if key.strip() and value.strip():
                    table_data.append(f"{key.strip()}是{value.strip()}")
            
            if table_data:
                text = "，".join(table_data) + "。"
        
        return text
    
    def _is_header_footer(self, line: str) -> bool:
        """基于内容特征判断页眉页脚（增强版）"""
        line_stripped = line.strip()
        if len(line_stripped) < 5 or len(line_stripped) > 50:
            return False
        # 结合关键词和模式匹配
        return (any(pattern.match(line_stripped) for pattern in self.header_footer_patterns) or
                any(keyword in line_stripped for keyword in ["第页", "页码", "版权所有", "摘要", "Abstract", "目录"]))
    
    def _remove_header_footer(self, lines: List[str]) -> List[str]:
        """移除页眉页脚"""
        if not self.remove_headers_footers:
            return lines
        
        cleaned_lines = []
        for line in lines:
            line_stripped = line.strip()
            
            # 检查是否匹配页眉页脚模式
            if self._is_header_footer(line_stripped):
                continue
            
            if len(line_stripped) > 0:
                cleaned_lines.append(line)
        
        return cleaned_lines
    
    def _remove_references(self, lines: List[str]) -> List[str]:
        """移除参考文献部分"""
        if not self.remove_references:
            return lines
        
        # 找到参考文献起始位置
        ref_start_idx = -1
        total_lines = len(lines)
        
        for idx, line in enumerate(lines):
            if self._is_reference_section(line, idx, total_lines):
                ref_start_idx = idx
                break
        
        # 如果找到参考文献部分，截断
        if ref_start_idx != -1:
            self.logger.info(f"检测到参考文献，从第{ref_start_idx+1}行开始移除")
            return lines[:ref_start_idx]
        
        return lines
    
    def _parse_markdown_structure(self, text: str) -> Tuple[List[Dict], str]:
        """解析Markdown结构，提取结构化信息"""
        lines = text.split('\n')
        structured_content = []
        cleaned_text_lines = []
        
        current_section = {
            'type': 'text',
            'level': 0,
            'title': '',
            'content': [],
            'line_numbers': []
        }
        
        for line_num, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 跳过空行
            if not line_stripped:
                continue
            
            # 识别Markdown标题
            header_match = self.markdown_patterns['headers'].match(line_stripped)
            if header_match:
                # 保存当前章节
                if current_section['content']:
                    structured_content.append(current_section)
                    cleaned_text_lines.append(' '.join(current_section['content']))
                
                # 开始新章节
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                current_section = {
                    'type': 'header',
                    'level': level,
                    'title': title,
                    'content': [],
                    'line_numbers': [line_num]
                }
                cleaned_text_lines.append(f"【标题】{title}")  # 标记标题类型
                continue
            
            # 识别表格行
            if self.markdown_patterns['tables'].match(line_stripped) and "-|" not in line_stripped:
                # 转换表格为文本描述
                table_text = self._clean_table_text(line_stripped)
                if table_text:
                    current_section['content'].append(table_text)
                    current_section['line_numbers'].append(line_num)
                    cleaned_text_lines.append(table_text)
                continue
            
            # 移除代码块、数学公式等非核心内容
            if (self.markdown_patterns['code_blocks'].match(line_stripped) or
                self.markdown_patterns['math_blocks'].match(line_stripped)):
                continue
            
            # 清理行内元素（链接、图片、行内公式）
            clean_line = line_stripped
            clean_line = self.markdown_patterns['links'].sub(r'\1', clean_line)  # 保留链接文本
            clean_line = self.markdown_patterns['images'].sub('', clean_line)   # 移除图片
            clean_line = self.markdown_patterns['inline_math'].sub('', clean_line)  # 移除行内公式
            
            if clean_line:
                current_section['content'].append(clean_line)
                current_section['line_numbers'].append(line_num)
                cleaned_text_lines.append(clean_line)
        
        # 添加最后一个章节
        if current_section['content']:
            structured_content.append(current_section)
        
        return structured_content, '\n'.join(cleaned_text_lines)
    
    def segment_sentences(self, text: str) -> List[str]:
        """智能分句（支持中英文）"""
        if not text:
            return []
        
        # 使用专业分句工具
        if SBD_AVAILABLE:
            # 中文分句
            if re.search(r'[\u4e00-\u9fa5]', text):
                sentences = self.zh_segmenter.segment(text)
            # 英文分句
            else:
                sentences = self.en_segmenter.segment(text)
        elif ZHSEGMENT_AVAILABLE:
            sentences = segment_sentences(text)  # 修复语法错误：移除多余空格
        else:
            # 基础正则分句
            sentences = self._basic_sentence_segmentation(text)
        
        # 过滤和清洗句子
        filtered_sentences = []
        for sent in sentences:
            sent = self.normalize_text(sent)
            
            # 过滤长度不符合要求的句子
            if len(sent) < self.min_sentence_length or len(sent) > self.max_sentence_length:
                continue
            
            # 过滤纯数字/纯符号的句子
            if re.match(r'^\s*[\d\s]+$', sent):
                continue
            
            # 过滤停用词占比过高的句子
            if self._stopword_ratio_too_high(sent):
                continue
            
            filtered_sentences.append(sent)
        
        return filtered_sentences
    
    def _basic_sentence_segmentation(self, text: str) -> List[str]:
        """基础正则分句"""
        # 中文分句
        text = re.sub(r'([。！？；])', r'\1|||', text)
        # 英文分句
        text = re.sub(r'([.!?;])\s', r'\1|||', text)
        
        sentences = [s.strip() for s in text.split('|||') if s.strip()]
        return sentences
    
    def _stopword_ratio_too_high(self, text: str) -> bool:
        """检查停用词占比是否过高"""
        if not text or not self.stopwords:
            return False
        
        words = jieba.lcut(text)
        if len(words) < 3:
            return False
        
        stopword_count = sum(1 for word in words if word in self.stopwords)
        ratio = stopword_count / len(words)
        
        return ratio > 0.8
    
    def clean_markdown_text(self, markdown_text: str) -> Dict[str, any]:
        """
        清洗Markdown格式的PDF文本
        Returns:
            dict: 包含清洗后的文本、句子列表、结构化信息等
        """
        if not markdown_text:
            return {
                'raw_text': '',
                'cleaned_text': '',
                'sentences': [],
                'structured_content': [],
                'metadata': {'cleaned': False, 'error': '空输入'}
            }
        
        try:
            self.logger.info("开始Markdown文本清洗")
            
            # 1. 按行拆分
            lines = markdown_text.split('\n')
            
            # 2. 移除页眉页脚
            lines = self._remove_header_footer(lines)
            
            # 3. 移除参考文献
            lines = self._remove_references(lines)
            
            # 4. 解析Markdown结构（基于标题和表格标记）
            structured_content, cleaned_text = self._parse_markdown_structure('\n'.join(lines))
            
            # 5. 最终文本归一化
            cleaned_text = self.normalize_text(cleaned_text)
            
            # 6. 分句处理
            sentences = self.segment_sentences(cleaned_text)
            
            # 7. 生成元数据
            metadata = {
                'cleaned': True,
                'original_lines': len(markdown_text.split('\n')),
                'cleaned_lines': len(lines),
                'sentence_count': len(sentences),
                'char_count': len(cleaned_text),
                'sections_count': len(structured_content)
            }
            
            self.logger.info(f"清洗完成 - 原始行数: {metadata['original_lines']}, "
                             f"清洗后行数: {metadata['cleaned_lines']}, "
                             f"有效句子数: {metadata['sentence_count']}")
            
            return {
                'raw_text': markdown_text,
                'cleaned_text': cleaned_text,
                'sentences': sentences,
                'structured_content': structured_content,
                'metadata': metadata
            }
        
        except Exception as e:
            self.logger.error(f"清洗失败: {e}", exc_info=True)
            return {
                'raw_text': markdown_text,
                'cleaned_text': '',
                'sentences': [],
                'structured_content': [],
                'metadata': {'cleaned': False, 'error': str(e)}
            }
    
    def clean_text_file(self, input_path: str, output_path: str) -> bool:
        """清洗单个文本文件"""
        try:
            # 读取文件
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 清洗
            result = self.clean_markdown_text(content)
            
            if not result['metadata']['cleaned']:
                self.logger.error(f"文件清洗失败: {input_path}")
                return False
            
            # 保存清洗结果
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)
            
            # 保存主文本
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result['cleaned_text'])
            
            # 保存句子列表（JSON格式）
            sentences_path = output_path.replace('.txt', '_sentences.json')
            with open(sentences_path, 'w', encoding='utf-8') as f:
                json.dump(result['sentences'], f, ensure_ascii=False, indent=2)
            
            # 保存元数据
            meta_path = output_path.replace('.txt', '_metadata.json')
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(result['metadata'], f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"文件清洗完成: {input_path} -> {output_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"处理文件失败 {input_path}: {e}", exc_info=True)
            return False
    
    def clean_directory(self, input_dir: str, output_dir: str) -> Dict[str, bool]:
        """批量清洗目录下的文本文件"""
        input_path = Path(input_dir)
        if not input_path.exists():
            self.logger.error(f"输入目录不存在: {input_dir}")
            return {}
        
        # 查找所有文本文件
        text_files = list(input_path.glob('*.txt')) + list(input_path.glob('*.md'))
        
        if not text_files:
            self.logger.warning(f"未找到文本文件: {input_dir}")
            return {}
        
        # 批量处理
        results = {}
        for file_path in tqdm(text_files, desc="清洗文件"):
            # 构建输出路径
            rel_path = file_path.relative_to(input_path)
            output_path = Path(output_dir) / rel_path
            
            # 清洗文件
            success = self.clean_text_file(str(file_path), str(output_path))
            results[str(file_path)] = success
        
        # 统计结果
        success_count = sum(1 for v in results.values() if v)
        fail_count = len(results) - success_count
        
        self.logger.info(f"批量清洗完成 - 成功: {success_count}, 失败: {fail_count}")
        return results


# 示例使用
if __name__ == "__main__":
    # 初始化清洗器
    cleaner = MarkdownDataCleaner(
        remove_references=True,
        clean_tables=True,
        normalize_chinese=True,
        min_sentence_length=6,
        max_sentence_length=400
    )
    
    # 单文件清洗示例
    input_file = "./output/extracted_texts/sample.pdf.txt"
    output_file = "./output/cleaned_texts/sample_cleaned.txt"
    
    if os.path.exists(input_file):
        cleaner.clean_text_file(input_file, output_file)
    
    # 批量清洗示例
    # input_dir = "./output/extracted_texts"
    # output_dir = "./output/cleaned_texts"
    # cleaner.clean_directory(input_dir, output_dir)


# 向后兼容别名
DataCleaner = MarkdownDataCleaner