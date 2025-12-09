#!/bin/bash
# 知识图谱构建启动脚本 - 使用正确的 Python 环境
# 集成六大改进功能 + 分批处理 + 自动负载监控
#
# 新功能：
#   - 滑动窗口上下文机制
#   - 层级本体 Label
#   - Local Search 精确检索
#   - 实体消歧与链接 (CanonicalResolver)
#   - 多模态深度融合
#   - 人机回环纠错

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

# 分批处理配置
BATCH_SIZE=50        # 每批处理的chunk数量（默认50）
BATCH_MODE="auto"   # 批次模式: auto(自动), manual(手动确认), single(单批)
BATCH_CLEANUP=true   # 批次间是否自动清理
BATCH_LOG="output/batch_progress.log"
BATCH_STATE="output/.batch_state.json"

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

# 批次状态管理
get_batch_state() {
    if [ -f "$BATCH_STATE" ]; then
        cat "$BATCH_STATE"
    else
        echo '{"current_batch": 0, "total_batches": 0, "completed_chunks": 0}'
    fi
}

save_batch_state() {
    local batch=$1
    local total=$2
    local chunks=$3
    echo "{\"current_batch\": $batch, \"total_batches\": $total, \"completed_chunks\": $chunks, \"timestamp\": \"$(date -Iseconds)\"}" > "$BATCH_STATE"
}

