#!/bin/bash
# 检查处理进度

echo "=== 处理进度检查 ==="
echo ""

# 检查输出文件
if [ -f "output/concepts_enhanced.csv" ]; then
    CONCEPTS=$(wc -l < output/concepts_enhanced.csv)
    echo "✓ 已提取概念: $CONCEPTS 行"
fi

if [ -f "output/relationships_enhanced.csv" ]; then
    RELATIONS=$(wc -l < output/relationships_enhanced.csv)
    echo "✓ 已提取关系: $RELATIONS 行"
fi

# 检查日志
if [ -f "output/kg_builder.log" ]; then
    echo ""
    echo "=== 最近日志 ==="
    tail -20 output/kg_builder.log | grep -E "(Processing|Extracted|chunks)"
fi

echo ""
echo "=== Ollama 状态 ==="
curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | head -5

echo ""
echo "提示: 按 Ctrl+C 停止当前处理"
