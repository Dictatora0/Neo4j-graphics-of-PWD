# 松材线虫病知识图谱构建系统

<div align="center">

**知识工程第二组 - 基于文献的松材线虫病知识图谱项目**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![Neo4j](https://img.shields.io/badge/Neo4j-4.x%20%7C%205.x-green.svg)](https://neo4j.com)

**GitHub 仓库**：[https://github.com/Dictatora0/Neo4j-graphics-of-PWD.git](https://github.com/Dictatora0/Neo4j-graphics-of-PWD.git)

</div>

---

## 项目简介

本项目是知识工程课程第二组的实验项目，从松材线虫病（Pine Wilt Disease，PWD）相关的 PDF 学术论文中自动提取知识实体和关系，构建可导入 Neo4j 的知识图谱。采用多策略实体识别、规则与统计结合的关系抽取方法，实现从文献到知识图谱的端到端自动化处理。

### 核心功能

- **智能 PDF 解析**：自动提取 PDF 正文，过滤页眉页脚和参考文献，支持缓存与并行处理
- **多策略实体识别**：结合 TF-IDF、YAKE、KeyBERT、spaCy NER 等多种方法，支持外部领域词典
- **关系自动抽取**：基于正则模式匹配和共现分析，支持关系方向校验和置信度分级
- **数据智能清洗**：去重、同义词合并、质量过滤、实体链接与消歧
- **Neo4j 集成**：自动生成导入文件（nodes.csv、relations.csv）和 Cypher 脚本
- **性能优化**：缓存机制、并行处理、增量更新支持

### 适用场景

- 学术研究中的文献知识整合
- 生物医学领域知识图谱构建
- 林业病虫害知识库建设
- 科研知识管理和检索

---

## 快速开始

### 环境要求

- Python 3.8+
- Neo4j 4.x 或 5.x（可选）

### 安装依赖

```bash
# 方法一：使用安装脚本（推荐）
bash install.sh

# 方法二：手动安装
pip install -r requirements.txt
python -m spacy download zh_core_web_sm
python -m spacy download en_core_web_sm
```

### 运行程序

```bash
# 1. 将PDF文件放入 文献/ 目录
# 2. 运行主程序
python main.py
```

程序将自动执行完整的知识图谱构建流程：

1. PDF 文本提取
2. 实体识别
3. 关系抽取
4. 数据清洗
5. 生成 Neo4j 导入文件

### 导入 Neo4j

```bash
# 直接导入数据到 Neo4j
python import_to_neo4j_final.py
```

导入完成后访问：http://localhost:7474

**当前数据状态**：

- 节点数: 59
- 关系数: 365
- 数据来源: 松材线虫病相关文献
- 核心疾病: 松材线虫病（1 个）
- 实体类型: 8 种（Host, Symptom, ControlMeasure, EnvironmentalFactor, Region, Vector, Disease, Pathogen）
- 关系类型: 7 种（hasHost, hasSymptom, controlledBy, affectedBy, hasVector, occursIn, hasPathogen）

---

## 系统架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  PDF 文献   │ --> │  文本提取   │ --> │  实体识别   │ --> │  关系抽取   │ --> │  数据清洗   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                         PyMuPDF           多策略 NER          模式匹配           去重/规范化
                                                               共现分析
                                                                    |
                                                                    v
                    ┌──────────────────────────────────────────────────────────┐
                    │                  Neo4j 知识图谱                                 │
                    │              (可视化查询 / 知识推理)                        │
                    └──────────────────────────────────────────────────────────┘
```

---

## 数据模型

### 实体类型

| 类型                | 说明     | 示例                                 |
| ------------------- | -------- | ------------------------------------ |
| Disease             | 疾病     | 松材线虫病、PWD                      |
| Pathogen            | 病原体   | 松材线虫、Bursaphelenchus xylophilus |
| Host                | 宿主     | 马尾松、黑松                         |
| Vector              | 传播媒介 | 松褐天牛、Monochamus alternatus      |
| Symptom             | 症状     | 针叶变色、萎蔫                       |
| ControlMeasure      | 防控措施 | 清理病死树、化学防治                 |
| Region              | 地区     | 浙江、江苏                           |
| EnvironmentalFactor | 环境因素 | 温度、湿度                           |

### 关系类型

| 关系         | 说明       | 示例                    |
| ------------ | ---------- | ----------------------- |
| hasPathogen  | 有病原体   | 松材线虫病 → 松材线虫   |
| hasHost      | 有宿主     | 松材线虫病 → 马尾松     |
| hasVector    | 有传播媒介 | 松材线虫病 → 松褐天牛   |
| hasSymptom   | 有症状     | 松材线虫病 → 针叶变色   |
| controlledBy | 被控制     | 松材线虫病 → 清理病死树 |
| occursIn     | 发生在     | 松材线虫病 → 浙江       |
| affectedBy   | 受影响     | 松材线虫病 → 温度       |
| transmits    | 传播       | 松褐天牛 → 松材线虫     |
| infects      | 感染       | 松材线虫 → 马尾松       |

---

## 数据处理流程

```
┌─────────────────────────────────────────────────────────────┐
│  第 1 步：原始数据提取                                        │
│  python main.py                                             │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
           ┌──────────────────────┐
           │  output/entities.csv  │ (原始实体，~1000+条)
           │  output/relations.csv │ (原始关系，~500+条)
           └──────────┬───────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│  第 2 步：数据清洗（在 main.py 中完成）                       │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
           ┌──────────────────────────┐
           │  output/entities_clean.csv │ (清洗后)
           │  output/relations_clean.csv│ (清洗后)
           └──────────┬────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│  第 3 步：转换为 Neo4j 格式（在 main.py 中自动完成）          │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
           ┌────────────────────────────────┐
           │  output/neo4j_import/nodes.csv     │ (Neo4j 格式)
           │  output/neo4j_import/relations.csv │ (Neo4j 格式)
           └──────────┬─────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│  第 4 步：导入到 Neo4j                                        │
│  python import_fixed_data.py                                │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
                 ┌─────────┐
                 │  Neo4j  │
                 │ 数据库   │
                 └─────────┘
```

### 文件说明

| 文件                                       | 说明                         | 用途           |
| ------------------------------------------ | ---------------------------- | -------------- |
| `output/entities.csv`                      | 原始提取的实体               | 备份           |
| `output/relations.csv`                     | 原始提取的关系               | 备份           |
| `output/entities_clean.csv`                | 清洗后的实体                 | 备份           |
| `output/relations_clean.csv`               | 清洗后的关系                 | 备份           |
| `output/triples_export.csv`                | 最初导出的三元组             | 语义体检输入   |
| `output/triples_export_semantic_clean.csv` | 语义体检与规则修正后的三元组 | Neo4j 导入源   |
| `output/triples_semantic_issues.csv`       | 语义体检中发现的问题及建议   | 人工复核       |
| `output/neo4j_import/nodes.csv`            | Neo4j 节点文件（最终节点集） | **导入 Neo4j** |
| `output/neo4j_import/relations.csv`        | Neo4j 关系文件（最终关系集） | **导入 Neo4j** |
| `output/neo4j_import/queries.cypher`       | Cypher 查询示例              | 参考查询       |

### 项目结构

```
PWD/
├── main.py                    # 主程序入口
├── pdf_extractor.py           # PDF 文本提取
├── entity_recognizer.py      # 实体识别
├── relation_extractor.py     # 关系抽取
├── data_cleaner.py           # 数据清洗
├── neo4j_generator.py        # Neo4j 文件生成
├── import_fixed_data.py      # Neo4j 数据导入
├── config/                   # 配置文件目录
│   ├── config.yaml          # 主配置文件
│   └── domain_dict.json     # 领域词典
├── output/                   # 输出目录
│   └── neo4j_import/        # Neo4j 导入文件
│       ├── nodes.csv        # 节点文件（44个）
│       ├── relations.csv    # 关系文件（43条）
│       └── queries.cypher   # 查询示例
├── archive/                  # 归档目录（历史脚本和文档）
│   ├── scripts/             # 临时脚本（28个）
│   └── docs/                # 过时文档（4个）
└── 文献/                    # PDF 文献目录
```

**注意**：`archive/` 目录用于存放开发过程中的临时脚本和历史文档，不影响核心流程。

### 语义体检与最终图谱构建流程

在传统管道的基础上，本项目增加了一套面向松材线虫病领域的语义检查与修正流程，用于得到最终版本的 PWD 图谱：

1. 使用抽取管道生成 `output/triples_export.csv`。
2. 运行 `bio_semantic_review.py`：
   - 基于名称规则推断节点类型（Pathogen, Host, Vector, Disease 等）。
   - 按白名单检查关系三元组的起点/终点类型是否合理。
   - 在少数关系类型上自动纠正方向，并导出：
     - `triples_export_semantic_clean.csv`（用于重新导入的三元组）。
     - `triples_semantic_issues.csv`（问题三元组及建议）。
3. 根据 `triples_semantic_issues.csv`，结合生物学知识手工/脚本化修正：
   - 运行 `fix_semantic_triples.py` 对部分典型三元组做批量修正或删除。
   - 运行 `refine_node_labels.py` 调整 Neo4j 中关键节点的标签（如 Symptom, EnvironmentalFactor, Location 等）。
   - 运行 `fix_remaining_relations.py` 对少量残余关系类型进行统一处理。
4. 运行 `import_to_neo4j_final.py`：
   - 优先导入 `triples_export_semantic_clean.csv`，若不存在则回退到原始导出文件。
   - 在 Neo4j 中创建节点和关系，并应用可视化样式文件 `neo4j_style.grass`。
5. 使用 `export_neo4j_to_csv.py` 与 `verify_neo4j_data.py` 对最终数据库进行导出与一致性检查。

---

## 配置说明

主要配置文件：`config/config.yaml`

```yaml
# PDF 提取配置
pdf:
  input_directory: ./文献
  parallel_workers: 4 # 并行处理进程数（null=自动检测）

# 系统功能开关
system:
  enable_cache: true # 缓存机制（推荐启用，速度提升10x）
  enable_parallel: true # 并行处理（推荐启用）
  enable_incremental: false # 增量更新（首次运行设为 false）

# 实体识别配置
entity:
  max_entity_length: 30
  domain_dict_file: ./config/domain_dict.json # 外部领域词典

# 数据清洗配置
cleaning:
  confidence_threshold: 0.65 # 关系置信度阈值（0.60-0.70）
  enable_entity_linking: false # 实体链接与消歧（提升准确率10-15%）
```

### 配置建议

| 场景               | `confidence_threshold` | `enable_entity_linking` | 说明                 |
| ------------------ | ---------------------- | ----------------------- | -------------------- |
| 高质量模式（科研） | 0.70                   | true                    | 质量优先，数量较少   |
| 平衡模式（推荐）   | 0.65                   | false                   | 质量与数量平衡       |
| 高召回模式（探索） | 0.60                   | false                   | 数量优先，可能有噪声 |

---

## Neo4j 使用指南

### 连接信息

- **Neo4j Browser**: http://localhost:7474
- **连接 URI**: `neo4j://127.0.0.1:7687`
- **默认用户**: `neo4j`
- **默认密码**: `12345678`

### 基础查询

```cypher
// 查看所有节点类型和数量
MATCH (n)
RETURN labels(n)[0] AS 类型, count(n) AS 数量
ORDER BY 数量 DESC;

// 查看所有关系类型和数量
MATCH ()-[r]->()
RETURN type(r) AS 关系类型, count(r) AS 数量
ORDER BY 数量 DESC;
```

### 传播链分析

```cypher
// 完整传播链查询
MATCH (d:Disease {name: '松材线虫病'})-[:hasPathogen]->(p:Pathogen)
MATCH (d)-[:hasVector]->(v:Vector)
MATCH (d)-[:hasHost]->(h:Host)
MATCH (d)-[:hasSymptom]->(s:Symptom)
RETURN d.name AS 疾病,
       p.name AS 病原体,
       collect(v.name) AS 媒介,
       collect(h.name) AS 宿主,
       s.name AS 症状;
```

### 可视化关系网络

```cypher
// 查看松材线虫病的完整关系网络
MATCH path = (d:Disease {name: '松材线虫病'})-[*1]-(n)
RETURN path
LIMIT 50;
```

### 更多查询示例

完整查询示例请查看：`output/neo4j_import/queries.cypher`

---

## 故障排除

### KeyBERT 导入错误

**错误信息**：`ImportError: cannot import name 'cached_download'`

**解决方案**：

```bash
pip uninstall sentence-transformers huggingface-hub keybert -y
pip install sentence-transformers==2.3.1 huggingface-hub>=0.19.0 keybert==0.8.5
```

### spaCy 模型未安装

**错误信息**：`OSError: [E050] Can't find model 'zh_core_web_sm'`

**解决方案**：

```bash
python -m spacy download zh_core_web_sm
python -m spacy download en_core_web_sm
```

### Neo4j 连接失败

**错误信息**：`Connection refused` 或 `Failed to establish connection`

**原因**：Neo4j 服务未启动

**解决方案**：

```bash
# 方法 1: 使用命令行启动 Neo4j
neo4j start

# 方法 2: 使用 brew services（macOS）
brew services start neo4j

# 方法 3: 使用 Neo4j Desktop
# 打开 Neo4j Desktop 应用，点击数据库的 Start 按钮

# 检查 Neo4j 状态
neo4j status

# 访问 Neo4j Browser 确认运行
open http://localhost:7474
```

**如果未安装 Neo4j**：

```bash
# macOS 使用 Homebrew 安装
brew install neo4j

# 或下载 Neo4j Desktop（推荐）
# 访问: https://neo4j.com/download/
```

### 关系数量为 0

**原因**：置信度阈值太高

**解决方案**：修改 `config/config.yaml`，设置 `confidence_threshold: 0.65` 或更低

### Neo4j CSV 导入失败

**错误信息**：`Couldn't load the external resource`

**解决方案**：确保 CSV 文件在 Neo4j 的 import 目录下

```bash
# 查找 Neo4j import 目录
# Linux/Mac: ~/neo4j/import/ 或 /var/lib/neo4j/import/
# Windows: C:\Users\YourName\neo4j\import\

# 复制文件
cp output/neo4j_import/*.csv ~/neo4j/import/
```

### 内存不足

**解决方案**：减少并行进程数

```yaml
# config/config.yaml
pdf:
  parallel_workers: 2 # 降低从 4
```

---

## 性能指标

### 典型处理速度（14 个 PDF，约 50MB）

| 指标     | 首次运行 | 缓存后重运行 |
| -------- | -------- | ------------ |
| 处理时间 | 4-8 分钟 | 30-60 秒     |

### 典型数据量

- **原始实体**：~1,071 条 → 清洗后 ~1,021 条
- **原始关系**：~1,502 条 → 清洗后 ~401 条
- **最终实体**：44 条（高质量，无孤立节点）
- **最终关系**：43 条（高质量，所有关系都连接到核心疾病）

### 数据质量指标

- 无孤立节点：所有节点都通过关系连接到核心疾病"松材线虫病"
- 无自环关系：所有关系都是有效的实体间连接
- 无重复关系：每条关系都是唯一的
- 关系类型正确：所有关系类型符合数据模型定义
- 实体类型完整：包含 8 种实体类型，覆盖疾病知识图谱的核心要素

---

## 技术栈

- **语言**：Python 3.8+
- **PDF 处理**：PyMuPDF
- **自然语言处理**：spaCy、jieba、YAKE、KeyBERT
- **数据处理**：pandas、numpy、scikit-learn
- **图数据库**：Neo4j 4.x / 5.x

---

## 注意事项

1. **PDF 格式**：仅支持可提取文本的 PDF（不支持扫描版）
2. **准确率**：自动提取的准确率约 70-80%，建议人工审核关键数据
3. **内存需求**：大规模处理（>50 个 PDF）需要 4GB+ 内存
4. **置信度阈值**：系统生成的关系置信度最高为 0.72，阈值不应超过此值
5. **项目归档**：临时脚本和过时文档已归档到 `archive/` 目录，不影响核心功能使用

---

## 项目信息

- **课程**：知识工程
- **小组**：第二组
- **项目主题**：基于文献的松材线虫病知识图谱构建
- **GitHub 仓库**：[https://github.com/Dictatora0/Neo4j-graphics-of-PWD.git](https://github.com/Dictatora0/Neo4j-graphics-of-PWD.git)

---

## 扩展功能

### 增量更新

修改 `config.yaml` 中 `enable_incremental: true`，只处理新增 PDF

### 实体链接

修改 `config.yaml` 中 `enable_entity_linking: true`，提升准确率 10-15%

### 领域词典

编辑 `config/domain_dict.json` 添加领域专业术语

### 关系模式

编辑 `relation_extractor.py` 中的正则模式扩展关系类型

---

## 许可证

本项目仅供学术研究使用。

---

<div align="center">

**知识工程第二组 - 基于文献的松材线虫病知识图谱项目**

</div>
