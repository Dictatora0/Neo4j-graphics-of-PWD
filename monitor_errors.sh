#!/bin/bash
# 实时监控JSON解析错误

echo "🔍 监控JSON解析错误..."
echo "按 Ctrl+C 停止"
echo "================================"

tail -f output/kg_builder.log | grep --line-buffered -E "(❌|✅|JSON解析|原始响应|错误类型|Failed to parse)"
