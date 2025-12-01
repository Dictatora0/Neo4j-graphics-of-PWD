#!/bin/bash
# 分批处理快速测试脚本

echo "================================"
echo "分批处理功能测试"
echo "================================"
echo ""

# 测试1: 显示帮助
echo "[测试 1/3] 显示帮助信息..."
./start.sh --help
echo ""

# 测试2: 单批测试（5个chunks）
echo "[测试 2/3] 单批测试（5 chunks）..."
echo "按Ctrl+C可中断测试"
read -p "按Enter开始..." 
./start.sh --batch-size 5 --batch-mode single
echo ""

# 测试3: 检查输出
echo "[测试 3/3] 检查输出..."
if [ -f "output/batch_progress.log" ]; then
    echo "✅ 批次日志已创建"
    echo ""
    echo "最近5条日志:"
    tail -5 output/batch_progress.log
else
    echo "❌ 批次日志未创建"
fi
echo ""

if [ -f "output/concepts.csv" ]; then
    lines=$(wc -l < output/concepts.csv)
    echo "✅ 概念文件已创建 ($lines 行)"
else
    echo "⚠️  概念文件未创建（可能还未完成第一批）"
fi
echo ""

echo "================================"
echo "测试完成"
echo "================================"
echo ""
echo "下一步:"
echo "  1. 查看批次日志: cat output/batch_progress.log"
echo "  2. 继续处理: ./start.sh --batch-size 30"
echo "  3. 清理checkpoint: rm -rf output/checkpoints/*"
echo ""
