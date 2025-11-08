#!/bin/bash
# 安装脚本

echo "=================================="
echo "松材线虫病知识图谱构建系统 v1.1"
echo "安装依赖包"
echo "=================================="
echo ""

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"

# 创建虚拟环境（可选）
read -p "是否创建虚拟环境? (y/n): " create_venv
if [ "$create_venv" = "y" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✓ 虚拟环境已创建并激活"
fi

# 升级pip
echo ""
echo "升级pip..."
pip install --upgrade pip

# 安装核心依赖
echo ""
echo "安装核心依赖包..."
pip install PyMuPDF pandas numpy tqdm pyyaml spacy jieba scikit-learn yake neo4j

# 询问是否安装可选依赖
echo ""
read -p "是否安装 KeyBERT（关键词提取，推荐）? (y/n): " install_keybert
if [ "$install_keybert" = "y" ]; then
    echo "安装 KeyBERT..."
    pip install keybert sentence-transformers huggingface-hub
fi

echo ""
read -p "是否安装 OCR 支持（处理扫描版PDF）? (y/n): " install_ocr
if [ "$install_ocr" = "y" ]; then
    echo "安装 OCR 依赖..."
    pip install pytesseract pdf2image Pillow
    
    echo ""
    echo "⚠️  还需要安装 Tesseract OCR 引擎:"
    echo "  macOS: brew install tesseract"
    echo "  Ubuntu: sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim"
    echo "  Windows: https://github.com/UB-Mannheim/tesseract/wiki"
fi

echo ""
read -p "是否安装 PaddleOCR（更好的中文OCR，推荐）? (y/n): " install_paddle
if [ "$install_paddle" = "y" ]; then
    echo "安装 PaddleOCR..."
    pip install paddlepaddle paddleocr
fi

# 下载spaCy模型
echo ""
echo "下载spaCy中文模型..."
python3 -m spacy download zh_core_web_sm

echo ""
echo "下载spaCy英文模型..."
python3 -m spacy download en_core_web_sm

# 创建必要目录
echo ""
echo "创建目录结构..."
mkdir -p output
mkdir -p output/extracted_texts
mkdir -p output/neo4j_import
mkdir -p output/cache
mkdir -p config

echo ""
echo "=================================="
echo "✓ 安装完成！"
echo "=================================="
echo ""
echo "已安装的功能:"
echo "  ✓ 核心功能（PDF提取、实体识别、关系抽取）"
[ "$install_keybert" = "y" ] && echo "  ✓ KeyBERT 关键词提取"
[ "$install_ocr" = "y" ] && echo "  ✓ OCR 支持"
[ "$install_paddle" = "y" ] && echo "  ✓ PaddleOCR 中文OCR"

echo ""
echo "运行程序:"
echo "  python3 main.py"
echo ""
echo "配置文件:"
echo "  config/config.yaml - 系统配置"
echo "  config/domain_dict.json - 领域词典"
echo "  config/stopwords.txt - 停用词列表"
echo ""