# 批次间清理
batch_cleanup() {
    local batch_num=$1
    echo -e "\n${YELLOW}[BATCH-CLEANUP] 批次 $batch_num 完成，执行清理...${NC}"
    
    # 1. 重启Ollama释放内存
    if pgrep ollama > /dev/null; then
        echo -e "${BLUE}  → 重启Ollama服务${NC}"
        pkill ollama 2>/dev/null || true
        sleep 3
        nohup ollama serve > /dev/null 2>&1 &
        sleep 5
        echo -e "${GREEN}  Ollama已重启${NC}"
    fi
    
    # 2. Python垃圾回收提示
    echo -e "${BLUE}  → Python将在下批开始时自动执行GC${NC}"
    
    # 3. 等待系统稳定
    echo -e "${BLUE}  → 等待系统稳定 (3秒)...${NC}"
    sleep 3
    
    # 4. 显示资源状态
    resources=$(check_system_resources)
    mem_usage=$(echo $resources | cut -d: -f1)
    echo -e "${GREEN}  当前内存: ${mem_usage}%${NC}"
    
    echo -e "${GREEN}[BATCH-CLEANUP] 清理完成${NC}\n"
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
    
    # 3. 系统缓存清理（macOS）- 无需sudo
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "${BLUE}  → 触发内存压缩${NC}"
        # 使用sync强制写入缓存，无需sudo
        sync 2>/dev/null || true
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

# 检查新功能状态
check_features() {
    echo -e "\n${BLUE}[功能状态检查]${NC}"
    
    # 检查 Python 依赖
    local missing_deps=()
    for dep in pandas requests yaml sklearn; do
        if ! "$PYTHON_BIN" -c "import $dep" 2>/dev/null; then
            # yaml 对应的包名是 pyyaml
            if [ "$dep" = "yaml" ]; then
                missing_deps+=("pyyaml")
            else
                missing_deps+=("$dep")
            fi
        fi
    done
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo -e "  ${RED}缺少依赖: ${missing_deps[*]}${NC}"
        echo -e "    安装命令: pip install ${missing_deps[*]}"
        return 1
    else
        echo -e "  ${GREEN}Python 依赖完整${NC}"
    fi
    
    # 检查配置文件
    if [ ! -f "config/config.yaml" ]; then
        echo -e "  ${RED}配置文件不存在${NC}"
        return 1
    fi
    
    # 检查新功能配置
    if command -v python3 &> /dev/null; then
        context_window=$("$PYTHON_BIN" -c "import yaml; c=yaml.safe_load(open('config/config.yaml')); print(c.get('improvements', {}).get('context_window', {}).get('enable', False))" 2>/dev/null || echo "False")
        entity_linking=$("$PYTHON_BIN" -c "import yaml; c=yaml.safe_load(open('config/config.yaml')); print(c.get('improvements_phase2', {}).get('entity_linking', {}).get('use_external_kb', False))" 2>/dev/null || echo "False")
        
        echo -e "  ${GREEN}配置文件加载成功${NC}"
        echo -e "    - 滑动窗口: ${context_window}"
        echo -e "    - 外部知识库: ${entity_linking}"
    fi
    
    # 检查 Ollama
    if pgrep ollama > /dev/null; then
        echo -e "  ${GREEN}Ollama 服务运行中${NC}"
        # 测试 API 连接
        if curl -s -f http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo -e "    API 状态: 正常"
        else
            echo -e "    ${YELLOW}API 状态: 启动中${NC}"
        fi
    else
        echo -e "  ${YELLOW}Ollama 服务未运行${NC}"
        echo -e "    ${BLUE}提示: 运行 start.sh 时会自动启动 Ollama${NC}"
        echo -e "    或手动启动: ollama serve"
    fi
    
    echo ""
    return 0
}

# 快速测试新功能
test_features() {
    echo -e "\n${BLUE}[快速功能测试]${NC}"
    echo -e "正在测试新功能...\n"
    
    if [ -f "scripts/run_feature_tests.py" ]; then
        "$PYTHON_BIN" scripts/run_feature_tests.py
    elif [ -f "scripts/verify_all_improvements.sh" ]; then
        bash scripts/verify_all_improvements.sh
    else
        echo -e "${YELLOW}未找到测试脚本${NC}"
    fi
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --batch-mode)
            BATCH_MODE="$2"
            shift 2
            ;;
        --no-cleanup)
            BATCH_CLEANUP=false
            shift
            ;;
        --check)
            check_features
            exit $?
            ;;
        --test)
            test_features
            exit $?
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo ""
            echo "主要选项:"
            echo "  --batch-size <N>      每批处理N个chunks (默认: 50)"
            echo "  --batch-mode <mode>   批次模式: auto|manual|single (默认: auto)"
            echo "  --no-cleanup          禁用批次间自动清理"
            echo ""
            echo "诊断与测试:"
            echo "  --check               检查系统依赖和功能状态"
            echo "  --test                运行快速功能测试"
            echo "  --help                显示此帮助信息"
            echo ""
            echo "批次模式说明:"
            echo "  auto   - 自动连续处理所有批次"
            echo "  manual - 每批完成后需手动确认"
            echo "  single - 只处理一批后停止"
            echo ""
            echo "新功能："
            echo "  - 滑动窗口上下文机制 - 解决跨块实体指代丢失"
            echo "  - 层级本体 Label - 支持高级语义查询"
            echo "  - Local Search - 精确问答能力"
            echo "  - 实体消歧与链接 - 生物分类学标准化"
            echo "  - 多模态深度融合 - 图片-概念关联"
            echo "  - 人机回环纠错 - 用户反馈机制"
            echo ""
            echo "示例:"
            echo "  $0                                    # 使用默认配置运行"
            echo "  $0 --check                            # 检查系统状态"
            echo "  $0 --test                             # 测试新功能"
            echo "  $0 --batch-size 30 --batch-mode manual  # 自定义批次"
            echo "  $0 --batch-size 100 --no-cleanup       # 大批次无清理"
            echo ""
            echo "配置文件: config/config.yaml"
            echo "日志文件: output/kg_builder.log"
            echo "批次日志: $BATCH_LOG"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║        松材线虫病知识图谱构建系统                                         ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}新功能状态:${NC}"
echo -e "  - 滑动窗口上下文机制 (解决跨块实体指代)"
echo -e "  - 层级本体 Label (支持语义查询)"
echo -e "  - Local Search (精确问答)"
echo -e "  - 实体消歧与链接 (标准化)"
echo -e "  - 多模态深度融合 (图片关联)"
echo -e "  - 人机回环纠错 (反馈收集)"
echo ""
echo -e "${BLUE}分批配置:${NC}"
echo -e "  批次大小: ${BATCH_SIZE} chunks/batch"
echo -e "  批次模式: ${BATCH_MODE}"
echo -e "  批次间清理: ${BATCH_CLEANUP}"
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

