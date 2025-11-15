#!/bin/bash
set -e

echo "启动Ollama服务..."
ollama serve > /tmp/ollama.log 2>&1 &
OLLAMA_PID=$!

# 等待Ollama启动
echo "等待Ollama服务就绪..."
sleep 5

# 拉取模型
echo "拉取llama3.2:3b模型..."
ollama pull llama3.2:3b

echo "Ollama服务已就绪"

# 执行主命令
exec "$@"
