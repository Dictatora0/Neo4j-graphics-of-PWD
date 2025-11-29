#!/bin/bash
# 知识图谱构建启动脚本 - 使用正确的 Python 环境

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 设置 HuggingFace 环境变量
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_OFFLINE=1  # 强制离线模式
export TRANSFORMERS_OFFLINE=1  # 禁用联网检查
echo "✓ 已设置 HuggingFace 离线模式" >&2

# 使用已安装依赖的 Python 3.10.13
PYTHON_BIN="$HOME/.pyenv/versions/3.10.13/bin/python"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║        松材线虫病知识图谱构建系统 v2.5                                  ║"
echo "║        启动中...                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# 检查 Python 是否存在
if [ ! -f "$PYTHON_BIN" ]; then
    echo -e "${YELLOW}⚠️  Python 3.10.13 未找到，尝试使用系统 Python${NC}"
    PYTHON_BIN="python3"
fi

# 显示使用的 Python
echo -e "${BLUE}使用的 Python:${NC} $PYTHON_BIN"
$PYTHON_BIN --version
echo ""

# 检查进度
if [ -f "output/checkpoints/.progress.json" ]; then
    echo -e "${GREEN}✓${NC} 发现 checkpoint，将从断点继续"
    processed=$($PYTHON_BIN -c "import json; print(len(json.load(open('output/checkpoints/.progress.json'))['processed_chunks']))" 2>/dev/null || echo "?")
    if [ "$processed" != "?" ]; then
        echo -e "  已处理块数: $processed"
    fi
    echo ""
fi

# 运行管道
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}启动安全模式管道...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "提示:"
echo "  • 按 Ctrl+C 可安全退出并保存进度"
echo "  • 在另一个终端运行 './monitor.sh' 查看进度"
echo "  • 日志文件: output/kg_builder.log"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 执行主程序
exec "$PYTHON_BIN" enhanced_pipeline_safe.py "$@"
