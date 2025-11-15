# 松材线虫病知识图谱构建 - Docker镜像
FROM ubuntu:22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV OLLAMA_HOST=http://localhost:11434

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装Ollama
RUN curl -fsSL https://ollama.ai/install.sh | sh

# 创建工作目录
WORKDIR /app

# 复制项目文件
COPY requirements.txt .
COPY *.py .
COPY config/ config/
COPY 文献/ 文献/

# 安装Python依赖
RUN pip3 install --no-cache-dir -r requirements.txt

# 创建输出目录
RUN mkdir -p output cache

# 启动脚本
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

# 暴露端口 (如果需要Neo4j)
EXPOSE 7474 7687

# 入口点
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["python3", "main.py"]
