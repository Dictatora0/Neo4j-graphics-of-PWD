#!/bin/bash

###############################################################################
# 知识图谱 Web 应用启动脚本
# 功能：端口冲突检测、自动释放、前后端服务启动
###############################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置
BACKEND_PORT=8000
FRONTEND_PORT=5173
NEO4J_PORT=7687
NEO4J_HTTP_PORT=7474

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_step() {
    echo -e "\n${PURPLE}▶${NC} ${CYAN}$1${NC}\n"
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 未安装"
        return 1
    fi
    return 0
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0  # 端口被占用
    else
        return 1  # 端口空闲
    fi
}

# 获取占用端口的进程信息
get_port_process() {
    local port=$1
    lsof -Pi :$port -sTCP:LISTEN -t 2>/dev/null
}

# 杀死占用端口的进程
kill_port_process() {
    local port=$1
    local process_name=$2
    
    if check_port $port; then
        local pid=$(get_port_process $port)
        if [ -n "$pid" ]; then
            local cmd=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
            log_warning "端口 $port 被进程占用 (PID: $pid, Command: $cmd)"
            log_info "正在自动终止占用进程..."
            
            # 直接杀死进程，不再询问
            if kill -9 $pid 2>/dev/null; then
                log_success "已终止进程 $pid"
                sleep 1
            else
                log_error "无法终止进程 $pid"
                log_error "端口 $port 仍被占用，无法启动 $process_name"
                return 1
            fi
        fi
    fi
    return 0
}

# 检查并清理端口
check_and_cleanup_ports() {
    log_step "检查端口占用情况"
    
    local ports_to_check=(
        "$BACKEND_PORT:后端服务"
        "$FRONTEND_PORT:前端服务"
    )
    
    local has_conflict=false
    
    for port_info in "${ports_to_check[@]}"; do
        IFS=':' read -r port name <<< "$port_info"
        if check_port $port; then
            has_conflict=true
            kill_port_process $port "$name" || return 1
        else
            log_success "端口 $port ($name) 可用"
        fi
    done
    
    if [ "$has_conflict" = false ]; then
        log_success "所有端口检查通过"
    fi
}

# 检查 Neo4j 连接
check_neo4j() {
    log_step "检查 Neo4j 数据库"
    
    if ! check_port $NEO4J_PORT; then
        log_error "Neo4j 未运行 (端口 $NEO4J_PORT)"
        log_info "请先启动 Neo4j 数据库"
        log_info "命令: neo4j start 或 neo4j-desktop"
        return 1
    fi
    
    log_success "Neo4j 正在运行 (端口 $NEO4J_PORT)"
    
    # 检查 HTTP 端口
    if check_port $NEO4J_HTTP_PORT; then
        log_success "Neo4j Browser 可访问: http://localhost:$NEO4J_HTTP_PORT"
    fi
    
    return 0
}

# 检查 Python 环境
check_python() {
    log_step "检查 Python 环境"
    
    if ! check_command python3; then
        log_error "Python3 未安装"
        return 1
    fi
    
    local python_version=$(python3 --version 2>&1 | awk '{print $2}')
    log_info "Python 版本: $python_version"
    
    # 检查后端依赖
    cd "$BACKEND_DIR"
    if [ ! -f "requirements.txt" ]; then
        log_error "未找到 requirements.txt"
        return 1
    fi
    
    log_info "检查 Python 依赖..."
    if ! python3 -c "import fastapi" 2>/dev/null; then
        log_warning "缺少 Python 依赖，正在安装..."
        pip install -q -r requirements.txt || {
            log_error "依赖安装失败"
            return 1
        }
        log_success "Python 依赖安装完成"
    else
        log_success "Python 依赖已安装"
    fi
    
    cd "$SCRIPT_DIR"
    return 0
}

# 检查 Node.js 环境
check_nodejs() {
    log_step "检查 Node.js 环境"
    
    if ! check_command node; then
        log_error "Node.js 未安装"
        return 1
    fi
    
    if ! check_command npm; then
        log_error "npm 未安装"
        return 1
    fi
    
    local node_version=$(node --version)
    local npm_version=$(npm --version)
    log_info "Node.js 版本: $node_version"
    log_info "npm 版本: $npm_version"
    
    # 检查前端依赖
    cd "$FRONTEND_DIR"
    if [ ! -d "node_modules" ]; then
        log_warning "缺少 Node.js 依赖，正在安装..."
        npm install || {
            log_error "依赖安装失败"
            return 1
        }
        log_success "Node.js 依赖安装完成"
    else
        log_success "Node.js 依赖已安装"
    fi
    
    cd "$SCRIPT_DIR"
    return 0
}