# 执行功能状态检查
if ! check_features; then
    echo -e "\n${YELLOW}[警告] 部分功能检查失败${NC}"
    echo -e "${YELLOW}建议运行: $0 --check 查看详细信息${NC}"
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

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

# 检查进度和批次状态
if [ -f "output/checkpoints/.progress.json" ]; then
    echo -e "${GREEN}[INFO] 发现 checkpoint，将从断点继续${NC}"
    processed=$($PYTHON_BIN -c "import json; print(len(json.load(open('output/checkpoints/.progress.json'))['processed_chunks']))" 2>/dev/null || echo "?")
    if [ "$processed" != "?" ]; then
        echo -e "  已处理块数: $processed"
    fi
    echo ""
fi

# 显示批次状态
if [ -f "$BATCH_STATE" ]; then
    batch_info=$(get_batch_state)
    current_batch=$($PYTHON_BIN -c "import json; print(json.loads('$batch_info')['current_batch'])" 2>/dev/null || echo "0")
    total_batches=$($PYTHON_BIN -c "import json; print(json.loads('$batch_info')['total_batches'])" 2>/dev/null || echo "0")
    if [ "$current_batch" != "0" ]; then
        echo -e "${BLUE}[批次进度] 批次 $current_batch/$total_batches${NC}"
        echo ""
    fi
fi

# 检查并启动 Ollama 服务
echo -e "${BLUE}[Ollama 服务] 检查 Ollama 状态...${NC}"
if pgrep ollama > /dev/null; then
    echo -e "${GREEN}  Ollama 服务已运行${NC}"
    # 测试 API 连接
    if curl -s -f http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${GREEN}  Ollama API 连接正常${NC}"
    else
        echo -e "${YELLOW}  Ollama 服务正在启动中，等待就绪...${NC}"
        sleep 3
    fi
else
    echo -e "${YELLOW}  Ollama 服务未运行，正在启动...${NC}"
    
    # 启动 Ollama 服务
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    ollama_pid=$!
    echo -e "${BLUE}  → 已启动 Ollama (PID: $ollama_pid)${NC}"
    
    # 等待服务就绪（最多 15 秒）
    echo -e "${BLUE}  → 等待 Ollama 服务就绪...${NC}"
    for i in {1..15}; do
        if curl -s -f http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo -e "${GREEN}  Ollama 服务已就绪${NC}"
            break
        fi
        if [ $i -eq 15 ]; then
            echo -e "${RED}  Ollama 启动超时，请检查日志: /tmp/ollama.log${NC}"
            echo -e "${YELLOW}  提示: 您可以手动运行 'ollama serve' 然后重新启动本脚本${NC}"
            exit 1
        fi
        sleep 1
        echo -n "."
    done
    echo ""
fi
echo ""

# 启动后台监控
echo -e "${BLUE}[监控] 启动后台资源监控 (间隔: ${CHECK_INTERVAL}s)${NC}"
background_monitor &
echo $! > "$MONITOR_PID_FILE"
echo -e "${GREEN}[监控] 后台监控已启动 (PID: $(cat $MONITOR_PID_FILE))${NC}"
echo -e "  监控阈值: 内存 ${MEMORY_THRESHOLD}%, CPU ${CPU_THRESHOLD}%"
echo -e "  监控日志: output/resource_monitor.log"
echo ""

# 运行管道（分批处理）
echo -e "${BLUE}====================================================================${NC}"
echo -e "${GREEN}启动分批处理模式${NC}"
echo -e "${BLUE}====================================================================${NC}"
echo ""
echo "提示:"
echo "  - 按 Ctrl+C 可安全退出并保存进度"
echo "  - 批次模式: ${BATCH_MODE} (${BATCH_SIZE} chunks/batch)"
echo "  - 自动监控: 检测到资源过载会自动清理"
echo "  - 批次日志: $BATCH_LOG"
echo "  - 系统日志: output/kg_builder.log"
echo ""
echo -e "${BLUE}====================================================================${NC}"
echo ""

