#!/bin/bash
# 知识图谱构建启动脚本（Shell 版本）

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印横幅
print_banner() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                      ║"
    echo "║        松材线虫病知识图谱构建系统 v2.5                                  ║"
    echo "║        Pine Wilt Disease Knowledge Graph Builder                    ║"
    echo "║                                                                      ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}✗${NC} $1 未安装"
        return 1
    else
        echo -e "${GREEN}✓${NC} $1 已安装"
        return 0
    fi
}

# 环境检查
check_environment() {
    echo "════════════════════════════════════════════════════════════════════════"
    echo " 🔍 环境检查"
    echo "════════════════════════════════════════════════════════════════════════"
    echo ""
    
    local all_ok=true
    
    # 检查 Python
    if check_command python || check_command python3; then
        PYTHON_CMD=$(command -v python3 || command -v python)
        echo "    版本: $($PYTHON_CMD --version)"
    else
        all_ok=false
    fi
    
    # 检查 Ollama
    if check_command ollama; then
        # 检查 Ollama 服务
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Ollama 服务运行中"
        else
            echo -e "${RED}✗${NC} Ollama 服务未运行"
            echo "    启动命令: ollama serve"
            all_ok=false
        fi
    else
        all_ok=false
    fi
    
    # 检查模型
    if command -v ollama &> /dev/null; then
        if ollama list | grep -q "qwen2.5-coder:7b"; then
            echo -e "${GREEN}✓${NC} qwen2.5-coder:7b 已安装"
        else
            echo -e "${YELLOW}⚠${NC} qwen2.5-coder:7b 未安装"
            echo "    安装命令: ollama pull qwen2.5-coder:7b"
        fi
    fi
    
    # 检查 PDF 文件
    if [ -d "文献" ]; then
        pdf_count=$(find 文献 -name "*.pdf" 2>/dev/null | wc -l | tr -d ' ')
        if [ "$pdf_count" -gt 0 ]; then
            echo -e "${GREEN}✓${NC} PDF 文件: $pdf_count 个"
        else
            echo -e "${RED}✗${NC} 未找到 PDF 文件"
            all_ok=false
        fi
    else
        echo -e "${RED}✗${NC} 文献目录不存在"
        all_ok=false
    fi
    
    # 检查输出目录
    if [ ! -d "output" ]; then
        echo -e "${YELLOW}⚠${NC} 输出目录不存在，将自动创建"
        mkdir -p output/checkpoints
    else
        echo -e "${GREEN}✓${NC} 输出目录存在"
    fi
    
    echo ""
    
    if [ "$all_ok" = false ]; then
        return 1
    else
        return 0
    fi
}

# 显示使用说明
show_usage() {
    echo "════════════════════════════════════════════════════════════════════════"
    echo " 💡 使用说明"
    echo "════════════════════════════════════════════════════════════════════════"
    echo ""
    echo "启动方式:"
    echo "  1. 使用 Python 启动器（推荐）:"
    echo "     python run_pipeline.py"
    echo ""
    echo "  2. 使用 Shell 脚本:"
    echo "     bash run.sh"
    echo ""
    echo "  3. 直接运行安全模式:"
    echo "     python enhanced_pipeline_safe.py"
    echo ""
    echo "监控进度:"
    echo "  • 实时日志: tail -f output/kg_builder.log"
    echo "  • 查看进度: cat output/checkpoints/.progress.json"
    echo "  • 监控脚本: bash monitor.sh"
    echo ""
    echo "════════════════════════════════════════════════════════════════════════"
    echo ""
}

# 主函数
main() {
    print_banner
    
    # 环境检查
    if ! check_environment; then
        echo -e "${RED}环境检查失败，请先解决上述问题${NC}"
        echo ""
        show_usage
        exit 1
    fi
    
    echo "════════════════════════════════════════════════════════════════════════"
    echo " 🚀 启动管道"
    echo "════════════════════════════════════════════════════════════════════════"
    echo ""
    echo "使用 Python 启动器（提供更详细的信息）"
    echo ""
    
    # 检查 Python 启动器
    if [ -f "run_pipeline.py" ]; then
        exec python run_pipeline.py "$@"
    else
        echo -e "${YELLOW}run_pipeline.py 不存在，使用直接模式${NC}"
        echo ""
        exec python enhanced_pipeline_safe.py "$@"
    fi
}

# 运行主函数
main "$@"
