#!/bin/bash
# 内存清理和优化脚本

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    内存清理与优化工具                                  ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# 检查当前内存使用
echo -e "${YELLOW}[1/5] 检查当前系统状态...${NC}"
python3 monitor_memory.py --once

# 询问是否继续
echo ""
read -p "是否继续清理？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

# 重启 Ollama 服务
echo ""
echo -e "${YELLOW}[2/5] 重启 Ollama 服务释放内存...${NC}"
pkill ollama 2>/dev/null
sleep 2
nohup ollama serve > /dev/null 2>&1 &
sleep 3
echo -e "${GREEN}Ollama 服务已重启${NC}"

# 清理临时文件
echo ""
echo -e "${YELLOW}[3/5] 清理临时文件...${NC}"
if [ -d "output/checkpoints" ]; then
    checkpoint_size=$(du -sh output/checkpoints 2>/dev/null | cut -f1)
    echo "  Checkpoint 目录大小: $checkpoint_size"
    read -p "  是否清理 checkpoint？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf output/checkpoints/*
        echo -e "${GREEN}  Checkpoint 已清理${NC}"
    fi
fi

# 清理系统缓存（macOS）
echo ""
echo -e "${YELLOW}[4/5] 清理系统缓存...${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "  执行 purge 命令（需要 sudo）..."
    sudo purge 2>/dev/null && echo -e "${GREEN}  系统缓存已清理${NC}" || echo -e "${RED}  清理失败${NC}"
else
    echo "  跳过（非 macOS 系统）"
fi

# 显示清理后状态
echo ""
echo -e "${YELLOW}[5/5] 检查清理后状态...${NC}"
sleep 2
python3 monitor_memory.py --once

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    内存清理完成                                       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "提示："
echo "  - 现在可以重新运行 ./start.sh"
echo "  - 使用 'python monitor_memory.py' 实时监控资源"
echo "  - 如仍有问题，请查看 MEMORY_OPTIMIZATION.md"
echo ""
