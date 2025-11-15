#!/bin/bash

################################################################################
# 完整工作流程自动化脚本
# 功能: 管理 Ollama 服务、安装依赖、运行增强型知识图谱管道
# 使用: bash run_complete_workflow.sh [命令]
################################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
OLLAMA_HOST="http://localhost:11434"
# 从配置文件读取模型名称
OLLAMA_MODEL=$(grep "model:" "$SCRIPT_DIR/config/config.yaml" | head -1 | awk '{print $2}' | tr -d '[:space:]#')
[ -z "$OLLAMA_MODEL" ] && OLLAMA_MODEL="llama3.2:3b"
PYTHON_CMD="python3"
PID_FILE="/tmp/ollama_pwd.pid"

################################################################################
# 辅助函数
################################################################################

print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

################################################################################
# 检查系统环境
################################################################################

check_system() {
    print_header "检查系统环境"
    
    # 检查 Python
    if ! command -v $PYTHON_CMD &> /dev/null; then
        print_error "Python3 未安装"
        exit 1
    fi
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    print_success "Python $PYTHON_VERSION 已安装"
    
    # 检查 Ollama
    if ! command -v ollama &> /dev/null; then
        print_warning "Ollama 未安装"
        print_info "请运行: brew install ollama (macOS) 或访问 https://ollama.ai"
        return 1
    fi
    OLLAMA_VERSION=$(ollama --version 2>&1 | awk '{print $NF}')
    print_success "Ollama $OLLAMA_VERSION 已安装"
    
    # 检查 pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 未安装"
        exit 1
    fi
    print_success "pip3 已安装"
    
    return 0
}

################################################################################
# 虚拟环境管理
################################################################################

setup_venv() {
    print_header "设置 Python 虚拟环境"
    
    if [ ! -d "$VENV_DIR" ]; then
        print_info "创建虚拟环境..."
        $PYTHON_CMD -m venv "$VENV_DIR"
        print_success "虚拟环境已创建"
    else
        print_info "虚拟环境已存在"
    fi
    
    # 激活虚拟环境
    source "$VENV_DIR/bin/activate"
    print_success "虚拟环境已激活"
}

install_dependencies() {
    print_header "安装 Python 依赖"
    
    if [ ! -f "$SCRIPT_DIR/requirements.txt" ]; then
        print_error "requirements.txt 未找到"
        exit 1
    fi
    
    print_info "升级 pip..."
    pip install --upgrade pip setuptools wheel > /dev/null 2>&1
    
    print_info "安装依赖包..."
    pip install -r "$SCRIPT_DIR/requirements.txt"
    
    print_success "依赖安装完成"
}

################################################################################
# Ollama 管理
################################################################################

