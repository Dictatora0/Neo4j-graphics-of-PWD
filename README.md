# 松材线虫病知识图谱构建系统

<div align="center">

**知识工程第二组 - 基于文献的松材线虫病知识图谱项目**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![Neo4j](https://img.shields.io/badge/Neo4j-4.x%20%7C%205.x-green.svg)](https://neo4j.com)

**GitHub 仓库**：[https://github.com/Dictatora0/Neo4j-graphics-of-PWD.git](https://github.com/Dictatora0/Neo4j-graphics-of-PWD.git)

</div>

---

## 项目概述

本项目从松材线虫病（Pine Wilt Disease，PWD）相关 PDF 文献中自动抽取实体和关系，构建可在 Neo4j 中查询和可视化的领域知识图谱。

管道核心由三部分组成：

- 从 PDF 中抽取文本，并做基础清洗
- 使用本地大模型（通过 Ollama）进行概念与关系抽取、嵌入式去重和邻近性分析
- 结合规则和统计，对关系进行过滤、语义体检和修正后导入 Neo4j

目标是得到一份结构清晰、数据质量可控的松材线虫病知识图谱，支持进一步分析和展示。

---

## 最终成果概览

### 图谱规模（Neo4j 数据库）

- **节点数**：59
- **关系数**：365
- **节点类型**：8 种（Host, Location, Vector, Technology, Control, Disease, Pathogen, Other）
- **关系类型**：21 种（以 CO_OCCURS_WITH 为主）

### 节点类别（概念层面）

根据节点上 `type` 字段的统计，当前图谱中的节点分布为：

- Other：18 个
- Host：16 个
- Location：10 个
- Vector：5 个
- Technology：5 个
- Control：3 个
- Disease：1 个
- Pathogen：1 个

从语义上看，这些类型覆盖了疾病、病原体、媒介、寄主、地点、技术方法、防治措施以及少量其他概念。

### 关系类型概况

当前数据库中共有 21 种关系类型，其中：

- `CO_OCCURS_WITH`：299 条（约 81.9%）
- `RELATED_TO`：12 条（约 3.3%）
- `PARASITIZES`：6 条
- `TREATS`、`DISTRIBUTED_IN`：各 5 条
- `AFFECTS`：4 条
- `TRANSMITS`、`INFECTS`、`FEEDS_ON`、`LOCATED_IN`、`USED_FOR`、`CONTAINS`、`SYMPTOM_OF`：各 3 条
- `CARRIES`、`COMPARES_WITH`、`CONTROLS`、`CAUSES`、`APPLIES_TO`：各 2 条
- `COMPETES_WITH`、`MONITORS`、`COMPONENT_OF`：各 1 条

详细的统计和示例可见：

- `output/statistics_report.txt`
- `FINAL_REPORT.md`

### 关键输出文件

- `output/concepts_final.csv`：最终概念列表
- `output/relationships_final.csv`：最终关系列表
- `output/neo4j_import/nodes_final.csv`：最终节点（导入 Neo4j 的简化版本）
- `output/neo4j_import/relations_final.csv`：最终关系（导入 Neo4j 的简化版本）
- `output/neo4j_export_*.csv`：从 Neo4j 导出的最新三元组（带权重与类型）
- `output/statistics_report.txt`：概念与关系的统计报告
- `FINAL_REPORT.md`：对最终图谱质量和结构的文字总结

---

## Jupyter Notebook 分析与可视化

项目提供完整的交互式分析 Notebook：

- `notebooks/PWD_Knowledge_Graph_Analysis.ipynb`：包含数据库连接、统计查询、多跳路径、风险评估、可视化图表、GDS 社区划分与最短路径可视化等十余个章节，可直接运行生成报告用图表与表格。

主要功能：

- 图规模、核心节点、传播链路、防控措施、地理分布等统计查询
- 病原-宿主-媒介链路、共现网络、风险评估等应用查询
- Matplotlib/Seaborn 可视化：节点/关系类型分布、宿主风险排序等
- GDS Louvain 社区检测与社区分布图
- NetworkX 最短路径可视化（可自定义起止节点）

使用方式：

```bash
./venv/bin/jupyter notebook
# 在浏览器打开 notebooks/PWD_Knowledge_Graph_Analysis.ipynb
```

---

## 快速开始

### 环境要求

- Python 3.8+
- Neo4j 4.x 或 5.x
- 本地 LLM 服务（默认通过 Ollama 调用 `llama3.2:3b`）

### 安装依赖

```bash
pip install -r requirements.txt
python -m spacy download zh_core_web_sm
python -m spacy download en_core_web_sm
```

### 准备数据

1. 将待处理的 PDF 文献放入项目根目录下的 `文献/` 目录
2. 根据需要调整 `config/config.yaml` 中的参数（见下文“配置说明”）

### 运行构建管道

```bash
# 方式一：直接运行主程序
python main.py

# 或使用封装好的脚本
./scripts/workflow/run_complete_workflow.sh
```

主程序完成后，会在 `output/` 目录生成：

- `concepts.csv` / `relationships.csv`：LLM 抽取和去重后的概念与关系
- `entities_clean.csv` / `relations_clean.csv`：清洗后的实体和关系
- `neo4j_import/`：导入 Neo4j 所需的 CSV 与 Cypher 脚本
- `statistics_report.txt`：抽取与清洗阶段的统计结果

### 导入 Neo4j

导入推荐使用两种方式之一：

1. **使用三元组导入脚本（最终图谱）**

   ```bash
   python import_to_neo4j_final.py
   ```

   该脚本会：

   - 读取 `output/triples_export_semantic_clean.csv`（若存在，否则使用 `triples_export.csv`）
   - 清空当前数据库
   - 创建节点与关系，并添加类型、权重、样式等属性
   - 生成索引和基本统计信息

2. **使用 CSV + Cypher 导入脚本**

   ```bash
   cd output/neo4j_import
   python import_to_neo4j.py
   # 或在 Neo4j Browser 中执行 import.cypher
   ```

   使用 `nodes.csv` / `relations.csv` 构建一个更简化的实体-关系图。

导入完成后，可在浏览器访问 Neo4j：

- 地址：`http://localhost:7474`
- 用户名：`neo4j`
- 密码：`12345678`（默认值，见 `config/config.yaml`）

---

## 工作流程

整个流程可以分为四个阶段：

### 1. 文本抽取与预处理

相关代码：`pdf_extractor.py`、`ocr_processor.py`

- 从 `文献/` 目录读取 PDF
- 使用 PyMuPDF 提取正文，按章节和页码切分文本
- 支持基础 OCR（可选），以及对页眉、脚注、参考文献等噪声区域的过滤

### 2. LLM 概念与关系抽取

相关代码：`enhanced_pipeline.py`、`concept_extractor.py`、`concept_deduplicator.py`

- 将抽取的文本按块切分并发送给本地大模型
- 识别候选概念和概念间的关系
- 使用向量嵌入进行去重和合并，相似度阈值和过滤规则可在配置中控制
- 输出到 `output/concepts.csv` 和 `output/relationships.csv`

### 3. 数据清洗与 Neo4j 导入文件生成

相关代码：`data_cleaner.py`、`neo4j_generator.py`

- 按置信度阈值、出现频次、字符过滤等规则清洗关系
- 规范化实体命名、去除明显噪声概念
- 生成：
  - `entities_clean.csv` / `relations_clean.csv`
  - `output/neo4j_import/nodes.csv` / `relations.csv`
  - `output/neo4j_import/import.cypher`

### 4. 语义体检与最终图谱构建

相关代码：`bio_semantic_review.py`、`fix_semantic_triples.py`、`refine_node_labels.py`、`fix_remaining_relations.py`、`export_neo4j_to_csv.py`、`verify_neo4j_data.py`、`import_to_neo4j_final.py`

- 对三元组进行领域规则检查：
  - 按名称和上下文推断节点类别（疾病、病原体、寄主、媒介等）
  - 检查关系起止点类型是否合理
  - 识别方向错误、自环、孤立节点等问题
- 生成语义修正版三元组：
  - `triples_export_semantic_clean.csv`
  - `triples_semantic_issues.csv`
- 调整少量节点标签和剩余关系类型
- 通过 `import_to_neo4j_final.py` 导入最终版本图谱
- 使用 `export_neo4j_to_csv.py` 与 `verify_neo4j_data.py` 对最终数据库进行导出和一致性检查

---

## 知识图谱设计

### 实体类型（概念层面）

下表为图谱中常见的实体类型及示例：

| 类型       | 说明       | 示例                         |
| ---------- | ---------- | ---------------------------- |
| Disease    | 疾病       | pine wilt disease            |
| Pathogen   | 病原体     | bursaphelenchus xylophilus   |
| Host       | 寄主       | pinus thunbergii、马尾松     |
| Vector     | 媒介       | monochamus alternatus 等天牛 |
| Symptom    | 症状       | 叶片变色、落叶               |
| Control    | 防治措施   | 诱捕器、生物防治、防治       |
| Technology | 技术与方法 | Sentinel-2、高光谱数据       |
| Location   | 地点       | 泰山风景区、巴山、疫区       |
| Other      | 其他概念   | 林业、光谱、波段选择算法等   |

不同脚本和导入方式下，具体的标签命名会略有差异，但整体设计围绕上述几类。

### 关系类型（语义层面）

在最终图谱中，除了共现关系外，还包含多类语义关系，例如：

- `PARASITIZES`（寄生）：媒介或病原体寄生在寄主上
- `INFECTS`（感染）：病原体对寄主的感染关系
- `CAUSES` / `SYMPTOM`（引起 / 症状）：疾病与症状之间的联系
- `TRANSMITS`（传播）：媒介传播病原体或疾病
- `DISTRIBUTED_IN`（分布于）：疾病或媒介在地区上的分布
- `AFFECTS`（影响）：环境或技术因素对病害的影响
- `TREATS` / `CONTROLS`（治疗 / 防治）：防治措施与病害或病原体之间的关系
- `USED_FOR` / `MONITORS`（用于 / 监测）：技术与监测任务之间的关系
- `CO_OCCURS_WITH`（共现）：文献中共同出现的概念，用于补充背景连接

---

## 目录结构与核心脚本

项目根目录的主要结构如下（简化）：

```text
PWD/
├── README.md                  # 项目说明（本文件）
├── requirements.txt           # Python 依赖
├── .gitignore                 # Git 忽略规则
│
├── docs/                      # 文档目录
│   ├── PROJECT_STRUCTURE.txt  # 项目结构说明
│   └── PWD_Knowledge_Graph_Analysis.html  # 分析报告HTML版本
│
├── notebooks/                 # Jupyter Notebooks
│   ├── PWD_Knowledge_Graph_Analysis.ipynb  # 主分析笔记本
│   └── PWD_KG_Notebook.ipynb  # 知识图谱笔记本
│
├── 核心脚本（主流程）
│   ├── main.py                # 主入口，整合增强管道与 Neo4j 管理
│   ├── enhanced_pipeline.py   # LLM 概念与关系抽取管道
│   ├── concept_extractor.py   # 概念与关系抽取
│   ├── concept_deduplicator.py # 嵌入式去重与合并
│   ├── data_cleaner.py        # 数据清洗与规范化
│   ├── neo4j_generator.py     # 生成 Neo4j 导入文件
│   ├── neo4j_manager.py       # Neo4j 备份、清空与回滚
│   ├── pdf_extractor.py       # PDF 文本提取
│   ├── ocr_processor.py       # OCR 处理
│   ├── entity_linker.py       # 实体链接
│   ├── parallel_processor.py  # 并行处理
│   ├── bio_semantic_review.py # 三元组语义体检
│   └── import_to_neo4j_final.py # 使用三元组导入最终图谱
│
├── scripts/                   # 辅助脚本
│   ├── workflow/              # 工作流脚本
│   │   ├── run_complete_workflow.sh  # 一键运行完整流程
│   │   ├── check_progress.sh  # 运行进度检查
│   │   ├── clean_project.sh   # 输出与缓存清理
│   │   └── organize_project.sh # 项目文件整理
│   └── utils/                 # 工具脚本
│       ├── export_for_review.py  # 导出审查文件
│       ├── export_triples.py  # 导出三元组
│       ├── export_neo4j_to_csv.py # 从数据库导出 CSV
│       ├── auto_disambiguate.py # 自动消歧
│       ├── cache_manager.py   # 缓存管理
│       ├── config_loader.py   # 配置加载
│       ├── logger_config.py   # 日志配置
│       └── visualize_neo4j_graph.py # Neo4j 图可视化
│
├── config/
│   ├── config.yaml            # 主配置文件
│   ├── domain_dict.json       # 领域词典
│   └── stopwords.txt          # 停用词
│
├── output/                    # 输出目录
│   ├── concepts*.csv          # 概念相关中间结果
│   ├── relationships*.csv     # 关系相关中间结果
│   ├── entities_clean.csv     # 清洗后实体
│   ├── relations_clean.csv    # 清洗后关系
│   ├── neo4j_import/          # Neo4j 导入文件与脚本
│   ├── triples/               # 三元组相关中间结果
│   ├── statistics_report.txt  # 抽取/清洗阶段统计
│   └── *.md/*.json            # 数据检查与导入报告
│
├── archive/                   # 开发过程存档
│   ├── scripts/               # 调试和中间版本脚本
│   └── docs/                  # 旧文档和报告
│
├── 文献/                      # PDF 文献目录
└── venv/                      # 虚拟环境（不纳入版本控制）
```

更细致的说明可参考 `docs/PROJECT_STRUCTURE.txt`。

---

## 配置说明

主配置文件位于 `config/config.yaml`，与当前实现保持一致。核心字段示意：

```yaml
# PDF 提取
pdf:
  input_directory: ./文献
  output_directory: ./output/extracted_texts
  enable_cache: true
  parallel_workers: 8

# 实体识别
entity:
  enable_tfidf: true
  enable_yake: true
  enable_keybert: true
  enable_spacy: true
  domain_dict_file: ./config/domain_dict.json

# 关系抽取
relation:
  enable_pattern_matching: true
  enable_cooccurrence: true
  window_size: 100

# 数据清洗
cleaning:
  confidence_threshold: 0.65
  similarity_threshold: 0.85
  enable_entity_linking: true

# Neo4j
neo4j:
  uri: neo4j://127.0.0.1:7687
  user: neo4j
  password: "12345678"
  database: PWD

# LLM
llm:
  model: llama3.2:3b
  ollama_host: http://localhost:11434
  max_chunks: 100
  timeout: 120
```

配置建议：

- 小规模测试：降低 `max_chunks`，或在 `filtering` 中提高 `min_importance`
- 强调质量：提高 `cleaning.confidence_threshold`，保持 `enable_entity_linking: true`
- 强调召回：适当降低置信度阈值，但需要结合统计报告人工抽查

---

## Neo4j 使用与分析

- 基本连接信息和常用查询示例见：`NEO4J_USAGE_GUIDE.md`
- 导入完成后，可在 Neo4j Browser 中：
  - 按节点/关系类型浏览整体结构
  - 查看度数最高的节点、权重较高的关系
  - 通过最短路径和子图查询分析传播链路

典型查询示例（节选）：

```cypher
// 查看节点类型分布
MATCH (n)
RETURN n.type AS node_type, count(*) AS count
ORDER BY count DESC;

// 查看关系类型分布
MATCH ()-[r]->()
RETURN type(r) AS rel_type, count(*) AS count
ORDER BY count DESC;

// 查询病原体到寄主的传播路径
MATCH path = (p:Pathogen)-[*1..4]-(h:Host)
RETURN p.name, h.name, length(path) AS path_length
LIMIT 10;
```

更完整的查询和可视化建议请参考 `NEO4J_USAGE_GUIDE.md`。

---

## Neo4j 实时统计（示例）

统计时间：2025-11-16（基于当前默认数据库）

查询语句：

```cypher
// 节点和关系总数
MATCH (n) RETURN count(n) AS node_count;
MATCH ()-[r]->() RETURN count(r) AS rel_count;

// 节点类型分布（按 n.type 或标签）
MATCH (n)
RETURN coalesce(n.type, head(labels(n))) AS type, count(*) AS count
ORDER BY count DESC;

// 关系类型分布
MATCH ()-[r]->()
RETURN type(r) AS type, count(*) AS count
ORDER BY count DESC;
```

当前结果快照：

- 节点总数：59
- 关系总数：365

节点类型分布：

- Other：18
- Host：16
- Location：10
- Vector：5
- Technology：5
- Control：3
- Disease：1
- Pathogen：1

关系类型分布（按条数从高到低）：

- CO_OCCURS_WITH：299
- RELATED_TO：12
- PARASITIZES：6
- TREATS：5，DISTRIBUTED_IN：5
- AFFECTS：4
- TRANSMITS / INFECTS / FEEDS_ON / LOCATED_IN / USED_FOR / CONTAINS / SYMPTOM_OF：各 3
- CARRIES / COMPARES_WITH / CONTROLS / CAUSES / APPLIES_TO：各 2
- COMPETES_WITH / MONITORS / COMPONENT_OF：各 1

---

## 性能与注意事项

- 处理规模：当前配置下，处理十几篇 PDF（约几十 MB）在一台普通笔记本上耗时约几十分钟，依赖本地 LLM 推理速度
- 运行过程中会生成较多中间 CSV/JSON 文件，建议定期使用 `scripts/workflow/clean_project.sh` 清理
- LLM 抽取结果难免包含噪声和边缘概念，最终图谱是在多轮过滤和语义体检后得到，关键结论建议结合领域知识复核

---

## 许可证及用途

本项目仅用于课程学习和学术研究，不用于生产环境部署。
