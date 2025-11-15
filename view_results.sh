#!/bin/bash
# 查看处理结果

echo "=== 知识图谱处理结果 ==="
echo ""

if [ -f "output/concepts.csv" ]; then
    CONCEPTS=$(tail -n +2 output/concepts.csv | wc -l)
    echo "✓ 概念数量: $CONCEPTS"
    echo ""
    echo "前10个概念:"
    head -11 output/concepts.csv | column -t -s,
fi

echo ""
echo "================================"
echo ""

if [ -f "output/relationships.csv" ]; then
    RELATIONS=$(tail -n +2 output/relationships.csv | wc -l)
    echo "✓ 关系数量: $RELATIONS"
    echo ""
    echo "前10个关系:"
    head -11 output/relationships.csv | column -t -s,
fi

echo ""
echo "================================"
echo ""
echo "完整文件位置:"
echo "  - output/concepts.csv"
echo "  - output/relationships.csv"
echo "  - output/entities_clean.csv"
echo "  - output/relations_clean.csv"
echo "  - output/neo4j_import/"
echo "  - output/statistics_report.txt"
