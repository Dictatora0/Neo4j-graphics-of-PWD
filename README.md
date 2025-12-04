# <center>松材线虫病知识图谱构建系统</center>

<div align="center">

**基于文献的松材线虫病（Pine Wilt Disease, PWD）知识图谱自动化构建与可视化系统**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org)
[![Neo4j](https://img.shields.io/badge/Neo4j-4.x%20%7C%205.x-green.svg)](https://neo4j.com)
[![LLM](https://img.shields.io/badge/LLM-Qwen2.5--Coder--7B/14B-orange.svg)](https://github.com/QwenLM/Qwen2.5-Coder)
[![BGE-M3](https://img.shields.io/badge/Embedding-BGE--M3-red.svg)](https://huggingface.co/BAAI/bge-m3)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-green.svg)](https://github.com/features/actions)

</div>

---

## 目录

- [松材线虫病知识图谱构建系统](#松材线虫病知识图谱构建系统)
  - [目录](#目录)
  - [1. 项目简介](#1-项目简介)
    - [核心能力](#核心能力)
  - [2. 技术栈与系统架构](#2-技术栈与系统架构)
    - [2.1 技术栈](#21-技术栈)
    - [2.2 系统架构概览](#22-系统架构概览)
  - [3. 快速开始](#3-快速开始)
    - [3.1 Docker 方式（推荐）](#31-docker-方式推荐)
      - [前置要求](#前置要求)
      - [一键启动](#一键启动)
    - [3.2 传统方式（本地环境）](#32-传统方式本地环境)
      - [步骤 1：安装依赖](#步骤-1安装依赖)
      - [步骤 2：准备 PDF 文献](#步骤-2准备-pdf-文献)
      - [步骤 3：一键运行管道](#步骤-3一键运行管道)
      - [步骤 4：导入 Neo4j 并启动 Web](#步骤-4导入-neo4j-并启动-web)
  - [4. 目录结构](#4-目录结构)
  - [5. 环境与配置](#5-环境与配置)
    - [5.1 LLM 与 Ollama](#51-llm-与-ollama)
    - [5.2 去重与过滤](#52-去重与过滤)
    - [5.3 PDF 与多模态（可选）](#53-pdf-与多模态可选)
    - [5.4 Neo4j 连接（导入脚本内部配置）](#54-neo4j-连接导入脚本内部配置)
  - [6. 知识图谱构建流程](#6-知识图谱构建流程)
    - [6.1 流程概览](#61-流程概览)
    - [6.2 主要脚本一览](#62-主要脚本一览)
  - [7. Web 可视化应用](#7-web-可视化应用)
    - [7.1 功能概览](#71-功能概览)
    - [7.2 启动方式](#72-启动方式)
  - [8. DevOps 与 CI/CD](#8-devops-与-cicd)
    - [8.1 容器化与 Makefile](#81-容器化与-makefile)
    - [8.2 GitHub Actions CI/CD](#82-github-actions-cicd)
  - [9. 性能与优化](#9-性能与优化)
  - [10. 常用命令速查表](#10-常用命令速查表)
    - [10.1 知识图谱构建（本地）](#101-知识图谱构建本地)
    - [10.2 Docker 与服务](#102-docker-与服务)
    - [10.3 Web 应用（非 Docker）](#103-web-应用非-docker)
  - [11. 故障排查](#11-故障排查)
  - [12. 贡献与许可证](#12-贡献与许可证)
    - [12.1 贡献流程](#121-贡献流程)
    - [12.2 许可证](#122-许可证)
  - [13. 相关文档](#13-相关文档)

---

## 1. 项目简介

松材线虫病（Pine Wilt Disease, PWD）是典型的毁灭性森林病害。本项目面向该领域：

- 从多篇 PDF 文献中自动抽取**实体**与**关系**
- 构建 Neo4j 知识图谱，并提供 **Web 可视化界面**
- 支持 **GraphRAG 社区摘要**、**语义去重**、**多模态图片抽取（可选）**
- 提供完整的 **Docker 部署** 与 **CI/CD 工作流**

### 核心能力

- 文献 → 文本解析 → 实体/关系抽取 → 语义去重 → 图数据库导入 → Web 可视化
- 支持 9 类实体（病原、寄主、媒介、防治等）、17 类关系（感染、传播、防治、影响等）
- 提供断点续传、增量保存、性能监控等长任务保护机制

---

## 2. 技术栈与系统架构

### 2.1 技术栈

| 模块      | 技术                 | 用途                       |
| --------- | -------------------- | -------------------------- |
| LLM       | Qwen2.5-Coder 7B/14B | 概念和关系抽取             |
| Embedding | BGE-M3               | 语义去重与实体对齐         |
| 图数据库  | Neo4j 5.x            | 知识图谱存储与查询         |
| 后端 API  | FastAPI + Uvicorn    | 图谱查询 REST API          |
| 前端      | React 19 + Vite + TS | 图谱可视化界面             |
| 可视化    | Cytoscape.js         | 交互式网络图               |
| 样式      | Tailwind CSS         | UI 设计                    |
| 容器化    | Docker + Compose     | 一键部署与环境隔离         |
| CI/CD     | GitHub Actions       | 自动化测试、构建与镜像推送 |

### 2.2 系统架构概览

```text
PDF 文献
  ↓
[文本提取]  pdf_extractor.py (PyMuPDF + OCR)
  ↓
[文本分块]  chunk_size / overlap
  ↓
[LLM 抽取]  concept_extractor.py (Qwen2.5-Coder)
  ↓
[语义去重]  concept_deduplicator.py (BGE-M3)
  ↓
[过滤与整合]  重要性/连接度过滤
  ↓
CSV 输出: output/concepts.csv, output/relationships.csv
  ↓
[图数据库导入]  import_to_neo4j_final.py → Neo4j
  ↓
[GraphRAG 社区摘要（可选）] graph_rag.py / graph_summarizer.py
  ↓
Web 应用: FastAPI 后端 + React 前端 (Docker / 本地)
```

---

## 3. 快速开始

### 3.1 Docker 方式（推荐）

> 适合希望快速体验完整系统（Neo4j + 后端 API + 前端可视化）的用户。

#### 前置要求

- 已安装 Docker Desktop（或 Docker Engine）和 Docker Compose v2
- 可访问 Docker Hub（或已配置镜像加速）

#### 一键启动

```bash
# 1. 克隆项目
git clone https://github.com/Dictatora0/Neo4j-graphics-of-PWD.git
cd PWD

# 2. 检查 Docker 环境
./check_docker_env.sh

# 3. 一键构建并启动所有服务（生产模式）
make quick-start
```

启动完成后：

- 前端可视化：`http://localhost`
- 后端 API 文档：`http://localhost:8000/docs`
- Neo4j Browser：`http://localhost:7474`  
  用户名：`neo4j`，密码：`12345678`

常用管理命令：

```bash
make status       # 查看容器与健康状态
make logs         # 查看所有服务日志
make logs-backend # 后端日志
make logs-neo4j   # Neo4j 日志

make restart      # 重启所有服务
make down         # 停止并移除容器
make up-dev       # 开发模式（前端热更新）

make test         # 运行后端 + 前端测试
make lint         # 运行代码风格检查
make help         # 查看 Makefile 所有命令
```

详细 Docker 使用说明参见：`archive/docs/DOCKER_DEPLOYMENT.md`、`archive/docs/QUICK_START_DOCKER.md`、`archive/docs/GET_STARTED_WITH_DEVOPS.md`。

---

### 3.2 传统方式（本地环境）

> 适合需要深入修改管道实现或无法使用 Docker 的环境。

#### 步骤 1：安装依赖

```bash
# Python 3.10+
pip install -r requirements.txt

# 安装并启动 Ollama
# macOS
brew install ollama
ollama serve

# 拉取模型
ollama pull qwen2.5-coder:7b
# 或更高精度：
ollama pull qwen2.5-coder:14b
```

#### 步骤 2：准备 PDF 文献

```bash
mkdir -p 文献
cp /path/to/your/*.pdf 文献/
```

如需修改目录，在 `config/config.yaml` 中调整：

```yaml
pdf:
  input_directory: ./文献
```

#### 步骤 3：一键运行管道

```bash
# 根目录
./start.sh
```

脚本会自动：

- 选择合适的 Python 环境
- 加载 `config/config.yaml`
- 断点续传（如存在 checkpoint）
- 显示进度与日志

结果输出到：

```text
output/concepts.csv
output/relationships.csv
output/kg_builder.log
output/checkpoints/
```

#### 步骤 4：导入 Neo4j 并启动 Web

```bash
# 导入 Neo4j
python import_to_neo4j_final.py

# 启动 Web 应用（本地脚本方式）
cd web
./start.sh

# 访问
# 前端: http://localhost:5173
# API : http://localhost:8000/docs
# Neo4j: http://localhost:7474
```

---

## 4. 目录结构

```text
PWD/
├── config/
│   ├── config.yaml           # 主配置文件
│   ├── logger_config.yaml    # 日志配置
│   └── config_loader.py
├── web/
│   ├── backend/              # FastAPI 后端
│   │   ├── app/
│   │   ├── requirements.txt
│   │   └── .env.example
│   ├── frontend/             # React + Vite 前端
│   │   ├── src/
│   │   └── package.json
│   ├── start.sh / stop.sh / status.sh
│   └── PROJECT_STRUCTURE.md
├── output/
│   ├── concepts.csv
│   ├── relationships.csv
│   ├── checkpoints/
│   └── kg_builder.log
├── docker-compose.yml
├── Makefile
├── check_docker_env.sh
├── scripts/
│   └── local_ci_test.sh      # 本地 CI 测试脚本
├── archive/
│   └── docs/                 # 归档文档（部署、优化、实现细节等）
│       ├── DOCKER_DEPLOYMENT.md
│       ├── CI_CD_GUIDE.md
│       ├── IMPLEMENTATION_DETAILS.md
│       ├── MEMORY_OPTIMIZATION.md
│       └── ...
└── README.md                 # 本文件
```

---

## 5. 环境与配置

### 5.1 LLM 与 Ollama

配置位于 `config/config.yaml`：

```yaml
llm:
  model: qwen2.5-coder:7b # 或 14b
  ollama_host: http://localhost:11434
  timeout: 600 # 秒
  temperature: 0.1
  max_chunks: null # null 表示处理全部块
```

### 5.2 去重与过滤

```yaml
deduplication:
  use_bge_m3: true
  embedding_model: BAAI/bge-m3
  similarity_threshold: 0.85
  hybrid_alpha: 0.7

filtering:
  min_importance: 1
  min_connections: 0
```

### 5.3 PDF 与多模态（可选）

```yaml
pdf:
  input_directory: ./文献
  chunk_size: 2000
  chunk_overlap: 200
  enable_image_captions: false # true 启用多模态
  caption_model: qwen2-vl
  max_images_per_pdf: 25
```

### 5.4 Neo4j 连接（导入脚本内部配置）

导入脚本会交互式询问：

```bash
python import_to_neo4j_final.py
# URI: bolt://localhost:7687
# 用户名: neo4j
# 密码: 12345678 (或自定义)
```

---

## 6. 知识图谱构建流程

### 6.1 流程概览

1. **PDF 文本抽取**：`pdf_extractor.py`
2. **文本清洗与分块**：按 `chunk_size` 切分，保留上下文
3. **概念与关系抽取**：`concept_extractor.py`，调用 Qwen2.5-Coder
4. **上下文共现关系增强**：ContextualProximityAnalyzer（可选）
5. **语义去重与实体对齐**：`concept_deduplicator.py` + BGE-M3
6. **重要性与连接度过滤**：ConceptImportanceFilter
7. **Checkpoint 与增量保存**：`CheckpointManager`
8. **输出 CSV**：`output/concepts.csv`、`output/relationships.csv`
9. **Neo4j 导入与索引**：`import_to_neo4j_final.py`
10. **GraphRAG 社区摘要（可选）**：`graph_rag.py` / `graph_summarizer.py`

### 6.2 主要脚本一览

| 脚本                        | 作用                             |
| --------------------------- | -------------------------------- |
| `start.sh`                  | 主入口脚本，一键运行安全管道     |
| `enhanced_pipeline_safe.py` | 安全版主流水线与 Checkpoint 管理 |
| `pdf_extractor.py`          | PDF 文本提取 + OCR               |
| `concept_extractor.py`      | LLM 概念与关系抽取               |
| `concept_deduplicator.py`   | 语义去重与实体对齐               |
| `import_to_neo4j_final.py`  | 导入 Neo4j，创建索引与样式       |
| `graph_rag.py`              | 基于 CSV 的社区检测与摘要        |
| `graph_summarizer.py`       | 基于 Neo4j 的 GraphRAG           |
| `simple_deduplicate.py`     | 不依赖 BGE-M3 的简单去重         |
| `test_imports.sh`           | 测试模块导入                     |
| `test_neo4j.py`             | 测试 Neo4j 连接                  |

---

## 7. Web 可视化应用

### 7.1 功能概览

- 交互式图谱浏览（拖拽、缩放、选中高亮）
- 按节点类型、重要性、连接度筛选
- 节点详情面板（名称、类别、度数、重要性等）
- 全局统计（节点数、关系数、类别分布）
- 基于 Neo4j 的实时数据

### 7.2 启动方式

**Docker（推荐）**

```bash
make quick-start
# 前端: http://localhost
# API:  http://localhost:8000/docs
# Neo4j: http://localhost:7474
```

**本地脚本**

```bash
# 已完成 CSV 导入 Neo4j 后
cd web
./start.sh

# 管理
./status.sh
./stop.sh
./restart.sh
```

---

## 8. DevOps 与 CI/CD

### 8.1 容器化与 Makefile

- `web/backend/Dockerfile`：FastAPI 后端镜像
- `web/frontend/Dockerfile`：React 前端多阶段构建镜像
- `docker-compose.yml`：Neo4j + Backend + Frontend 编排
- `.dockerignore`：根目录 + 前后端构建上下文优化
- `Makefile`：统一命令入口（构建、启动、测试、日志、清理等）

关键 Make 命令示意：

```bash
# 构建镜像
make build

# 生产模式启动
make up

# 开发模式（前端热更新）
make up-dev

# 测试与检查
make test
make lint

# 清理
make clean
make clean-all
make prune
```

详细说明见：`archive/docs/DOCKER_DEPLOYMENT.md`、`archive/docs/DEVOPS_SUMMARY.md`、`archive/docs/DEVOPS_IMPLEMENTATION_REPORT.md`。

### 8.2 GitHub Actions CI/CD

工作流文件：`.github/workflows/ci.yml`

典型阶段：

- 后端：Flake8、Black、Pytest、覆盖率上报
- 前端：ESLint、TypeScript 编译、构建检查
- 管道：根目录 Python 脚本静态检查
- Docker：构建后端/前端镜像，验证 `docker-compose config`
- 安全：Trivy 漏洞扫描
- 部署：构建并推送镜像到 Docker Hub（main 分支）

需要配置的 Secrets（示例）：

- `DOCKER_USERNAME` / `DOCKER_PASSWORD`
- `CODECOV_TOKEN`（可选）

本地模拟 CI 检查：

```bash
./scripts/local_ci_test.sh
```

详细说明见：`archive/docs/CI_CD_GUIDE.md`。

---

## 9. 性能与优化

系统针对长时间运行和内存占用进行了多轮优化：

- Checkpoint 增量保存，防止长任务中断导致数据丢失
- 语义去重与过滤在离线阶段进行，减轻在线负载
- 自动内存清理与资源监控脚本（`monitor_memory.py`、`cleanup_memory.sh`）
- 支持通过配置调整：
  - `chunk_size` / `max_chunks`
  - `num_ctx` / `parallel_workers`
  - 是否启用 Agentic、GraphRAG、多模态等可选模块

参考文档：

- `archive/docs/MEMORY_OPTIMIZATION.md`
- `archive/docs/OPTIMIZATION_SUMMARY.md`
- `archive/docs/FINAL_OPTIMIZATION_SUMMARY.md`
- `archive/docs/BATCH_PROCESSING_GUIDE.md`
- `archive/docs/BGE_M3_SPARSE_GUIDE.md`
- `archive/docs/PDF_CACHE_GUIDE.md`
- `archive/docs/AUTO_CLEANUP_GUIDE.md`

---

## 10. 常用命令速查表

### 10.1 知识图谱构建（本地）

```bash
./start.sh                 # 启动主流程
./status.sh                # 查看状态
./monitor.sh               # 实时监控（CPU/内存/进度）

./test_imports.sh          # 测试模块导入
python test_neo4j.py       # 测试 Neo4j 连接
python simple_deduplicate.py  # 简单去重
python scripts/model_benchmark.py  # 模型性能测试
```

### 10.2 Docker 与服务

```bash
./check_docker_env.sh      # 检查 Docker 环境
make quick-start           # 一键构建+启动
make up                    # 启动容器
make up-dev                # 开发模式
make down                  # 停止并移除容器
make restart               # 重启所有服务

make status                # 查看状态
make logs                  # 所有日志
make logs-backend          # 后端日志
make logs-frontend         # 前端日志
make logs-neo4j            # Neo4j 日志
```

### 10.3 Web 应用（非 Docker）

```bash
cd web
./start.sh                 # 启动 Web 应用
./status.sh                # 查看状态
./stop.sh                  # 停止
./restart.sh               # 重启
```

---

## 11. 故障排查

| 问题场景                   | 现象与日志片段                             | 处理建议                                                    |
| -------------------------- | ------------------------------------------ | ----------------------------------------------------------- |
| Docker 无法连接            | `Cannot connect to the Docker daemon`      | 启动 Docker Desktop / 守护进程                              |
| 拉取镜像超时               | 访问 Docker Hub 超时                       | 配置国内镜像加速器                                          |
| Ollama 连接失败            | `Connection refused` / 无法访问 11434 端口 | 运行 `ollama serve`，检查防火墙                             |
| 模型未找到                 | `model not found`                          | 运行 `ollama pull qwen2.5-coder`                            |
| JSON 解析失败              | 日志中出现 `JSON parse error`              | 降低 `temperature`，减小块大小                              |
| 内存/CPU 过高              | 系统卡顿、日志提示 OOM                     | 调整 `num_ctx`/`parallel_workers`，运行 `cleanup_memory.sh` |
| Neo4j 导入失败             | 连接错误或认证失败                         | 核对 URI/账号密码，确保服务已启动                           |
| 前端构建失败（TypeScript） | TS 编译错误                                | 根据错误提示修正前端类型                                    |
| Web 打不开或 404           | 前端容器未启动或端口被占用                 | 检查 `make status`，排查端口冲突                            |

更多细节参见：`archive/docs/DOCKER_DEPLOYMENT.md`、`archive/docs/CI_CD_GUIDE.md`、`archive/docs/MEMORY_OPTIMIZATION.md`、`docs/TECHNICAL_CHALLENGES.md`。

---

## 12. 贡献与许可证

### 12.1 贡献流程

1. Fork 仓库并创建分支：

   ```bash
   git checkout -b feature/your-feature
   ```

2. 配置本地环境并确保：

   ```bash
   ./test_imports.sh
   ./scripts/local_ci_test.sh
   ```

3. 提交代码时：

   - 使用语义化提交信息
   - 更新相关文档（如有）
   - 确保本地测试与 Lint 均通过

4. 提交 Pull Request，说明：
   - 变更目的
   - 主要修改点
   - 测试方式与结果

可参考：`.github/PULL_REQUEST_TEMPLATE.md`。

### 12.2 许可证

本项目采用 MIT 许可证，详见 `LICENSE` 文件。

---

## 13. 相关文档

- 部署与 DevOps
  - `archive/docs/DOCKER_DEPLOYMENT.md`：Docker 部署与运维手册
  - `archive/docs/CI_CD_GUIDE.md`：GitHub Actions 流程
  - `archive/docs/DEVOPS_SUMMARY.md` / `archive/docs/DEVOPS_IMPLEMENTATION_REPORT.md`：DevOps 实施总结
- 性能与优化
  - `archive/docs/MEMORY_OPTIMIZATION.md`
  - `archive/docs/OPTIMIZATION_SUMMARY.md`
  - `archive/docs/FINAL_OPTIMIZATION_SUMMARY.md`
  - `archive/docs/BATCH_PROCESSING_GUIDE.md`
  - `archive/docs/BGE_M3_SPARSE_GUIDE.md`
  - `archive/docs/PDF_CACHE_GUIDE.md`
  - `archive/docs/AUTO_CLEANUP_GUIDE.md`
- Web 与多模态
  - `web/PROJECT_STRUCTURE.md`
  - `web/SCRIPTS_USAGE.md`
  - `archive/docs/MULTIMODAL_IMAGE_GUIDE.md`
- 历史与技术细节
  - `archive/docs/IMPLEMENTATION_DETAILS.md`
  - `docs/TECHNICAL_CHALLENGES.md`
  - `archive/` 目录：旧版 README 与变更记录
