# <center>松材线虫病知识图谱构建系统</center>

<div align="center">

**基于文献的松材线虫病（Pine Wilt Disease, PWD）知识图谱自动化构建与可视化系统**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org)
[![Neo4j](https://img.shields.io/badge/Neo4j-4.x%20%7C%205.x-green.svg)](https://neo4j.com)
[![LLM](https://img.shields.io/badge/LLM-llama3.2:3B%20%7C%20Qwen2.5--Coder--7B-orange.svg)](https://ollama.com)
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
    - [最新改进](#最新改进)
      - [第一阶段：抽取与检索能力增强](#第一阶段抽取与检索能力增强)
      - [第二阶段：标准化、多模态与人机回环](#第二阶段标准化多模态与人机回环)
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

### 最新改进

下述改进已合并进主流程，不需要额外脚本。每一项都从三个角度说明：

- **功能**：解决什么问题
- **实现位置**：涉及的脚本 / 类
- **使用方式与配置**：如何在现有流程中启用或调整

#### 第一阶段：抽取与检索能力增强

- **滑动窗口上下文机制**（`concept_extractor.py`）

  - **功能**：在按 chunk 处理 PDF 时，引入前文实体作为上下文，减轻代词、省略、简称导致的实体不一致和跨段关系缺失问题。
  - **实现位置**：`ConceptExtractor.extract_from_chunks`
    - 新参数：
      - `use_context_window: bool = True` 是否启用滑动窗口；
      - `context_window_size: int = 5` 维护的“核心实体”数量。
    - 工作方式：
      - 每处理完一个 chunk，从该块抽取的概念中选取 `importance >= 4` 的实体加入 `context_entities`；
      - 处理下一个 chunk 时，在 LLM prompt 末尾自动追加：
        `前文提到的核心实体: 松材线虫, 松褐天牛, 马尾松`，并提示“保持实体名称一致性”。
  - **使用方式**：
    - 默认启用：`extract_from_chunks(chunks)`；
    - 禁用：`extract_from_chunks(chunks, use_context_window=False)`；
    - 建议：`context_window_size=5`，长文且上下文连贯性要求高时可调大到 8–10。
  - **相关配置**：`config/config.yaml` 中 `improvements.context_window.*`。

- **层级本体 Label**（`import_to_neo4j_final.py`）

  - **功能**：在 Neo4j 中为节点附加多级 Label，例如 `(:Pathogen:Organism:Concept)`，支持从“病原/寄主/媒介”等类型向生物、概念等上位类聚合查询。
  - **实现位置**：
    - 本体映射：`type_hierarchy = { 'Pathogen': ['Organism', 'Concept'], 'Host': ['Plant', 'Organism', 'Concept'], ... }`；
    - 创建节点时，将 `node_type` 与其父类展开为多 Label，例如：
      - `(:Pathogen:Organism:Concept { primary_label: 'Pathogen', all_labels: [...] })`。
    - 索引：`CREATE INDEX node_primary_label IF NOT EXISTS FOR (n) ON (n.primary_label)`。
  - **查询示例**：
    - 所有生物：`MATCH (n:Organism) RETURN n`；
    - 所有植物：`MATCH (n:Plant) RETURN n`；
    - 生物-生物关系：`MATCH (o1:Organism)-[r]->(o2:Organism) RETURN o1,r,o2`；
    - 所有防治方法：`MATCH (n:Treatment) RETURN n`；
    - 查看节点 Label：`MATCH (n) RETURN n.name, labels(n) LIMIT 10`。
  - **相关配置**：`config/config.yaml` 中 `improvements.hierarchical_ontology.*`。

- **Local Search 精确检索**（`graph_rag.py`）

  - **功能**：在社区摘要（全局 GraphRAG）之外，提供基于节点向量索引的精细问答能力，适合“某个药剂对某个媒介有什么作用”这类问题。
  - **核心类**：
    - `LocalSearchEngine`：
      - `build_node_index(concepts_df)`：使用 BGE-M3 为每个概念生成向量；
      - `search_relevant_nodes(query, top_k)`：向量检索 Top-K 相关节点；
      - `expand_subgraph(seed_nodes, relationships_df, max_hops)`：从种子节点扩展 1–2 跳子图；
      - `answer_query(query, concepts_df, relationships_df, ...)`：对检索到的子图调用 LLM 生成答案。
    - `GraphRAG`：
      - `build_local_search_index(concepts_df)`：构建索引；
      - `local_search(query, concepts_df, relationships_df, top_k=5, max_hops=2)`：本地精确检索统一入口。
  - **典型用法**：
    - 离线阶段：
      - `graph_rag = GraphRAG(model="llama3.2:3b", embedding_model="BAAI/bge-m3")`
      - `graph_rag.build_local_search_index(concepts_df)`
    - 在线查询：
      - `result = graph_rag.local_search("阿维菌素对松褐天牛有什么作用？", concepts_df, relationships_df)`
      - `result` 中包含：`relevant_nodes`（实体+相似度）、`subgraph_size`、`answer`（LLM 输出）。
  - **相关配置**：`config/config.yaml` 中 `improvements.local_search.*`；示例脚本见 `examples/local_search_demo.py`。

#### 第二阶段：标准化、多模态与人机回环

- **实体消歧与链接（CanonicalResolver）**（`concept_deduplicator.py`）

  - **功能**：在 Embedding 聚类之前，优先用规则和外部知识库把常见别名对齐到标准名称，保证图谱中生物名、病名、药剂名的一致性。
  - **核心类**：`CanonicalResolver`
    - 内置字典：
      - 生物分类名：如 `松材线虫 → Bursaphelenchus xylophilus`，`松褐天牛 → Monochamus alternatus`，`马尾松 → Pinus massoniana` 等；
      - 疾病名：`松材线虫病 / 松树萎蔫病 → Pine Wilt Disease`；
      - 药剂名：`阿维菌素 → Avermectin` 等。
    - 方法：
      - `resolve(entity, category=None) -> canonical_name`：优先规则匹配，其次（可选）外部知识库，最后回退到原名；
      - `batch_resolve(entities, categories=None)`：批量解析；
      - `add_custom_mapping(original, canonical)`：添加自定义别名映射。
  - **与去重流程的集成**：
    - `ConceptDeduplicator.__init__(..., use_canonical_resolver=True, use_external_kb=False)` 默认启用；
    - `deduplicate_concepts` 中先应用 `CanonicalResolver` 做规则对齐，再对剩余实体做 Embedding 聚类去重。
  - **相关配置**：`config/config.yaml` 中 `improvements_phase2.entity_linking.*`（包括是否启用外部知识库、超时时间等）。

- **多模态深度融合（图片 ↔ 概念）**（`multimodal_graph_builder.py`）

  > **当前状态**：✅ 已完整实现（后端 API + 前端 UI）。节点详情面板会自动显示相关图片。

  - **功能**：把 `image_captioner.py` 生成的图片描述接入图谱，为每张图片创建 `:Image` 节点，并通过 `(:Concept)-[:ILLUSTRATED_BY]->(:Image)` 关系将图片与概念关联，在查询和 GraphRAG 中同时返回文本与图片线索。
  - **核心类**：`MultimodalGraphBuilder`
    - `load_image_captions(caption_file)`：加载 JSON 格式的图片与描述；
    - `extract_concepts_from_captions(images_df, concept_extractor)`：复用现有 LLM，从 caption 中抽取概念；
    - `build_image_concept_relationships(image_concepts_df, concepts_df)`：仅保留已在主图中的概念，建立配对关系；
    - `export_to_csv(images_df, image_concept_rels_df)`：输出 `images.csv` 与 `image_concept_relationships.csv` 供 Neo4j 导入；
    - `generate_neo4j_import_statements(...)`：生成创建 `:Image` 节点与 `ILLUSTRATED_BY` 关系的 Cypher 语句。
  - **多模态检索**：`MultimodalRetriever`
    - 基于 `image_concept_relationships.csv` 构建 `concept → [images...]` 索引；
    - `retrieve_images_for_concepts(concepts, max_images_per_concept)`：按概念召回图片，用于 GraphRAG 和 Web 前端展示。
    - `config/config.yaml` 中 `pdf.enable_image_captions`、`pdf.caption_model`；
    - `config/config.yaml` 中 `improvements_phase2.multimodal.*`。

- **人机回环纠错（Human-in-the-loop）**（`human_feedback_manager.py` + Web API）

  > **当前状态**：✅ 已完整实现（后端 API + 前端 UI）。节点详情面板提供"建议实体合并"和"报告缺失关系"按钮。

  - **功能**：允许用户对错误的实体/关系进行标注和纠正，将这些反馈汇总为"错题集"，后续用于 Prompt 优化或小模型微调。
  - **前端入口**：在节点详情面板底部"反馈与纠错"区域，点击相应按钮即可提交反馈。
  - **核心类**：`HumanFeedbackManager`
    - 支持反馈类型（部分）：
      - 关系方向错误：`relation_direction_error`（如 A→B 实际应为 B→A）；
      - 关系类型错误：`relation_type_error`；
      - 实体合并建议：`entity_merge`（两种写法应归并到同一标准名）；
      - 缺失关系：`missing_relation`；
      - 虚假关系：`spurious_relation` 等。
    - 主要方法：
      - `record_relation_direction_error(...)` / `record_relation_type_error(...)` / `record_entity_merge(...)` / `record_missing_relation(...)`：将单条反馈以 JSONL 追加到 `output/human_feedback.jsonl`；
      - `generate_feedback_report()`：按类型/用户统计反馈情况；
      - `get_error_patterns()`：分析常见方向错误、类型混淆、常见合并建议；
      - `export_training_data()`：把反馈转成 `input/output` 对，用于 Prompt 或小模型微调。
  - **后端 API（FastAPI）**：`web/backend/app/routers/feedback.py`
    - 关系方向纠错：`POST /api/feedback/relation-direction`；
    - 关系类型纠错：`POST /api/feedback/relation-type`；
    - 实体合并建议：`POST /api/feedback/entity-merge`；
    - 缺失关系反馈：`POST /api/feedback/missing-relation`；
    - 查看统计：`GET /api/feedback/report`；
    - 查看错误模式：`GET /api/feedback/error-patterns`；
    - 导出训练数据：`POST /api/feedback/export-training-data`。
  - **多模态 API**：`web/backend/app/routers/multimodal.py`
    - 按概念检索图片：`POST /api/multimodal/retrieve-images`；
    - 查询某个概念的图片：`GET /api/multimodal/concept/{concept_name}/images`；
    - 访问图片文件：`GET /api/multimodal/image/{image_path}`；
    - 查看多模态数据统计：`GET /api/multimodal/stats`。

> 具体实现细节可直接查看对应 Python 文件；README 聚焦于整体架构、功能概览和配置入口。

---

## 2. 技术栈与系统架构

### 2.1 技术栈

| 模块      | 技术                        | 用途                       |
| --------- | --------------------------- | -------------------------- |
| LLM       | llama3.2:3B / Qwen2.5-Coder | 概念和关系抽取             |
| Embedding | BGE-M3                      | 语义去重与实体对齐         |
| 图数据库  | Neo4j 5.x                   | 知识图谱存储与查询         |
| 后端 API  | FastAPI + Uvicorn           | 图谱查询 REST API          |
| 前端      | React 19 + Vite + TS        | 图谱可视化界面             |
| 可视化    | Cytoscape.js                | 交互式网络图               |
| 样式      | Tailwind CSS                | UI 设计                    |
| 容器化    | Docker + Compose            | 一键部署与环境隔离         |
| CI/CD     | GitHub Actions              | 自动化测试、构建与镜像推送 |

### 2.2 系统架构概览

```text
PDF 文献
  ↓
[文本提取]  pdf_extractor.py (PyMuPDF + OCR)
  ↓
[文本分块]  chunk_size / overlap
  ↓
[LLM 抽取]  concept_extractor.py (Ollama LLM，默认 llama3.2:3b，可选 Qwen2.5-Coder)
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

# 安装并启动 Ollama（以 macOS 为例）
brew install ollama
ollama serve

# 拉取推荐模型（默认使用）
ollama pull llama3.2:3b

# 可选：拉取 Qwen2.5-Coder 作为备选模型
ollama pull qwen2.5-coder:7b
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

LLM 相关配置位于 `config/config.yaml`：

```yaml
llm:
  # 默认使用轻量模型，内存占用更低
  model: llama3.2:3b

  # 备选模型列表（按顺序回退）
  fallback_models:
    - llama3.2:3b
    - qwen2.5-coder:7b

  ollama_host: http://localhost:11434
  timeout: 900 # 秒
  num_ctx: 2048 # LLM 上下文窗口
  temperature: 0.1 # 采样温度
  max_chunks: null # null 表示处理全部块
```

如需切换回 Qwen2.5-Coder，可将 `model` 改为 `qwen2.5-coder:7b`，同时确保已通过 `ollama pull` 拉取对应模型。

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

  # 多模态图片描述（关闭时不做图片抽取）
  enable_image_captions: false # 资源有限时建议关闭
  image_output_dir: ./output/pdf_images
  caption_model: llava:7b # 通过 Ollama 提供的多模态模型
  max_images_per_pdf: 20 # 每篇文献的最大图片数
```

启用多模态时，需要：

- 使用 `ollama pull llava:7b` 预先下载模型；
- 将 `enable_image_captions` 设为 `true`；
- 根据机器性能适当调低 `max_images_per_pdf`。

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
3. **概念与关系抽取**：`concept_extractor.py`，调用通过 Ollama 提供的 LLM（默认 `llama3.2:3b`）
4. **上下文共现关系增强**：ContextualProximityAnalyzer（可选）
5. **语义去重与实体对齐**：`concept_deduplicator.py` + BGE-M3
6. **重要性与连接度过滤**：ConceptImportanceFilter
7. **Checkpoint 与增量保存**：`CheckpointManager`
8. **输出 CSV**：`output/concepts.csv`、`output/relationships.csv`
9. **Neo4j 导入与索引**：`import_to_neo4j_final.py`
10. **GraphRAG 社区摘要（可选）**：`graph_rag.py` / `graph_summarizer.py`

### 6.2 主要脚本一览



| --------------------------- | ------------ | -------------------------------- |
| `start.sh`                  | ✅ **推荐**  | 主入口脚本，一键运行安全管道     |
| `enhanced_pipeline_safe.py` | ✅ **推荐**  | 安全版主流水线与 Checkpoint 管理 |
| `pdf_extractor.py`          | ✅ 核心模块  | PDF 文本提取 + OCR               |
| `concept_extractor.py`      | ✅ 核心模块  | LLM 概念与关系抽取               |
| `concept_deduplicator.py`   | ✅ 核心模块  | 语义去重与实体对齐               |
| `import_to_neo4j_final.py`  | ✅ 核心模块  | 导入 Neo4j，创建索引与样式       |
| `graph_rag.py`              | ✅ 可选功能  | 基于 CSV 的社区检测与摘要        |
| `graph_summarizer.py`       | ✅ 可选功能  | 基于 Neo4j 的 GraphRAG           |
| `run_pipeline.py`           | 🔄 旧版/示例 | 旧版管线入口（保留作参考）       |
| `enhanced_pipeline.py`      | 🔄 旧版/示例 | 旧版管线（保留作参考）           |
| `simple_deduplicate.py`     | 🔄 可选      | 不依赖 BGE-M3 的简单去重         |
| `test_imports.sh`           | 🧪 测试工具  | 测试模块导入                     |
| `test_neo4j.py`             | 🧪 测试工具  | 测试 Neo4j 连接                  |

**状态说明**：

- ✅ **推荐** - 日常使用的主入口
- ✅ 核心模块 - 系统核心功能
- ✅ 可选功能 - 根据需求选用
- 🔄 旧版/示例 - 保留作参考，不推荐直接使用
- 🧪 测试工具 - 开发和调试用

---

## 7. Web 可视化应用

### 7.1 功能概览

- **交互式图谱浏览**：拖拽、缩放、选中高亮
- **节点筛选**：按节点类型、重要性、连接度筛选
- **智能问答（GraphRAG）**：✨ 新增
  - 自然语言提问
  - Local Search 精确检索
  - LLM 生成答案
  - 相关节点高亮
- **节点详情面板**：
  - 基本信息（名称、类别、度数、重要性等）
  - 相关图片展示（多模态功能）
  - 反馈与纠错按钮（人机回环功能）
- **全局统计**：节点数、关系数、类别分布
- **实时数据**：基于 Neo4j 的实时查询

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
| 模型未找到                 | `model not found`                          | 运行 `ollama pull llama3.2:3b` 或对应模型名                 |
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

- **新功能说明** ✨
  - `docs/NEW_FEATURES_GRAPHRAG_CONFIG.md`：GraphRAG 问答 + 领域配置外置化
  - `docs/CONFIG_REFACTORING.md`：配置系统重构 + 多环境支持
  - `web/frontend/NEW_FEATURES.md`：前端人机回环 + 多模态 UI
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
- 配置与工具
  - `config/domain_dict.json`：实体别名映射配置
  - `config/type_hierarchy.json`：类型层级配置
  - `tools/validate_domain_config.py`：配置验证工具
  - `tools/domain_config_loader.py`：配置加载工具
- 历史与技术细节
  - `archive/docs/IMPLEMENTATION_DETAILS.md`
  - `docs/TECHNICAL_CHALLENGES.md`
  - `archive/` 目录：旧版 README 与变更记录
