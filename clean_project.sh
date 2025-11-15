#!/bin/bash
# 项目清理脚本

echo "=== 项目清理工具 ==="
echo ""

# 显示菜单
echo "请选择清理选项:"
echo "  1. 清理所有输出文件（保留备份）"
echo "  2. 清理缓存文件"
echo "  3. 清理 Neo4j 导入文件"
echo "  4. 清理日志文件"
echo "  5. 清理所有（输出+缓存+日志）"
echo "  6. 仅列出文件大小"
echo ""

if [ -z "$1" ]; then
    read -p "请输入选项 (1-6): " choice
else
    choice=$1
fi

case $choice in
    1)
        echo "清理输出文件..."
        rm -f output/*.csv
        rm -rf output/neo4j_import
        rm -rf output/neo4j_import_enhanced
        rm -f output/*.txt
        echo "✓ 输出文件已清理（备份保留）"
        ;;
    
    2)
        echo "清理缓存文件..."
        rm -rf output/cache
        rm -rf __pycache__
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
        find . -type f -name "*.pyc" -delete 2>/dev/null
        echo "✓ 缓存文件已清理"
        ;;
    
    3)
        echo "清理 Neo4j 导入文件..."
        rm -rf output/neo4j_import
        rm -rf output/neo4j_import_enhanced
        echo "✓ Neo4j 导入文件已清理"
        ;;
    
    4)
        echo "清理日志文件..."
        rm -f output/*.log
        rm -f output/*.log.*
        echo "✓ 日志文件已清理"
        ;;
    
    5)
        echo "清理所有文件..."
        rm -f output/*.csv
        rm -rf output/neo4j_import
        rm -rf output/neo4j_import_enhanced
        rm -f output/*.txt
        rm -rf output/cache
        rm -f output/*.log
        rm -f output/*.log.*
        rm -rf __pycache__
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
        find . -type f -name "*.pyc" -delete 2>/dev/null
        echo "✓ 所有文件已清理（备份保留）"
        ;;
    
    6)
        echo "=== 文件大小统计 ==="
        echo ""
        echo "输出文件:"
        du -sh output/*.csv 2>/dev/null || echo "  无 CSV 文件"
        echo ""
        echo "Neo4j 导入:"
        du -sh output/neo4j_import* 2>/dev/null || echo "  无导入文件"
        echo ""
        echo "缓存:"
        du -sh output/cache 2>/dev/null || echo "  无缓存"
        echo ""
        echo "日志:"
        du -sh output/*.log 2>/dev/null || echo "  无日志"
        echo ""
        echo "备份:"
        du -sh output/neo4j_backups 2>/dev/null || echo "  无备份"
        echo ""
        echo "总计:"
        du -sh output 2>/dev/null
        ;;
    
    *)
        echo "无效选项"
        exit 1
        ;;
esac

echo ""
echo "完成！"
