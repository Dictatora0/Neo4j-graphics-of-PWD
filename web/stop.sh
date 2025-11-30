#!/bin/bash

###############################################################################
# 知识图谱 Web 应用停止脚本
# 功能：优雅停止前后端服务
###############################################################################

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

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

# 停止服务
stop_service() {
    local service_name=$1
    local pid_file=$2
    local port=$3
    
    log_info "停止 $service_name..."
    
    # 从 PID 文件读取
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            kill $pid 2>/dev/null
            sleep 1
            
            # 如果进程还在，强制杀死
            if ps -p $pid > /dev/null 2>&1; then
                kill -9 $pid 2>/dev/null
            fi
            
            log_success "$service_name 已停止 (PID: $pid)"
        else
            log_warning "$service_name 进程不存在 (PID: $pid)"
        fi
        rm -f "$pid_file"
    else
        # 尝试通过端口查找进程
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            local pid=$(lsof -Pi :$port -sTCP:LISTEN -t)
            kill -9 $pid 2>/dev/null
            log_success "$service_name 已停止 (端口: $port, PID: $pid)"
        else
            log_warning "$service_name 未运行"
        fi
    fi
}

# 清理日志文件
cleanup_logs() {
    local log_pattern=$1
    local keep_logs=$2
    
    if [ "$keep_logs" = false ]; then
        log_info "清理日志文件..."
        rm -f /tmp/pwd-*.log
        log_success "日志文件已清理"
    else
        log_info "保留日志文件: /tmp/pwd-*.log"
    fi
}

# 主函数
main() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║     停止知识图谱 Web 应用服务                          ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
    
    # 询问是否保留日志
    local keep_logs=true
    if [ "$1" != "--keep-logs" ]; then
        read -p "$(echo -e ${YELLOW}是否保留日志文件? [Y/n]: ${NC})" -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            keep_logs=false
        fi
    fi
    
    # 停止前端服务
    stop_service "前端服务" "/tmp/pwd-frontend.pid" "5173"
    
    # 停止后端服务
    stop_service "后端服务" "/tmp/pwd-backend.pid" "8000"
    
    # 清理日志
    cleanup_logs "/tmp/pwd-*.log" $keep_logs
    
    echo
    log_success "所有服务已停止"
    
    if [ "$keep_logs" = true ]; then
        echo
        log_info "查看日志:"
        log_info "  后端: tail -f /tmp/pwd-backend.log"
        log_info "  前端: tail -f /tmp/pwd-frontend.log"
    fi
}

# 运行主函数
main "$@"