# 启动后端服务
start_backend() {
    log_step "启动后端服务"
    
    cd "$BACKEND_DIR"
    
    # 检查环境变量文件
    if [ ! -f ".env" ]; then
        log_warning ".env 文件不存在，从 .env.example 复制"
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_success "已创建 .env 文件"
        fi
    fi
    
    log_info "启动 FastAPI 服务 (端口: $BACKEND_PORT)..."
    
    # 后台启动 uvicorn
    nohup uvicorn app.main:app --reload --port $BACKEND_PORT > /tmp/pwd-backend.log 2>&1 &
    local backend_pid=$!
    
    # 保存 PID
    echo $backend_pid > /tmp/pwd-backend.pid
    
    # 等待服务启动
    sleep 2
    
    # 检查服务是否正常启动
    if check_port $BACKEND_PORT; then
        log_success "后端服务启动成功 (PID: $backend_pid)"
        log_info "API 地址: http://localhost:$BACKEND_PORT"
        log_info "API 文档: http://localhost:$BACKEND_PORT/docs"
        log_info "日志文件: /tmp/pwd-backend.log"
    else
        log_error "后端服务启动失败"
        log_info "查看日志: tail -f /tmp/pwd-backend.log"
        return 1
    fi
    
    cd "$SCRIPT_DIR"
    return 0
}

# 启动前端服务
start_frontend() {
    log_step "启动前端服务"
    
    cd "$FRONTEND_DIR"
    
    # 检查环境变量文件
    if [ ! -f ".env" ]; then
        log_info "创建 .env 文件"
        echo "VITE_API_URL=http://localhost:$BACKEND_PORT" > .env
        log_success "已创建 .env 文件"
    fi
    
    log_info "启动 Vite 开发服务器 (端口: $FRONTEND_PORT)..."
    
    # 后台启动 vite
    nohup npm run dev > /tmp/pwd-frontend.log 2>&1 &
    local frontend_pid=$!
    
    # 保存 PID
    echo $frontend_pid > /tmp/pwd-frontend.pid
    
    # 等待服务启动
    sleep 3
    
    # 检查服务是否正常启动
    if check_port $FRONTEND_PORT; then
        log_success "前端服务启动成功 (PID: $frontend_pid)"
        log_info "应用地址: http://localhost:$FRONTEND_PORT"
        log_info "日志文件: /tmp/pwd-frontend.log"
    else
        log_error "前端服务启动失败"
        log_info "查看日志: tail -f /tmp/pwd-frontend.log"
        return 1
    fi
    
    cd "$SCRIPT_DIR"
    return 0
}

# 显示服务状态
show_status() {
    log_step "服务状态"
    
    echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  🚀 知识图谱 Web 应用已启动                           ${CYAN}║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════════════════════╣${NC}"
    
    if check_port $BACKEND_PORT; then
        echo -e "${CYAN}║${NC}  ${GREEN}✓${NC} 后端服务: http://localhost:$BACKEND_PORT          ${CYAN}║${NC}"
        echo -e "${CYAN}║${NC}    API 文档: http://localhost:$BACKEND_PORT/docs      ${CYAN}║${NC}"
    fi
    
    if check_port $FRONTEND_PORT; then
        echo -e "${CYAN}║${NC}  ${GREEN}✓${NC} 前端应用: http://localhost:$FRONTEND_PORT          ${CYAN}║${NC}"
    fi
    
    if check_port $NEO4J_HTTP_PORT; then
        echo -e "${CYAN}║${NC}  ${GREEN}✓${NC} Neo4j 浏览器: http://localhost:$NEO4J_HTTP_PORT     ${CYAN}║${NC}"
    fi
    
    echo -e "${CYAN}╠════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  停止服务: ./stop.sh                                   ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  查看日志: tail -f /tmp/pwd-*.log                      ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
    echo
}

# 主函数
main() {
    clear
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║     松材线虫病知识图谱 Web 应用启动脚本               ║"
    echo "║     PWD Knowledge Graph Web Application Launcher      ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
    
    # 检查必要条件
    check_neo4j || exit 1
    check_python || exit 1
    check_nodejs || exit 1
    
    # 检查并清理端口
    check_and_cleanup_ports || exit 1
    
    # 启动服务
    start_backend || exit 1
    start_frontend || exit 1
    
    # 显示状态
    show_status
    
    log_success "所有服务已成功启动！"
    log_info "按 Ctrl+C 不会停止服务，请使用 ./stop.sh 停止"
}

# 运行主函数
main