check_ollama_running() {
    if curl -s "$OLLAMA_HOST/api/tags" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

start_ollama() {
    print_header "启动 Ollama 服务"
    
    # 检查是否已运行
    if check_ollama_running; then
        print_success "Ollama 已在运行"
        return 0
    fi
    
    # 检查是否有旧进程
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            print_info "Ollama 进程已存在 (PID: $OLD_PID)"
            return 0
        fi
    fi
    
    print_info "启动 Ollama 服务..."
    
    # 在后台启动 Ollama
    if command -v ollama &> /dev/null; then
        # macOS 使用 launchctl，Linux 使用 systemctl 或直接运行
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            print_info "使用 macOS 启动方式..."
            ollama serve > /tmp/ollama.log 2>&1 &
            OLLAMA_PID=$!
        else
            # Linux
            print_info "使用 Linux 启动方式..."
            ollama serve > /tmp/ollama.log 2>&1 &
            OLLAMA_PID=$!
        fi
        
        echo $OLLAMA_PID > "$PID_FILE"
        
        # 等待 Ollama 启动
        print_info "等待 Ollama 启动..."
        for i in {1..30}; do
            if check_ollama_running; then
                print_success "Ollama 已启动 (PID: $OLLAMA_PID)"
                sleep 2
                return 0
            fi
            sleep 1
            echo -n "."
        done
        
        print_error "Ollama 启动超时"
        print_info "日志: tail -f /tmp/ollama.log"
        return 1
    else
        print_error "Ollama 命令未找到"
        return 1
    fi
}

stop_ollama() {
    print_header "停止 Ollama 服务"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            print_info "停止 Ollama (PID: $PID)..."
            kill $PID
            rm "$PID_FILE"
            sleep 2
            print_success "Ollama 已停止"
        else
            print_info "Ollama 进程不存在"
            rm "$PID_FILE"
        fi
    else
        print_info "未找到 Ollama 进程文件"
    fi
}

check_ollama_model() {
    print_header "检查 Ollama 模型"
    
    if ! check_ollama_running; then
        print_error "Ollama 服务未运行"
        return 1
    fi
    
    # 获取已安装的模型
    MODELS=$(curl -s "$OLLAMA_HOST/api/tags" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
    
    if echo "$MODELS" | grep -q "$OLLAMA_MODEL"; then
        print_success "模型 '$OLLAMA_MODEL' 已安装"
        return 0
    else
        print_warning "模型 '$OLLAMA_MODEL' 未安装"
        print_info "已安装的模型: $MODELS"
        return 1
    fi
}

pull_ollama_model() {
    print_header "下载 Ollama 模型"
    
    if ! check_ollama_running; then
        print_error "Ollama 服务未运行"
        return 1
    fi
    
    if check_ollama_model; then
        print_info "模型已存在，跳过下载"
        return 0
    fi
    
    print_info "下载模型 '$OLLAMA_MODEL'..."
    print_warning "这可能需要几分钟，取决于网络速度..."
    
    ollama pull "$OLLAMA_MODEL"
    
    if check_ollama_model; then
        print_success "模型下载完成"
        return 0
    else
        print_error "模型下载失败"
        return 1
    fi
}

################################################################################
# 工作流程执行
################################################################################

run_pipeline() {
    print_header "运行增强型知识图谱管道"
    
    # 激活虚拟环境
    source "$VENV_DIR/bin/activate"
    
    # 检查 PDF 文献目录
    if [ ! -d "$SCRIPT_DIR/文献" ] || [ -z "$(ls -A $SCRIPT_DIR/文献)" ]; then
        print_warning "文献目录为空或不存在"
        print_info "请将 PDF 文件放在 $SCRIPT_DIR/文献 目录中"
        return 1
    fi
    
    print_info "开始处理 PDF 文献..."
    cd "$SCRIPT_DIR"
    
    if [ -f "main.py" ]; then
        $PYTHON_CMD main.py
        if [ $? -eq 0 ]; then
            print_success "管道执行完成"
            return 0
        else
            print_error "管道执行失败"
            return 1
        fi
    else
        print_error "main.py 未找到"
        return 1
    fi
}

show_results() {
    print_header "查看结果"
    
    OUTPUT_DIR="$SCRIPT_DIR/output"
    
    if [ ! -d "$OUTPUT_DIR" ]; then
        print_warning "输出目录不存在"
        return 1
    fi
    
    print_info "输出文件:"
    ls -lh "$OUTPUT_DIR"/ 2>/dev/null | tail -n +2 | awk '{print "  " $9 " (" $5 ")"}'
    
    # 显示统计报告
    if [ -f "$OUTPUT_DIR/statistics_report_enhanced.txt" ]; then
        print_info "\n统计报告摘要:"
        head -20 "$OUTPUT_DIR/statistics_report_enhanced.txt"
    fi
}

################################################################################
# 完整工作流程
################################################################################

run_complete_workflow() {
    print_header "完整工作流程开始"
    
    # 1. 检查系统
    if ! check_system; then
        print_error "系统检查失败"
        exit 1
    fi
    
    # 2. 设置虚拟环境
    setup_venv
    
    # 3. 安装依赖
    install_dependencies
    
    # 4. 启动 Ollama
    if ! start_ollama; then
        print_error "Ollama 启动失败"
        exit 1
    fi
    
    # 5. 检查/下载模型
    if ! check_ollama_model; then
        print_info "需要下载模型..."
        if ! pull_ollama_model; then
            print_error "模型下载失败"
            stop_ollama
            exit 1
        fi
    fi
    
    # 6. 运行管道
    if ! run_pipeline; then
        print_error "管道执行失败"
        stop_ollama
        exit 1
    fi
    
    # 7. 显示结果
    show_results
    
    print_header "✓ 完整工作流程完成！"
    print_info "Ollama 服务仍在运行"
    print_info "停止服务: bash $0 stop"
}

################################################################################
# 命令处理
################################################################################

show_usage() {
    cat << EOF
${BLUE}增强型知识图谱系统 - 完整工作流程管理${NC}

${GREEN}使用方法:${NC}
  bash run_complete_workflow.sh [命令]

${GREEN}命令:${NC}
  run              运行完整工作流程（推荐）
  start            启动 Ollama 服务
  stop             停止 Ollama 服务
  status           检查 Ollama 服务状态
  setup            仅安装依赖和设置虚拟环境
  pipeline         仅运行管道（假设 Ollama 已运行）
  check            检查系统环境
  logs             查看 Ollama 日志
  results          查看处理结果
  clean            清理输出文件
  help             显示此帮助信息

${GREEN}示例:${NC}
  # 完整工作流程（推荐新用户）
  bash run_complete_workflow.sh run

  # 仅启动 Ollama 服务
  bash run_complete_workflow.sh start

  # 运行管道（Ollama 已运行）
  bash run_complete_workflow.sh pipeline

  # 停止服务
  bash run_complete_workflow.sh stop

${GREEN}工作流程步骤:${NC}
  1. 检查系统环境 (Python, Ollama, pip)
  2. 设置 Python 虚拟环境
  3. 安装 Python 依赖
  4. 启动 Ollama 服务
  5. 检查/下载 Ollama 模型
  6. 运行增强型知识图谱管道
  7. 显示处理结果

${YELLOW}注意:${NC}
  - 首次运行会下载 Ollama 模型（可能需要几分钟）
  - 请确保 PDF 文献放在 文献/ 目录中
  - Ollama 服务会在后台运行，使用 'stop' 命令停止

EOF
}

# 主命令处理
case "${1:-run}" in
    run)
        run_complete_workflow
        ;;
    start)
        check_system || exit 1
        start_ollama
        check_ollama_model || pull_ollama_model
        ;;
    stop)
        stop_ollama
        ;;
    status)
        print_header "Ollama 服务状态"
        if check_ollama_running; then
            print_success "Ollama 服务正在运行"
            print_info "地址: $OLLAMA_HOST"
            curl -s "$OLLAMA_HOST/api/tags" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | while read model; do
                print_info "  - 模型: $model"
            done
        else
            print_error "Ollama 服务未运行"
            exit 1
        fi
        ;;
    setup)
        check_system || exit 1
        setup_venv
        install_dependencies
        ;;
    pipeline)
        if [ ! -d "$VENV_DIR" ]; then
            print_error "虚拟环境不存在，请先运行: bash $0 setup"
            exit 1
        fi
        if ! check_ollama_running; then
            print_error "Ollama 服务未运行，请先运行: bash $0 start"
            exit 1
        fi
        run_pipeline
        ;;
    check)
        check_system
        ;;
    logs)
        print_header "Ollama 日志"
        if [ -f "/tmp/ollama.log" ]; then
            tail -50 /tmp/ollama.log
        else
            print_warning "日志文件不存在"
        fi
        ;;
    results)
        show_results
        ;;
    clean)
        print_header "清理输出文件"
        if [ -d "$SCRIPT_DIR/output" ]; then
            print_info "删除 output 目录..."
            rm -rf "$SCRIPT_DIR/output"
            print_success "清理完成"
        else
            print_info "输出目录不存在"
        fi
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        print_error "未知命令: $1"
        echo ""
        show_usage
        exit 1
        ;;
esac

exit 0