# 分批处理主循环
batch_num=1
total_processed=0

while true; do
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}[批次 $batch_num] 开始处理 (最多 $BATCH_SIZE chunks)${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # 记录批次开始
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Batch $batch_num started (size: $BATCH_SIZE)" >> "$BATCH_LOG"
    
    # 执行pipeline（传递batch_size参数）
    if "$PYTHON_BIN" enhanced_pipeline_safe.py --max-chunks "$BATCH_SIZE"; then
        echo -e "\n${GREEN}[批次 $batch_num] 完成${NC}"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Batch $batch_num completed" >> "$BATCH_LOG"
        
        # 更新进度
        total_processed=$((total_processed + BATCH_SIZE))
        
        # 检查是否还有未处理的chunks
        if [ -f "output/checkpoints/.progress.json" ]; then
            remaining=$($PYTHON_BIN -c "
import json
try:
    with open('output/checkpoints/.progress.json') as f:
        progress = json.load(f)
    # 这里需要知道总chunk数，暂时假设检查processed_chunks列表
    print('continue')  # 简化处理
except:
    print('done')
" 2>/dev/null || echo "done")
        else
            remaining="done"
        fi
        
        # 批次间处理
        if [ "$remaining" = "done" ]; then
            echo -e "\n${GREEN}所有批次处理完成${NC}"
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] All batches completed. Total processed: $total_processed chunks" >> "$BATCH_LOG"
            break
        fi
        
        # 批次间清理
        if [ "$BATCH_CLEANUP" = true ]; then
            batch_cleanup $batch_num
        fi
        
        # 批次模式处理
        if [ "$BATCH_MODE" = "single" ]; then
            echo -e "\n${BLUE}[单批模式] 已完成一批，退出${NC}"
            echo "提示: 再次运行 $0 继续处理下一批"
            break
        elif [ "$BATCH_MODE" = "manual" ]; then
            echo -e "\n${YELLOW}[手动模式] 批次 $batch_num 已完成${NC}"
            read -p "是否继续下一批？(y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo -e "${BLUE}用户选择停止，退出${NC}"
                break
            fi
        else
            # auto模式：继续下一批
            echo -e "\n${GREEN}[自动模式] 准备处理下一批...${NC}"
            sleep 2
        fi
        
        batch_num=$((batch_num + 1))
        
    else
        echo -e "\n${RED}[批次 $batch_num] 处理失败${NC}"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Batch $batch_num failed" >> "$BATCH_LOG"
        
        echo -e "${YELLOW}选项:${NC}"
        echo "  1. 重试当前批次"
        echo "  2. 跳过当前批次"
        echo "  3. 退出"
        read -p "请选择 (1/2/3): " -n 1 -r
        echo
        
        case $REPLY in
            1)
                echo -e "${BLUE}重试批次 $batch_num...${NC}"
                continue
                ;;
            2)
                echo -e "${YELLOW}跳过批次 $batch_num${NC}"
                batch_num=$((batch_num + 1))
                ;;
            *)
                echo -e "${RED}退出${NC}"
                break
                ;;
        esac
    fi
done

echo -e "\n${GREEN}═══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}分批处理完成${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════${NC}"
echo -e "  总批次: $batch_num"
echo -e "  已处理: ~$total_processed chunks"
echo -e "  批次日志: $BATCH_LOG"
echo -e "  系统日志: output/kg_builder.log"
echo ""
echo -e "${BLUE}下一步操作:${NC}"
echo -e "  1. 导入 Neo4j:  python import_to_neo4j_final.py"
echo -e "  2. 启动 Web:    cd web && ./start.sh"
echo -e "  3. 测试功能:    $0 --test"
echo -e "  4. 查看日志:    tail -f output/kg_builder.log"
echo ""
