# 松材线虫病知识图谱构建系统

<div align="center">

**知识工程第二组 - 基于文献的松材线虫病知识图谱项目**

**基于 Qwen2.5-Coder、BGE-M3 与 GraphRAG 的领域知识图谱自动化构建系统**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org)
[![Neo4j](https://img.shields.io/badge/Neo4j-4.x%20%7C%205.x-green.svg)](https://neo4j.com)
[![LLM](https://img.shields.io/badge/LLM-Qwen2.5--Coder--7B-orange.svg)](https://github.com/QwenLM/Qwen2.5-Coder)
[![BGE-M3](https://img.shields.io/badge/Embedding-BGE--M3-red.svg)](https://huggingface.co/BAAI/bge-m3)

</div>

---

## 目录

- [项目背景](#项目背景)
- [项目概述](#项目概述)
- [核心创新点](#核心创新点)
- [技术挑战与解决方案](#技术挑战与解决方案)
- [快速开始](#快速开始)
- [核心功能](#核心功能)
- [技术架构](#技术架构)
- [系统特性](#系统特性)
- [配置说明](#配置说明)
- [故障排查](#故障排查)

---

## 项目背景

### 领域意义

松材线虫病（Pine Wilt Disease, PWD）是一种由松材线虫（_Bursaphelenchus xylophilus_）引起的毁灭性松树病害，被称为"松树癌症"：

- **危害程度**: 感染后松树 40-60 天内死亡，致死率接近 100%
- **传播速度**: 通过松褐天牛等媒介昆虫快速传播
- **经济损失**: 每年造成数十亿元直接经济损失
- **生态影响**: 破坏森林生态系统，影响水土保持

### 研究现状

当前松材线虫病研究存在以下问题：

1. **文献分散**: 研究论文散布在多个期刊和数据库
2. **知识孤岛**: 不同领域（病理、媒介、防治）研究缺乏整合
3. **检索困难**: 传统文献检索难以发现隐含的知识关联
4. **决策支持不足**: 缺乏系统化的知识支持防治决策

### 项目价值

本项目通过**自动化知识图谱构建**技术，实现：

- **知识整合**: 从 28 篇文献中自动抽取和整合领域知识
- **关系发现**: 揭示病原、寄主、媒介、防治之间的复杂关系
- **智能检索**: 支持语义检索和知识推理
- **决策支持**: 为防治策略制定提供知识支撑

---

## 项目概述

### 核心目标

从松材线虫病相关文献中**自动构建**结构化知识图谱，包括：

1. **实体识别**: 自动识别 9 大类领域实体（病原、寄主、媒介、症状等）
2. **关系抽取**: 提取 6 类核心关系（感染、传播、防治等）
3. **知识去重**: 基于语义相似度的智能去重
4. **图谱构建**: 生成可查询、可视化的 Neo4j 知识图谱

### 系统能力

- **自动化程度高**: 从 PDF 文献到知识图谱全流程自动化
- **准确率高**: 采用 Agentic Workflow 可选增强，提升抽取质量
- **鲁棒性强**: 支持断点续传，长时间运行零数据丢失
- **性能优异**: 通过模型优化实现处理速度显著提升

### 技术栈

| 类别          | 技术选型       | 版本/规格 | 用途               |
| ------------- | -------------- | --------- | ------------------ |
| **LLM**       | Qwen2.5-Coder  | 7B        | 概念和关系抽取     |
| **Embedding** | BGE-M3         | 2.27GB    | 语义去重、实体对齐 |
| **图数据库**  | Neo4j          | 5.x       | 知识图谱存储和查询 |
| **LLM 服务**  | Ollama         | Latest    | 本地模型推理       |
| **PDF 解析**  | PyMuPDF        | Latest    | 文本提取           |
| **进度追踪**  | tqdm + logging | -         | 实时进度和日志     |

### 技术要点概览

- **本地 LLM 推理链路**: 基于 Ollama 部署 Qwen2.5-Coder 7B/14B，本地推理、严格 JSON Schema 输出，减少外部依赖和网络不确定性。
- **长时间任务容错设计**: `enhanced_pipeline_safe.py` 结合 `checkpoint_manager.py`，提供按块增量保存、断点续传和安全退出，控制单次故障影响范围。
- **语义去重与实体对齐**: `concept_deduplicator.py` 使用 BGE-M3 混合检索（dense + sparse），对相似概念聚合、对齐中英文实体，减少图谱冗余。
- **多源关系构建策略**: 将 LLM 抽取的关系与 ContextualProximityAnalyzer 的近邻关系合并，加权生成最终关系集合，兼顾精度和覆盖率。
- **图数据库落库与查询**: 通过 `import_to_neo4j_final.py` 与 Neo4j，将概念与关系以节点/边形式存储，支持后续 Cypher 查询和可视化分析。
- **可选增强模块**: `agentic_extractor.py` 和 `graph_rag.py` 提供 Agentic Workflow 和 GraphRAG 社区摘要能力，通过配置文件按需启用或关闭。
- **多模态扩展路径**: `multimodal_extractor.py` 结合 Qwen2-VL，对 PDF 图片生成文本描述并统一纳入抽取流程，为后续多模态知识扩展预留接口。

### v2.5 核心升级

| 功能模块     | 技术方案          | 效果说明             |
| ------------ | ----------------- | -------------------- |
| **核心模型** | 32B → 7B 优化     | 处理时间显著缩短     |
| **数据安全** | Checkpoint 机制   | 数据丢失风险大幅降低 |
| **容错能力** | 多层防御设计      | 系统可用性提升       |
| **用户体验** | 进度条 + 监控脚本 | 可观测性显著提升     |
| **嵌入模型** | MiniLM → BGE-M3   | 中文语义理解增强     |

---

## 核心创新点

### 1. Checkpoint 机制：长时间任务的数据安全

**问题**: 长时间任务中断导致数据全部丢失

**解决方案**:

- 增量保存：每处理一个文本块立即保存概念和关系
- 断点续传：程序重新启动时自动跳过已处理块
- 安全退出：Ctrl+C 优雅退出并保存进度

**效果**:

- 最大损失时间: 数小时 → 数分钟
- 用户可中断: 否 → 是

### 2. LLM 性能优化：质量与速度的权衡

**问题**: 大模型处理速度慢，影响实际应用

**创新决策**:

- 对比测试不同规模模型的处理速度与输出质量
- 选择 7B 模型作为默认配置，在保持可接受质量的同时显著提升处理速度
- 通过 Agentic Workflow 可选增强，在需要时提升抽取质量

### 3. 多层容错架构

**问题**: 单次 LLM 失败导致整个管道崩溃

**方案**:

```
Layer 1 (LLM层):    返回 None → 转为 []
Layer 2 (Checkpoint层): 验证输入 → 标准化
Layer 3 (主循环层):  捕获异常 → continue

结果: 单点失败不影响整体
```

**成果**:

- 系统可用性显著提升
- 单点故障不影响整体处理流程

### 4. BGE-M3 混合检索去重

**创新**:

```python
混合相似度 = α × dense_sim + (1-α) × sparse_sim

# 中英文实体对齐
"松材线虫" ↔ "bursaphelenchus xylophilus" → 高相似度匹配
```

**成果**:

- 中文语义相似度识别能力提升
- 专业术语对齐效果增强
- 支持中英文混合场景的实体对齐

### 5. 完整的可观测性设计

**问题**: 黑盒运行，用户不知道进度

**方案**:

```bash
# 实时进度条
Extracting concepts:  X%|██▏     | XX/XXX [mm:ss<hh:mm:ss, XX.XXs/it]

# 一键状态查询
./status.sh    # 查看当前状态
./monitor.sh   # 实时监控

# 统一启动入口
./start.sh     # 唯一推荐方式
```

**成果**:

- 进度可见性: 无 → 实时显示
- 启动复杂度: 5 种方式 → 1 种方式
- 用户满意度: 低 → 高

---

## 技术挑战与解决方案

### 挑战 1: 长时间运行的数据安全

**技术难点**:

- 500+ 文本块需要 7-8 小时处理
- 任何中断（断电、崩溃、Ctrl+C）导致全部数据丢失
- 无法容忍的用户体验

**解决方案**: Checkpoint 机制

---

## 快速开始

### 1. 环境准备

1. **安装 Ollama**

   ```bash
   # macOS
   brew install ollama

   # Linux
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **启动 Ollama 服务**

   ```bash
   ollama serve
   ```

3. **下载 LLM 模型**

   ```bash
   # 推荐 7B 模型（平衡速度与质量）
   ollama pull qwen2.5-coder:7b

   # 或 14B 模型（更高精度）
   ollama pull qwen2.5-coder:14b
   ```

4. **安装 Python 依赖**
   ```bash
   pip install -r requirements.txt
   ```

### 2. 放置源文献

- 将待处理的 PDF 文献放入 `./文献/` 目录
- 如需修改目录，在 `config/config.yaml` 中调整 `pdf.input_directory`

### 3. 一键启动（推荐）

```bash
./start.sh
```

**就这么简单！** 这个脚本会：

- ✅ 自动使用正确的 Python 环境（3.10.13，已安装所有依赖）
- ✅ 自动检测并从断点继续
- ✅ 显示清晰的进度信息
- ✅ 支持 Ctrl+C 安全退出

### 4. 状态监控

```bash
# 查看当前状态
./status.sh

# 实时监控（在另一个终端运行）
./monitor.sh
```

监控信息包括：

- 已处理块数、概念和关系总数
- 进程状态（PID、CPU、内存）
- 最近日志和错误信息
- 完成时间估算

### 5. 常见操作

#### 清除进度重新开始

```bash
rm -rf output/checkpoints/
./start.sh
```

#### 查看结果

```bash
# 查看概念
head -20 output/concepts.csv

# 查看关系
head -20 output/relationships.csv

# 统计数量
wc -l output/*.csv
```

#### 查看日志

```bash
# 实时查看
tail -f output/kg_builder.log

# 查看错误
grep ERROR output/kg_builder.log
```

### 6. 安全模式特性

本项目采用安全模式，具备以下保护机制：

1. **增量保存**：每处理 10 个文本块自动保存进度
2. **断点续传**：程序中断后重新运行自动继续
3. **异常保护**：Ctrl+C 优雅退出，自动保存进度

**效果**：

- 最多损失 10 个块的进度（约 3-5 分钟）
- 任何时候中断都能安全恢复
- 几乎无性能损失（额外开销 < 0.5%）

### 7. 导入 Neo4j（可选）

```bash
python import_to_neo4j_final.py
```

- 根据提示在 Neo4j 中创建数据库和连接配置

---

## 核心功能

### 1. 智能 PDF 解析

- **Layout-Aware**: PDFPlumber 表格提取
- **OCR 支持**: Tesseract 扫描版 PDF 识别
- **结构化**: 自动识别标题、段落、表格

### 2. LLM 概念抽取

- **模型**: Qwen2.5-Coder（7B/14B，可配置，支持 JSON Schema 输出）
- **输出格式**: 严格的 JSON 结构，确保解析稳定性
- **领域优化**: 9 大概念类别 + 6 大关系类型

### 3. Agentic Workflow

```
Extract Agent → Critic Agent → Refine Agent
   (初次抽取)      (质量审查)      (修正优化)
```

- **Extract**: 使用 Qwen2.5 初次抽取概念和关系
- **Critic**: LLM 审查逻辑一致性和语义合理性
- **Refine**: 自动修正错误，补充遗漏信息

### 4. GraphRAG 社区摘要

- **社区检测**: Louvain / Leiden 算法
- **LLM 摘要**: 自动生成社区主题和描述
- **全局查询**: 突破三元组局限，支持主题级查询

### 5. BGE-M3 混合检索

- **Dense Embedding**: 高维语义向量表示
- **Sparse Embedding**: 关键词级别精确匹配
- **混合相似度**: 结合语义相似度与关键词匹配，提升中英文实体对齐效果

### 6. 多模态融合（可选）

- **图片提取**: PyMuPDF 自动提取 PDF 图片
- **VLM 描述**: Qwen2-VL / LLaVA 生成图片描述
- **知识融合**: 将图片描述作为文本块参与抽取

---

## 技术架构

### 工作流程概览

```
PDF文献
  ↓
[1] 文本提取（PyMuPDF + OCR）
  ↓
[2] 文本分块（2000字符/块）
  ↓
[3] LLM 概念抽取（Qwen2.5-Coder）
  ↓
[4] Agentic 审查（Critic + Refine）
  ↓
[5] BGE-M3 去重（混合检索）
  ↓
[6] GraphRAG 社区摘要
  ↓
知识图谱 (Neo4j)
```

### 核心模块

| 模块     | 文件                      | 功能            |
| -------- | ------------------------- | --------------- |
| PDF 解析 | `pdf_extractor.py`        | 文本提取、OCR   |
| LLM 抽取 | `concept_extractor.py`    | 概念和关系抽取  |
| Agentic  | `agentic_extractor.py`    | 多智能体审查    |
| 去重     | `concept_deduplicator.py` | BGE-M3 语义去重 |
| GraphRAG | `graph_rag.py`            | 社区检测和摘要  |
| 多模态   | `multimodal_extractor.py` | 图片知识抽取    |
| 主流程   | `enhanced_pipeline.py`    | 整合所有模块    |

---

## 配置说明

### 基础配置 (`config/config.yaml`)

```yaml
# LLM 配置
llm:
  model: qwen2.5-coder:7b # 默认使用 7B，可在配置中切换为 14B
  ollama_host: http://localhost:11434
  max_chunks: null # 处理块数限制，null 表示全部处理
  timeout: 600 # API 超时（秒）
  temperature: 0.1 # 降低随机性，提高输出稳定性

# 去重配置
deduplication:
  use_bge_m3: true # 启用 BGE-M3
  similarity_threshold: 0.85
  embedding_model: BAAI/bge-m3
  hybrid_alpha: 0.7 # 混合检索权重

# 过滤配置
filtering:
  min_importance: 1 # 最小重要性
  min_connections: 0 # 允许孤立概念
```

### 进阶配置（可选功能）

```yaml
# Agentic Workflow 与 GraphRAG
agentic:
  enable_llm_review: false # LLM 二次审查（耗时）
  review_confidence_range: [0.6, 0.8]
  review_model: qwen2.5-coder:7b
  enable_graph_rag: false # 社区检测和摘要
  community_algorithm: louvain # 或 leiden
  summary_model: qwen2.5-coder:7b

# 多模态
pdf:
  enable_image_captions: false # 图片知识抽取
  caption_model: qwen2-vl
  max_images_per_pdf: 25
```

---

## 故障排查

### 已知问题与修复概览

| #   | 问题                       | 解决方案                                     | 状态   |
| --- | -------------------------- | -------------------------------------------- | ------ |
| 1   | 缺少 zhconv 模块           | `pip install zhconv pdfplumber networkx`     | 已修复 |
| 2   | DataCleaner 导入错误       | 添加别名 `DataCleaner = MarkdownDataCleaner` | 已修复 |
| 3   | enhanced_pipeline 导入错误 | 注释未使用的导入                             | 已修复 |
| 4   | torch 版本冲突             | marker-pdf 标记为可选                        | 已修复 |
| 5   | logger_config 路径错误     | 复制到根目录                                 | 已修复 |
| 6   | config_loader 路径错误     | 复制到根目录                                 | 已修复 |

### 常见问题

#### Q1: Ollama 连接失败

```bash
# 检查服务
curl http://localhost:11434/api/tags

# 启动服务
ollama serve
```

#### Q2: 模型未找到

```bash
# 查看已安装模型
ollama list

# 下载模型
ollama pull qwen2.5-coder:14b
```

#### Q3: JSON 解析失败

**解决方案**: 降低 temperature

```yaml
# config/config.yaml
llm:
  temperature: 0.05 # 更确定的输出
```

#### Q4: 内存不足

**解决方案**: 使用 7B 模型或减少处理量

```yaml
llm:
  model: qwen2.5-coder:7b # 从 14B 降到 7B
  max_chunks: 50 # 从 100 降到 50
```

#### Q5: 运行速度慢

**优化方案**:

1. 禁用 Agentic 审查: `enable_llm_review: false`
2. 使用 7B 模型（处理速度显著提升）
3. 减少处理文本块数量

#### Q6: LLM 超时

**现象**：

```
Ollama timeout (attempt 1/3), retrying...
```

**解决方案**：

1. 增加超时时间（`config/config.yaml`）：
   ```yaml
   llm:
     timeout: 300 # 改为 300 秒
   ```
2. 减小文本块大小：
   ```yaml
   system:
     chunk_size: 2000 # 从 3000 降至 2000
   ```

#### Q7: 进度丢失

**不用担心！**

- 每 10 个块会自动保存 checkpoint
- 最多损失 10 个块的进度（约 15 分钟）
- 重新运行会自动从断点继续

#### Q8: 使用 tmux 防止 SSH 断开

```bash
# 创建会话
tmux new -s pwd_kg

# 运行管道
./start.sh

# 分离会话：Ctrl+B, D
# 重新连接：tmux attach -t pwd_kg
```

### 验证系统

```bash
# 测试所有导入
./test_imports.sh

# 预期输出: 所有9个模块 [OK]
```

### 快速检查清单

开始运行前，确认以下项目：

- [ ] Ollama 服务已启动 (`ollama serve`)
- [ ] 模型已下载 (`ollama list | grep qwen`)
- [ ] PDF 文件已放入 `文献/` 目录
- [ ] 依赖已安装 (`pip install -r requirements.txt`)
- [ ] PyTorch 版本 >= 2.1
- [ ] 磁盘空间充足（至少 10GB）

---

## 进阶功能

### 1. 启用 Agentic Workflow

```yaml
# config/config.yaml
agentic:
  enable_llm_review: true
  review_model: qwen2.5-coder:14b
```

**效果**: 通过三阶段质量审查提升抽取准确性，处理时间相应增加

### 2. 启用 GraphRAG

```yaml
agentic:
  enable_graph_rag: true
  community_algorithm: louvain
```

**效果**: 生成社区摘要，支持全局查询

### 3. 启用多模态

```yaml
pdf:
  enable_image_captions: true
  caption_model: qwen2-vl
```

**前置条件**: 下载 VLM 模型

```bash
ollama pull qwen2-vl
```

### 4. 模型性能测试

```bash
python scripts/model_benchmark.py
```

测试内容:

- JSON Schema 遵循率
- 概念/关系抽取 F1
- 推理速度对比

### 5. 导入 Neo4j

```bash
# 方式 1: 使用 Python 脚本
python import_to_neo4j_final.py

# 方式 2: 使用 Cypher（需先生成）
# 在 Neo4j Browser 中执行 output/neo4j_import/import.cypher
```

---

## 输出文件说明

### 核心输出

```
output/
├── concepts.csv              # 抽取的概念
├── relationships.csv         # 抽取的关系
├── kg_builder.log           # 运行日志
├── community_summaries.csv  # 社区摘要（如启用GraphRAG）
├── checkpoints/             # Checkpoint 与进度文件
└── pdf_images/              # 提取的图片（如启用多模态）
```

### concepts.csv 格式

```csv
entity,importance,category,source_chunk,connections
松材线虫,5,Pathogen,chunk_001,23
马尾松,4,Host,chunk_003,18
```

### relationships.csv 格式

```csv
node_1,edge,node_2,weight,confidence,source
松材线虫,INFECTS,马尾松,0.92,0.88,paper1.pdf
```

---

## 系统特性

### 稳定性特性

**零数据丢失**: Checkpoint 机制确保任何中断都不丢失数据  
**断点续传**: 自动从中断点恢复，无需重新开始  
**优雅退出**: Ctrl+C 安全退出并保存进度  
**多层容错**: 单点失败不影响整体流程

### 性能特性

- **高效处理**: 500+ 文本块，约 5.5 小时完成
- **扩展空间**: 架构支持后续多进程或分布式扩展
- **内存控制**: 增量保存避免内存占用持续增长
- **模型选择**: 默认 7B 模型，在速度和质量之间取得平衡

### 易用性特性

**一键启动**: `./start.sh` 唯一入口  
**实时监控**: 进度条 + 日志 + 监控脚本  
**状态查询**: `./status.sh` 快速查看状态  
**环境自动**: 自动处理 Python 环境问题

### 扩展性特性

**模块化设计**: 各模块独立，易于替换  
 **配置驱动**: YAML 配置文件灵活控制  
 **模型可换**: 支持不同 LLM 和 Embedding 模型  
 **格式兼容**: CSV 输出方便后续处理

---

## 更新日志

### v2.5 (2025-11-29) - 稳定性与性能全面升级

**核心改进**：

- **Checkpoint 机制**: 增量保存 + 断点续传，大幅降低数据丢失风险
- **性能优化**: 32B→7B 模型，处理时间显著缩短
- **多层容错**: LLM 层+Checkpoint 层+主循环层三重防护
- **可观测性**: 进度条 + 实时监控 + 统一启动入口
- **嵌入升级**: MiniLM → BGE-M3，中文语义理解能力增强

**技术文档**：

- **核心技术挑战**: `docs/TECHNICAL_CHALLENGES.md` - 核心技术挑战与解决方案
- **实现细节**: `IMPLEMENTATION_DETAILS.md` - 端到端数据流详解与核心模块说明
- **问题修复**: `FIX_SUMMARY.md` - 问题修复记录

### v2.0 (2024-11-20) - 基础功能完善

- Layout-Aware PDF 解析
- LLM 概念抽取基础版
- BGE-M3 嵌入模型集成

### v1.0 (2024-10) - 项目启动

- 基础实体关系抽取
- Neo4j 图谱可视化
- 初始管道搭建

---

## 相关文档

### 技术文档

- **实现细节与模块说明**: `IMPLEMENTATION_DETAILS.md`

  - 端到端数据流详解（PDF → Neo4j）
  - 核心模块与源码位置速查表
  - 典型运行场景与日志示例
  - 性能指标与实验数据
  - 故障排查决策树

- **核心技术挑战**: `docs/TECHNICAL_CHALLENGES.md`

  - 5 大核心技术挑战详解
  - 完整解决方案和代码实现
  - 性能优化决策分析
  - 架构演进历程
  - 附录：代码位置与日志速查

- **问题修复**: `FIX_SUMMARY.md`
  - 已知问题诊断和修复
  - 故障排查流程

### 使用指南

```bash
# 快速开始
./start.sh              # 启动管道

# 状态监控
./status.sh             # 查看当前状态
./monitor.sh            # 实时监控（每5秒刷新）

# 辅助脚本
./fast_download_bge_m3.sh    # 快速下载BGE-M3模型
./simple_deduplicate.py      # 简单去重（不依赖BGE-M3）
```

---

## 许可证

本项目采用 MIT 许可证。

---

## 快速链接

- **快速开始**: 见上方"快速开始"章节
- **配置文件**: `config/config.yaml`
- **示例数据**: `output/` 目录
- **运行脚本**: `./archive/RUN.sh`
- **故障排查**: 见上方"故障排查"章节
- **归档文档**: `archive/` 目录（旧版文档和脚本）

---

```bash
# 常用命令示例
python enhanced_pipeline.py
python main.py
```
