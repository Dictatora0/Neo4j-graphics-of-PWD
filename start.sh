#!/bin/bash
# 知识图谱构建启动脚本 - 使用正确的 Python 环境
# v2.6 - 自动负载监控与清理

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 监控配置
MEMORY_THRESHOLD=85  # 内存使用率阈值 (%)
CPU_THRESHOLD=90     # CPU使用率阈值 (%)
CHECK_INTERVAL=60    # 检查间隔 (秒)
MONITOR_PID_FILE="/tmp/kg_monitor.pid"

# 清理函数
cleanup_monitor() {
    if [ -f "$MONITOR_PID_FILE" ]; then
        monitor_pid=$(cat "$MONITOR_PID_FILE")
        if ps -p $monitor_pid > /dev/null 2>&1; then
            kill $monitor_pid 2>/dev/null || true
        fi
        rm -f "$MONITOR_PID_FILE"
    fi
}

# 注册退出时清理监控进程
trap cleanup_monitor EXIT INT TERM

# 检查系统资源
check_system_resources() {
    # 获取内存使用率
    if command -v python3 &> /dev/null; then
        mem_usage=$(python3 -c "import psutil; print(int(psutil.virtual_memory().percent))" 2>/dev/null || echo "0")
    else
        mem_usage=0
    fi
    
    # 获取CPU使用率
    if [[ "$OSTYPE" == "darwin"* ]]; then
        cpu_usage=$(ps -A -o %cpu | awk '{s+=$1} END {print int(s)}' 2>/dev/null || echo "0")
    else
        cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print int(100 - $1)}' 2>/dev/null || echo "0")
    fi
    
    echo "$mem_usage:$cpu_usage"
}

# 自动清理资源
auto_cleanup() {
    echo -e "\n${YELLOW}[AUTO-CLEANUP] 检测到资源过载，执行自动清理...${NC}"
    
    # 1. Python垃圾回收（通过发送信号）
    if pgrep -f "enhanced_pipeline_safe.py" > /dev/null; then
        echo -e "${BLUE}  → 触发Python垃圾回收${NC}"
        # Python进程会自动执行周期性GC
    fi
    
    # 2. 重启Ollama释放内存
    if pgrep ollama > /dev/null; then
        echo -e "${BLUE}  → 重启Ollama服务${NC}"
        pkill ollama 2>/dev/null || true
        sleep 2
        nohup ollama serve > /dev/null 2>&1 &
        sleep 3
    fi
    
    # 3. 系统缓存清理（macOS）
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "${BLUE}  → 清理系统缓存${NC}"
        sudo purge 2>/dev/null || true
    fi
    
    echo -e "${GREEN}[AUTO-CLEANUP] 清理完成${NC}\n"
}

# 后台监控进程
background_monitor() {
    while true; do
        sleep $CHECK_INTERVAL
        
        # 检查资源使用
        resources=$(check_system_resources)
        mem_usage=$(echo $resources | cut -d: -f1)
        cpu_usage=$(echo $resources | cut -d: -f2)
        
        # 记录到日志
        timestamp=$(date '+%Y-%m-%d %H:%M:%S')
        echo "[$timestamp] Memory: ${mem_usage}%, CPU: ${cpu_usage}%" >> output/resource_monitor.log
        
        # 检查是否需要清理
        if [ $mem_usage -ge $MEMORY_THRESHOLD ] || [ $cpu_usage -ge $CPU_THRESHOLD ]; then
            echo "[$timestamp] ALERT: Memory ${mem_usage}%, CPU ${cpu_usage}% - Triggering cleanup" >> output/resource_monitor.log
            auto_cleanup >> output/resource_monitor.log 2>&1
        fi
    done
}

# 设置 HuggingFace 环境变量
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_OFFLINE=1  # 强制离线模式
export TRANSFORMERS_OFFLINE=1  # 禁用联网检查
echo "[INFO] 已设置 HuggingFace 离线模式" >&2

# 使用已安装依赖的 Python 3.10.13
PYTHON_BIN="$HOME/.pyenv/versions/3.10.13/bin/python"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║        松材线虫病知识图谱构建系统 v2.6                                  ║"
echo "║        自动负载监控与清理已启用                                         ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# 检查 Python 是否存在
if [ ! -f "$PYTHON_BIN" ]; then
    echo -e "${YELLOW}[WARN] Python 3.10.13 未找到，尝试使用系统 Python${NC}"
    PYTHON_BIN="python3"
fi

# 显示使用的 Python
echo -e "${BLUE}使用的 Python:${NC} $PYTHON_BIN"
$PYTHON_BIN --version
echo ""

# 启动前资源检查
echo -e "${BLUE}[系统检查] 检测当前资源状态...${NC}"
resources=$(check_system_resources)
mem_usage=$(echo $resources | cut -d: -f1)
cpu_usage=$(echo $resources | cut -d: -f2)

echo -e "  内存使用: ${mem_usage}%"
echo -e "  CPU使用: ${cpu_usage}%"

if [ $mem_usage -ge 85 ]; then
    echo -e "${RED}[警告] 内存使用率过高 (${mem_usage}%)${NC}"
    echo -e "${YELLOW}建议: 运行 './cleanup_memory.sh' 清理后再启动${NC}"
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
elif [ $mem_usage -ge 70 ]; then
    echo -e "${YELLOW}[提示] 内存使用偏高 (${mem_usage}%)，自动清理功能已启用${NC}"
else
    echo -e "${GREEN}[正常] 系统资源充足${NC}"
fi
echo ""

# 检查进度
if [ -f "output/checkpoints/.progress.json" ]; then
    echo -e "${GREEN}[INFO] 发现 checkpoint，将从断点继续${NC}"
    processed=$($PYTHON_BIN -c "import json; print(len(json.load(open('output/checkpoints/.progress.json'))['processed_chunks']))" 2>/dev/null || echo "?")
    if [ "$processed" != "?" ]; then
        echo -e "  已处理块数: $processed"
    fi
    echo ""
fi

# 启动后台监控
echo -e "${BLUE}[监控] 启动后台资源监控 (间隔: ${CHECK_INTERVAL}s)${NC}"
background_monitor &
echo $! > "$MONITOR_PID_FILE"
echo -e "${GREEN}[监控] 后台监控已启动 (PID: $(cat $MONITOR_PID_FILE))${NC}"
echo -e "  监控阈值: 内存 ${MEMORY_THRESHOLD}%, CPU ${CPU_THRESHOLD}%"
echo -e "  监控日志: output/resource_monitor.log"
echo ""

# 运行管道
echo -e "${BLUE}====================================================================${NC}"
echo -e "${GREEN}启动安全模式管道 (v2.6 - 自动负载优化)${NC}"
echo -e "${BLUE}====================================================================${NC}"
echo ""
echo "提示:"
echo "  - 按 Ctrl+C 可安全退出并保存进度"
echo "  - 自动监控: 检测到资源过载会自动清理"
echo "  - 手动监控: 在另一个终端运行 'python monitor_memory.py'"
echo "  - 日志文件: output/kg_builder.log"
echo "  - 资源日志: output/resource_monitor.log"
echo ""
echo -e "${BLUE}====================================================================${NC}"
echo ""

# 执行主程序
exec "$PYTHON_BIN" enhanced_pipeline_safe.py "$@"
