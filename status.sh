#!/bin/bash
# 快速查看当前状态

PYTHON_BIN="$HOME/.pyenv/versions/3.10.13/bin/python"

if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

# 颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo " 📊 知识图谱构建状态"
echo "════════════════════════════════════════════════════════════════════════"
echo ""

# 检查进度文件
if [ -f "output/checkpoints/.progress.json" ]; then
    echo -e "${GREEN}✓${NC} Checkpoint 进度:"
    
    if command -v jq &> /dev/null; then
        processed=$(jq -r '.processed_chunks | length' output/checkpoints/.progress.json)
        concepts=$(jq -r '.total_concepts' output/checkpoints/.progress.json)
        relations=$(jq -r '.total_relationships' output/checkpoints/.progress.json)
        last_update=$(jq -r '.last_update' output/checkpoints/.progress.json)
        
        echo "  已处理块数: $processed"
        echo "  概念总数: $concepts"
        echo "  关系总数: $relations"
        echo "  最后更新: ${last_update:0:19}"
    else
        $PYTHON_BIN -c "
import json
with open('output/checkpoints/.progress.json') as f:
    p = json.load(f)
    print(f'  已处理块数: {len(p[\"processed_chunks\"])}')
    print(f'  概念总数: {p[\"total_concepts\"]}')
    print(f'  关系总数: {p[\"total_relationships\"]}')
    print(f'  最后更新: {p[\"last_update\"][:19]}')
" 2>/dev/null || echo "  (无法读取详细信息)"
    fi
else
    echo -e "${YELLOW}⚠${NC} 未找到 checkpoint 文件"
fi

echo ""

# 检查输出文件
echo "📁 输出文件:"
for file in output/concepts.csv output/relationships.csv; do
    if [ -f "$file" ]; then
        size=$(du -h "$file" | awk '{print $1}')
        lines=$(wc -l < "$file")
        echo -e "  ${GREEN}✓${NC} $(basename $file): $size ($lines 行)"
    else
        echo -e "  ${RED}✗${NC} $(basename $file): 不存在"
    fi
done

echo ""

# 检查进程
if pgrep -f "enhanced_pipeline|test_safe" > /dev/null; then
    echo -e "${GREEN}✓${NC} 管道进程: 运行中"
    ps aux | grep -E "enhanced_pipeline|test_safe" | grep -v grep | awk '{printf "  PID: %s, CPU: %s%%, 内存: %s%%\n", $2, $3, $4}' | head -1
else
    echo -e "${YELLOW}⚠${NC} 管道进程: 未运行"
    echo ""
    echo "启动命令:"
    echo "  ./start.sh"
fi

echo ""

# 检查最近错误
if [ -f "output/kg_builder.log" ]; then
    error_count=$(grep -c "ERROR" output/kg_builder.log 2>/dev/null || echo "0")
    if [ "$error_count" -gt 0 ]; then
        echo -e "${RED}⚠${NC} 检测到 $error_count 个错误，最近的错误:"
        grep "ERROR" output/kg_builder.log | tail -3 | while IFS= read -r line; do
            echo "  ${line:0:100}"
        done
    else
        echo -e "${GREEN}✓${NC} 没有错误"
    fi
fi

echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo ""
