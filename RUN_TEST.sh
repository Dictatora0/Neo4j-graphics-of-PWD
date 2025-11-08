#!/bin/bash
# 松材线虫病知识图谱构建系统 - 快速测试脚本

echo "=========================================="
echo "  松材线虫病知识图谱构建系统 v1.1"
echo "  快速测试脚本"
echo "=========================================="
echo ""

# 检查Python版本
echo "1. 检查Python版本..."
python3 --version || { echo "错误: 未安装Python3"; exit 1; }
echo "✓ Python版本检查通过"
echo ""

# 检查必需依赖
echo "2. 检查必需依赖..."
python3 -c "import fitz" 2>/dev/null || { echo "警告: PyMuPDF未安装，运行: pip install PyMuPDF"; }
python3 -c "import pandas" 2>/dev/null || { echo "警告: pandas未安装，运行: pip install pandas"; }
python3 -c "import numpy" 2>/dev/null || { echo "警告: numpy未安装，运行: pip install numpy"; }
python3 -c "import spacy" 2>/dev/null || { echo "警告: spacy未安装，运行: pip install spacy"; }
echo "✓ 依赖检查完成"
echo ""

# 检查配置文件
echo "3. 检查配置文件..."
if [ ! -f "config/config.yaml" ]; then
    echo "错误: 配置文件不存在: config/config.yaml"
    exit 1
fi
echo "✓ 配置文件存在"
echo ""

# 检查PDF目录
echo "4. 检查PDF目录..."
PDF_DIR="./文献"
if [ ! -d "$PDF_DIR" ]; then
    echo "错误: PDF目录不存在: $PDF_DIR"
    exit 1
fi

PDF_COUNT=$(find "$PDF_DIR" -name "*.pdf" | wc -l)
echo "找到 $PDF_COUNT 个PDF文件"

if [ $PDF_COUNT -eq 0 ]; then
    echo "警告: PDF目录为空"
else
    echo "✓ PDF文件检查通过"
fi
echo ""

# 创建必要目录
echo "5. 创建必要目录..."
mkdir -p output
mkdir -p output/cache
mkdir -p output/neo4j_import
echo "✓ 目录创建完成"
echo ""

# 显示配置信息
echo "=========================================="
echo "  当前配置（config/config.yaml）"
echo "=========================================="
echo "PDF目录: $PDF_DIR"
echo "PDF数量: $PDF_COUNT"
echo ""
echo "推荐配置（首次运行）："
echo "  - enable_cache: true"
echo "  - enable_parallel: true"
echo "  - enable_incremental: false"
echo "  - enable_entity_linking: false"
echo ""

# 询问是否运行
echo "=========================================="
read -p "是否开始构建知识图谱? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消运行"
    exit 0
fi

echo "=========================================="
echo "  开始构建知识图谱..."
echo "=========================================="
echo ""

# 运行主程序
python3 main.py

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "  ✓ 构建完成！"
    echo "=========================================="
    echo ""
    echo "输出文件位置："
    echo "  - 实体: output/entities_clean.csv"
    echo "  - 关系: output/relations_clean.csv"
    echo "  - Neo4j: output/neo4j_import/"
    echo "  - 日志: output/kg_builder.log"
    echo "  - 统计: output/statistics_report.txt"
    echo ""
    echo "下一步："
    echo "  1. 查看统计报告: cat output/statistics_report.txt"
    echo "  2. 导入Neo4j: python output/neo4j_import/import_to_neo4j.py"
    echo "  3. 查看文档: cat COMPLETION_SUMMARY.md"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "  ✗ 构建失败"
    echo "=========================================="
    echo ""
    echo "请检查："
    echo "  1. 日志文件: output/kg_builder.log"
    echo "  2. 错误信息: 查看上方输出"
    echo "  3. 问题排查: cat TROUBLESHOOTING.md"
    echo ""
fi

exit $EXIT_CODE

