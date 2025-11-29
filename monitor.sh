#!/bin/bash
# 实时监控知识图谱构建进度

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# 清屏并打印标题
print_header() {
    clear
    echo "════════════════════════════════════════════════════════════════════════"
    echo " 📊 知识图谱构建进度监控"
    echo " 更新时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "════════════════════════════════════════════════════════════════════════"
    echo ""
}

# 检查进程
check_process() {
    if pgrep -f "enhanced_pipeline|run_pipeline|test_safe" > /dev/null; then
        echo -e "${GREEN}✓${NC} 管道进程: 运行中"
        ps aux | grep -E "enhanced_pipeline|run_pipeline|test_safe" | grep -v grep | awk '{printf "  PID: %s, CPU: %s%%, 内存: %s%%\n", $2, $3, $4}'
        return 0
    else
        echo -e "${RED}✗${NC} 管道进程: 未运行"
        return 1
    fi
}

# 检查 checkpoint 进度
check_checkpoint() {
    local progress_file="output/checkpoints/.progress.json"
    
    if [ -f "$progress_file" ]; then
        echo -e "\n${BLUE}📝 Checkpoint 进度:${NC}"
        
        # 解析 JSON（需要 jq，如果没有则用 grep）
        if command -v jq &> /dev/null; then
            local processed=$(jq -r '.processed_chunks | length' "$progress_file" 2>/dev/null || echo "?")
            local concepts=$(jq -r '.total_concepts' "$progress_file" 2>/dev/null || echo "?")
            local relationships=$(jq -r '.total_relationships' "$progress_file" 2>/dev/null || echo "?")
            local last_update=$(jq -r '.last_update' "$progress_file" 2>/dev/null || echo "N/A")
            
            echo "  已处理块数: $processed"
            echo "  总概念数: $concepts"
            echo "  总关系数: $relationships"
            echo "  最后更新: ${last_update:0:19}"
        else
            echo "  （安装 jq 以查看详细信息: brew install jq）"
            cat "$progress_file" | head -10
        fi
    else
        echo -e "\n${YELLOW}⚠${NC} 尚无 checkpoint 数据"
    fi
}

# 检查日志
check_logs() {
    local log_file="output/kg_builder.log"
    
    if [ -f "$log_file" ]; then
        echo -e "\n${CYAN}📋 最近日志:${NC}"
        tail -n 5 "$log_file" | while IFS= read -r line; do
            if echo "$line" | grep -q "ERROR"; then
                echo -e "  ${RED}$line${NC}"
            elif echo "$line" | grep -q "WARNING"; then
                echo -e "  ${YELLOW}$line${NC}"
            elif echo "$line" | grep -q "Checkpoint"; then
                echo -e "  ${GREEN}$line${NC}"
            else
                echo "  $line"
            fi
        done
    else
        echo -e "\n${YELLOW}⚠${NC} 日志文件不存在"
    fi
}

# 检查输出文件
check_output() {
    echo -e "\n${BLUE}📁 输出文件:${NC}"
    
    local files=(
        "output/concepts.csv"
        "output/relationships.csv"
        "output/checkpoints/.progress.json"
    )
    
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            local size=$(du -h "$file" | awk '{print $1}')
            local lines=$(wc -l < "$file" 2>/dev/null || echo "N/A")
            echo -e "  ${GREEN}✓${NC} $(basename $file): $size ($lines 行)"
        else
            echo -e "  ${RED}✗${NC} $(basename $file): 不存在"
        fi
    done
}

# 估算完成时间
estimate_completion() {
    local progress_file="output/checkpoints/.progress.json"
    
    if [ -f "$progress_file" ] && command -v jq &> /dev/null; then
        local processed=$(jq -r '.processed_chunks | length' "$progress_file" 2>/dev/null || echo "0")
        local started=$(jq -r '.started_at' "$progress_file" 2>/dev/null)
        
        if [ "$processed" != "0" ] && [ "$processed" != "?" ] && [ -n "$started" ]; then
            echo -e "\n${BLUE}⏱️  时间估算:${NC}"
            
            # 计算已运行时间
            local start_ts=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${started:0:19}" "+%s" 2>/dev/null || echo "0")
            local now_ts=$(date "+%s")
            local elapsed=$((now_ts - start_ts))
            
            if [ "$elapsed" -gt 0 ]; then
                local time_per_chunk=$((elapsed / processed))
                local remaining=$((100 - processed))
                local estimated_remaining=$((time_per_chunk * remaining))
                
                echo "  已运行: $((elapsed / 60)) 分钟"
                echo "  平均速度: $time_per_chunk 秒/块"
                echo "  剩余时间: 约 $((estimated_remaining / 60)) 分钟 (假设 100 块)"
            fi
        fi
    fi
}

# 显示快捷操作
show_shortcuts() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo " 快捷操作:"
    echo "   [r] 刷新  [l] 查看完整日志  [q] 退出"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# 主循环
main() {
    # 检查是否安装了必要工具
    if ! command -v jq &> /dev/null; then
        echo -e "${YELLOW}提示: 安装 jq 以获得更详细的进度信息${NC}"
        echo "安装命令: brew install jq"
        echo ""
        sleep 2
    fi
    
    while true; do
        print_header
        check_process
        local process_running=$?
        
        check_checkpoint
        estimate_completion
        check_output
        check_logs
        show_shortcuts
        
        # 如果进程未运行，提示
        if [ $process_running -ne 0 ]; then
            echo ""
            echo -e "${YELLOW}提示: 管道未运行，启动命令:${NC}"
            echo "  python run_pipeline.py"
            echo "  # 或"
            echo "  bash run.sh"
        fi
        
        # 等待用户输入（5秒超时自动刷新）
        read -t 5 -n 1 -s key
        case $key in
            q|Q)
                echo ""
                echo "退出监控"
                exit 0
                ;;
            l|L)
                clear
                echo "完整日志 (按 q 退出):"
                echo "════════════════════════════════════════════════════════════════════════"
                less +G output/kg_builder.log
                ;;
            r|R|"")
                # 刷新（默认行为）
                ;;
        esac
    done
}

# 捕获 Ctrl+C
trap 'echo -e "\n\n退出监控"; exit 0' INT

main
