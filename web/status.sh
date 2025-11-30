#!/bin/bash

###############################################################################
# 知识图谱 Web 应用状态检查脚本
###############################################################################

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 检查端口
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # 运行中
    else
        return 1  # 未运行
    fi
}

# 获取进程信息
get_process_info() {
    local port=$1
    local pid=$(lsof -Pi :$port -sTCP:LISTEN -t 2>/dev/null)
    if [ -n "$pid" ]; then
        # macOS compatible ps command
        local mem=$(ps -p $pid -o rss 2>/dev/null | tail -n 1 | awk '{printf "%.1f", $1/1024}')
        local cpu=$(ps -p $pid -o %cpu 2>/dev/null | tail -n 1 | awk '{print $1}')
        if [ -n "$mem" ] && [ -n "$cpu" ]; then
            echo "$pid|${mem}MB|${cpu}%"
        else
            echo "$pid|N/A|N/A"
        fi
    else
        echo "N/A|N/A|N/A"
    fi
}

# 检查HTTP响应
check_http() {
    local url=$1
    local timeout=2
    if curl -s --max-time $timeout "$url" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 主函数
main() {
    clear
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════════╗"
    echo "║           知识图谱 Web 应用 - 服务状态                             ║"
    echo "╚════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
    
    # Neo4j
    echo -e "${BLUE}━━━ Neo4j 数据库 ━━━${NC}"
    if check_port 7687; then
        local info=$(get_process_info 7687)
        IFS='|' read -r pid mem cpu <<< "$info"
        echo -e "  状态: ${GREEN}●${NC} 运行中"
        echo -e "  端口: 7687 (Bolt), 7474 (HTTP)"
        echo -e "  PID:  $pid"
        echo -e "  内存: $mem"
        echo -e "  CPU:  $cpu"
        echo -e "  URL:  http://localhost:7474"
    else
        echo -e "  状态: ${RED}●${NC} 未运行"
        echo -e "  提示: ${YELLOW}请启动 Neo4j 数据库${NC}"
    fi
    
    echo
    
    # 后端服务
    echo -e "${BLUE}━━━ 后端 FastAPI 服务 ━━━${NC}"
    if check_port 8000; then
        local info=$(get_process_info 8000)
        IFS='|' read -r pid mem cpu <<< "$info"
        echo -e "  状态: ${GREEN}●${NC} 运行中"
        echo -e "  端口: 8000"
        echo -e "  PID:  $pid"
        echo -e "  内存: $mem"
        echo -e "  CPU:  $cpu"
        echo -e "  API:  http://localhost:8000"
        echo -e "  文档: http://localhost:8000/docs"
        
        # 健康检查
        if check_http "http://localhost:8000/health"; then
            echo -e "  健康: ${GREEN}✓${NC} 正常"
        else
            echo -e "  健康: ${YELLOW}⚠${NC} 响应异常"
        fi
        
        # 日志
        if [ -f "/tmp/pwd-backend.log" ]; then
            local log_size=$(du -h /tmp/pwd-backend.log | awk '{print $1}')
            echo -e "  日志: /tmp/pwd-backend.log ($log_size)"
        fi
    else
        echo -e "  状态: ${RED}●${NC} 未运行"
        if [ -f "/tmp/pwd-backend.log" ]; then
            echo -e "  日志: /tmp/pwd-backend.log"
            echo -e "  最后错误:"
            tail -n 3 /tmp/pwd-backend.log | sed 's/^/    /'
        fi
    fi
    
    echo
    
    # 前端服务
    echo -e "${BLUE}━━━ 前端 Vite 服务 ━━━${NC}"
    if check_port 5173; then
        local info=$(get_process_info 5173)
        IFS='|' read -r pid mem cpu <<< "$info"
        echo -e "  状态: ${GREEN}●${NC} 运行中"
        echo -e "  端口: 5173"
        echo -e "  PID:  $pid"
        echo -e "  内存: $mem"
        echo -e "  CPU:  $cpu"
        echo -e "  URL:  http://localhost:5173"
        
        # 日志
        if [ -f "/tmp/pwd-frontend.log" ]; then
            local log_size=$(du -h /tmp/pwd-frontend.log | awk '{print $1}')
            echo -e "  日志: /tmp/pwd-frontend.log ($log_size)"
        fi
    else
        echo -e "  状态: ${RED}●${NC} 未运行"
        if [ -f "/tmp/pwd-frontend.log" ]; then
            echo -e "  日志: /tmp/pwd-frontend.log"
            echo -e "  最后错误:"
            tail -n 3 /tmp/pwd-frontend.log | sed 's/^/    /'
        fi
    fi
    
    echo
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # 总体状态
    local running_count=0
    check_port 7687 && ((running_count++))
    check_port 8000 && ((running_count++))
    check_port 5173 && ((running_count++))
    
    echo
    if [ $running_count -eq 3 ]; then
        echo -e "${GREEN}✓${NC} 所有服务运行正常 ($running_count/3)"
    elif [ $running_count -eq 0 ]; then
        echo -e "${RED}✗${NC} 所有服务均未运行 ($running_count/3)"
        echo -e "  提示: 运行 ${CYAN}./start.sh${NC} 启动服务"
    else
        echo -e "${YELLOW}⚠${NC} 部分服务运行中 ($running_count/3)"
        echo -e "  提示: 运行 ${CYAN}./start.sh${NC} 启动所有服务"
    fi
    
    echo
}

# 运行主函数
main
