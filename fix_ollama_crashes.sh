#!/bin/bash
# Ollama 崩溃修复和预防脚本

echo "======================================"
echo "  Ollama 崩溃诊断与修复工具"
echo "======================================"

# 1. 检查 Ollama 状态
check_ollama() {
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama 服务正常运行"
        return 0
    else
        echo "❌ Ollama 服务未运行"
        return 1
    fi
}

# 2. 重启 Ollama
restart_ollama() {
    echo ""
    echo "⚙️  重启 Ollama 服务..."
    
    # 杀掉所有 Ollama 进程
    pkill -9 ollama
    sleep 2
    
    # 启动 Ollama（后台运行）
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    sleep 3
    
    if check_ollama; then
        echo "✅ Ollama 重启成功"
        return 0
    else
        echo "❌ Ollama 重启失败，请手动运行: ollama serve"
        return 1
    fi
}

# 3. 卸载未使用的模型释放内存
unload_unused_models() {
    echo ""
    echo "⚙️  卸载未使用的大模型..."
    
    # 列出所有模型
    echo "📋 当前已加载模型:"
    ollama list
    
    # 只保留 llama3.2:3b（用于概念抽取）
    # 卸载 llava（如果禁用了图片功能）
    # 卸载 qwen2.5-coder（如果不使用）
    
    echo ""
    echo "⚠️  建议："
    echo "   如果不需要图片描述，可以删除 llava:7b"
    echo "   ollama rm llava:7b"
}

# 4. 监控内存使用
monitor_memory() {
    echo ""
    echo "📊 当前系统内存使用:"
    vm_stat | perl -ne '/page size of (\d+)/ and $size=$1; /Pages\s+([^:]+)[^\d]+(\d+)/ and printf("%-16s % 16.2f Mi\n", "$1:", $2 * $size / 1048576);'
    
    echo ""
    echo "📊 Ollama 进程内存:"
    ps aux | grep ollama | grep -v grep | awk '{print "进程ID:", $2, " 内存:", $6/1024, "MB"}'
}

# 5. 验证配置
check_config() {
    echo ""
    echo "⚙️  检查配置文件优化..."
    
    ENABLE_IMAGE=$(grep "enable_image_captions:" config/config.yaml | awk '{print $2}')
    PARALLEL=$(grep "parallel_workers:" config/config.yaml | grep -v "#" | awk '{print $2}')
    NUM_CTX=$(grep "num_ctx:" config/config.yaml | grep -v "#" | awk '{print $2}')
    
    echo "   图片抽取: $ENABLE_IMAGE"
    echo "   并发数: $PARALLEL"
    echo "   上下文窗口: $NUM_CTX"
    
    # 建议
    if [ "$ENABLE_IMAGE" = "true" ]; then
        echo "   ⚠️  建议: 禁用图片抽取以减少内存压力"
    fi
    
    if [ "$PARALLEL" -gt 2 ]; then
        echo "   ⚠️  建议: 降低并发数到 2"
    fi
}

# 主流程
main() {
    echo ""
    echo "步骤 1: 检查 Ollama 状态"
    echo "--------------------------------------"
    if ! check_ollama; then
        restart_ollama
    fi
    
    echo ""
    echo "步骤 2: 检查内存使用"
    echo "--------------------------------------"
    monitor_memory
    
    echo ""
    echo "步骤 3: 检查配置优化"
    echo "--------------------------------------"
    check_config
    
    echo ""
    echo "======================================"
    echo "  修复完成"
    echo "======================================"
    echo ""
    echo "✅ 已完成诊断和修复"
    echo ""
    echo "📋 下一步:"
    echo "   1. 确认 Ollama 服务正常"
    echo "   2. 在构建脚本终端按 Ctrl+C"
    echo "   3. 重新运行: bash start.sh --batch-size 3"
    echo ""
    echo "💡 提示:"
    echo "   - 当前配置已优化为最低资源消耗"
    echo "   - 图片抽取已禁用"
    echo "   - 并发数已降至 2"
    echo "   - 如果仍崩溃，考虑删除 llava 模型释放内存"
}

main
