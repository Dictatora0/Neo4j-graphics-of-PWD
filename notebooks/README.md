# 🌐 Google Colab 版本 - 松材线虫病知识图谱构建

## 📌 概述

本目录包含将松材线虫病知识图谱构建流程迁移到 Google Colab 环境的完整 Notebooks。

## 📂 文件列表

| 文件                    | 说明                           | 预计时间  | 费用 |
| ----------------------- | ------------------------------ | --------- | ---- |
| **00\_环境设置.ipynb**  | 安装依赖、配置环境、上传文件   | 5-10 分钟 | 免费 |
| **01_PDF 提取.ipynb**   | 从 PDF 提取文本并分块          | 2-10 分钟 | 免费 |
| **02\_概念提取.ipynb**  | 使用 OpenAI GPT 提取概念和关系 | 5-15 分钟 | $1-5 |
| **03\_概念去重.ipynb**  | 语义去重和质量过滤             | 2-5 分钟  | 免费 |
| **04_Neo4j 导入.ipynb** | 导入知识图谱到 Neo4j           | 1-3 分钟  | 免费 |
| **COLAB\_使用指南.md**  | 详细使用说明文档               | -         | -    |

---

## 🔬 技术实现详解（供迭代改进参考）

### 步骤 0：环境设置

**技术栈**：

- Python 3.12+
- pip 包管理（强制重装以避免版本冲突）

**关键技术点**：

```python
# 依赖版本控制
numpy==1.26.2          # 固定版本避免 dtype 冲突
pandas==2.1.4          # 与 numpy 兼容
sentence-transformers==2.3.1  # 语义嵌入模型

# 安装策略
--force-reinstall      # 强制重装避免 Colab 预装版本冲突
--no-cache-dir         # 清除缓存确保干净安装
```

**可优化点**：

- 🔄 考虑使用 `poetry` 或 `conda` 管理依赖
- 🔄 添加版本兼容性检查脚本
- 🔄 支持离线依赖包（预下载 wheels）

---

### 步骤 1：PDF 文本提取

**核心库**：PyMuPDF (fitz)

**技术实现**：

```python
# 文本提取
doc = fitz.open(pdf_path)
text = page.get_text()  # 默认使用文本模式，保留布局

# 文本清洗
re.sub(r'\s+', ' ', text)           # 多空白归一
re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)  # 移除控制字符
re.sub(r'\n\d+\n', '\n', text)      # 移除页码

# 分块策略
chunk_size = 2000      # 字符数，适配 GPT-3.5 的 token 限制
overlap = 200          # 重叠部分，避免语义断裂
```

**关键参数**：

- `chunk_size`: 影响 LLM 处理效果和成本
  - 太小：上下文不足，概念提取不准
  - 太大：超出 token 限制，费用增加
  - **推荐**：1500-2500 字符

**可优化点**：

- 🔄 智能分块：基于段落、句子边界切分
- 🔄 OCR 支持：处理扫描版 PDF（集成 Tesseract/PaddleOCR）
- 🔄 表格提取：使用 `camelot` 或 `pdfplumber`
- 🔄 多语言支持：自动检测和分离中英文
- 🔄 参考文献过滤：自动识别并移除 References 部分

**技术选型原因**：

- PyMuPDF：速度快、内存占用小、支持复杂 PDF 格式
- 缓存机制：避免重复提取，节省时间

---

### 步骤 2：LLM 概念提取

**核心技术**：OpenAI GPT API + Prompt Engineering

**实现架构**：

```python
# Prompt 设计（Chain-of-Thought）
system_prompt = """
你是专业的生物学知识提取助手。
请识别以下类别的概念：
- 病原体（如：松材线虫）
- 宿主（如：松树、黑松）
- 载体（如：松墨天牛）
- 症状、防治方法、地区等

输出 JSON 格式。
"""

# 结构化输出
{
  "concepts": [
    {"name": "概念名", "category": "类别", "importance": 1-3}
  ],
  "relationships": [
    {"head": "实体1", "tail": "实体2", "relation": "关系", "confidence": 0-1}
  ]
}
```

**关键参数调优**：

```python
model: "gpt-3.5-turbo"        # 性价比最高
temperature: 0.1              # 低温度保证输出稳定性
max_tokens: 800               # 限制输出长度控制成本
timeout: 120                  # API 超时设置

# 成本控制
max_chunks: 30                # 限制处理块数
文本截断: text[:1500]         # 限制输入长度
```

**成本分析**：

```
gpt-3.5-turbo 定价（2024）:
- Input:  $0.0015 / 1K tokens
- Output: $0.002 / 1K tokens

30块 × 1500字符 × 1.3 (中文) ≈ 58K tokens (input)
30块 × 800 tokens (output) = 24K tokens

预计费用: (58 × 0.0015 + 24 × 0.002) ≈ $0.13
```

**可优化点**：

- 🔄 Few-shot Learning：在 prompt 中添加示例提升准确率
- 🔄 函数调用（Function Calling）：使用 GPT-4 的结构化输出
- 🔄 批处理优化：合并多个块减少 API 调用次数
- 🔄 本地 LLM：使用 Llama-3、Qwen 等开源模型（需 GPU）
- 🔄 混合策略：先用规则提取候选，再用 LLM 精炼
- 🔄 主动学习：对低置信度样本进行人工标注迭代

**技术选型原因**：

- OpenAI：效果稳定、API 易用、无需 GPU
- gpt-3.5-turbo：成本低、速度快、效果够用
- 结构化 prompt：保证输出可解析性

---

### 步骤 3：概念去重与过滤

**核心算法**：语义嵌入 + 余弦相似度聚类

**技术实现**：

```python
# 嵌入模型
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
# 模型特点：
# - 支持中英文混合
# - 384 维向量
# - 模型大小：470MB

# 嵌入计算
embeddings = model.encode(concepts)  # [N, 384]

# 相似度计算
similarity_matrix = cosine_similarity(embeddings)  # [N, N]

# 聚类去重
threshold = 0.85  # 相似度阈值
# > 0.85: 视为同一概念
```

**去重策略**：

```python
# 贪心聚类算法
for i, concept_i in enumerate(concepts):
    if used[i]:
        continue
    canonical = concept_i  # 第一个作为规范形式

    for j in range(i+1, len(concepts)):
        if similarity[i][j] >= threshold:
            mapping[concepts[j]] = canonical
            used[j] = True

# 属性合并
importance = max(importances)  # 取最高重要性
connections = sum(connections)  # 累加连接数
```

**过滤规则**：

```python
# 重要性过滤
min_importance = 1        # 保留重要性 >= 1 的概念

# 连接度过滤
min_connections = 0       # 允许孤立节点

# 组合策略
keep = (importance >= min_importance) OR (connections >= min_connections)
```

**关键参数调优**：

```python
similarity_threshold: 0.85
# 太高(>0.9): 去重不充分，存在大量同义词
# 太低(<0.8): 过度合并，损失语义差异
# **推荐**: 0.83-0.87，根据领域调整

embedding_model:
# - paraphrase-multilingual-MiniLM-L12-v2: 通用多语言（推荐）
# - sentence-transformers/paraphrase-xlm-r-multilingual-v1: 更大更准
# - shibing624/text2vec-base-chinese: 专注中文
```

**可优化点**：

- 🔄 层次聚类：HDBSCAN 或 Agglomerative Clustering
- 🔄 实体链接：链接到外部知识库（WikiData、UMLS）
- 🔄 主动学习：人工审核边界样例优化阈值
- 🔄 多模态嵌入：结合文本 + 图结构特征
- 🔄 增量去重：支持新数据增量更新而非全量重算
- 🔄 同义词词典：预定义领域同义词加速去重

**性能分析**：

```
100 个概念 → 嵌入计算: ~2秒
相似度矩阵: ~0.1秒
聚类去重: ~0.5秒

瓶颈：嵌入计算（与概念数成正比）
优化：批量编码、GPU 加速
```

---

### 步骤 4：Neo4j 图数据库导入

**核心技术**：Neo4j Python Driver + Cypher 查询语言

**数据模型**：

```cypher
# 节点模型
(:Concept {
  name: String,           # 概念名称（唯一键）
  category: String,       # 类别
  importance: Integer,    # 重要性 1-3
  connections: Integer    # 连接数
})

# 关系模型
()-[r:RELATION_TYPE {
  weight: Float,          # 关系权重 0-1
  source: String          # 来源（llm/proximity）
}]->()
```

**导入策略**：

```python
# 批量导入（避免逐条插入）
with driver.session() as session:
    # 使用 MERGE 避免重复
    session.run("""
        UNWIND $batch as row
        MERGE (n:Concept {name: row.name})
        SET n.category = row.category,
            n.importance = row.importance
    """, batch=concept_batch)

# 索引优化
CREATE CONSTRAINT concept_name_unique
FOR (n:Concept) REQUIRE n.name IS UNIQUE

CREATE INDEX concept_category_index
FOR (n:Concept) ON (n.category)
```

**关系类型动态化**：

```python
# 将关系名转为 Cypher 关系类型
relation_type = row['edge'].replace(' ', '_').upper()
# "感染" → "感染"
# "has pathogen" → "HAS_PATHOGEN"

# 动态构建 Cypher
f"MERGE (a)-[r:{relation_type}]->(b)"
```

**可优化点**：

- 🔄 批量导入：使用 `apoc.periodic.iterate` 提升性能
- 🔄 图算法：计算 PageRank、社区检测、中心性指标
- 🔄 全文搜索：集成 Neo4j Full-Text Index
- 🔄 图可视化：集成 neovis.js 或 Bloom
- 🔄 版本控制：为节点添加时间戳和版本号
- 🔄 权限控制：基于角色的访问控制（RBAC）

**查询优化**：

```cypher
# 使用索引加速查询
MATCH (n:Concept {name: $name})  -- 利用唯一索引

# 避免笛卡尔积
MATCH (a:Concept)-[r]-(b:Concept)  -- ❌ 慢
MATCH (a:Concept {category: 'X'})-[r]-(b)  -- ✅ 快

# 限制遍历深度
MATCH path = (a)-[*1..3]-(b)  -- 限制 3 跳内
```

**性能基准**（100 节点 + 200 关系）：

- 导入时间：~10 秒
- 查询响应：<100ms（有索引）
- 内存占用：~50MB

---

## 🎯 整体架构与数据流

```
┌─────────────┐
│   PDF 文献   │
└──────┬──────┘
       │ PyMuPDF (fitz)
       ▼
┌─────────────┐
│  原始文本    │ text_chunks.json
└──────┬──────┘
       │ GPT-3.5-turbo + Prompt
       ▼
┌─────────────┐
│  原始概念    │ concepts_raw.csv
│  原始关系    │ relationships_raw.csv
└──────┬──────┘
       │ Sentence Transformers + Cosine Similarity
       ▼
┌─────────────┐
│  去重概念    │ concepts_final.csv
│  合并关系    │ relationships_final.csv
└──────┬──────┘
       │ Neo4j Python Driver
       ▼
┌─────────────┐
│   Neo4j DB  │ 可视化查询
└─────────────┘
```

---

## 📊 性能指标参考

| 指标           | 数值                | 说明                |
| -------------- | ------------------- | ------------------- |
| PDF 提取速度   | ~1-2 页/秒          | 取决于 PDF 复杂度   |
| LLM 调用延迟   | ~2-5 秒/块          | 网络 + API 处理时间 |
| 嵌入计算速度   | ~50 概念/秒         | CPU，GPU 可提升 10x |
| Neo4j 导入速度 | ~100 节点/秒        | 批量导入            |
| 总处理时间     | 30 PDF → 20-40 分钟 | 主要瓶颈：LLM API   |

---

## 🔄 迭代改进路线图

### 短期优化（1-2 周）

**优先级 P0**：

- [ ] **Prompt 优化**：添加 Few-shot 示例提升概念提取准确率
- [ ] **批量处理**：合并小块减少 API 调用次数（节省 30% 成本）
- [ ] **参数自适应**：根据领域自动调整 `similarity_threshold`

**优先级 P1**：

- [ ] **智能分块**：基于句子边界而非固定字符数
- [ ] **增量更新**：支持新增 PDF 而非全量重跑
- [ ] **人工审核界面**：可视化审核边界概念

### 中期优化（1-2 月）

**功能增强**：

- [ ] **OCR 集成**：支持扫描版 PDF（PaddleOCR）
- [ ] **表格提取**：识别和结构化提取表格数据
- [ ] **多语言支持**：自动检测和分离中英文
- [ ] **实体链接**：链接到 WikiData/UMLS 等外部知识库

**算法改进**：

- [ ] **层次聚类**：使用 HDBSCAN 替代简单阈值聚类
- [ ] **图算法**：计算 PageRank、中心性、社区检测
- [ ] **混合策略**：规则 + LLM 互补提升召回率

### 长期规划（3-6 月）

**架构升级**：

- [ ] **本地 LLM**：部署 Llama-3/Qwen 节省 API 成本
- [ ] **流式处理**：实时处理大规模文献库
- [ ] **分布式计算**：支持多节点并行处理

**产品化**：

- [ ] **Web 界面**：可视化操作和结果展示
- [ ] **API 服务**：RESTful API 供其他系统调用
- [ ] **知识问答**：基于图谱的 QA 系统
- [ ] **自动更新**：定期爬取最新文献自动更新图谱

### 技术债务

**需要重构**：

- [ ] 统一配置管理（使用 `pydantic` 或 `hydra`）
- [ ] 完善单元测试（覆盖率 > 80%）
- [ ] 添加类型注解（使用 `mypy` 检查）
- [ ] 性能分析和优化（使用 `cProfile`）

**文档完善**：

- [ ] API 文档（使用 `sphinx` 生成）
- [ ] 开发者指南
- [ ] 贡献指南（CONTRIBUTING.md）

---

## 🚀 快速开始

### 1. 准备工作

- ✅ Google 账号（Colab 和 Drive）
- ✅ OpenAI API Key ([获取地址](https://platform.openai.com/api-keys))
- ✅ Neo4j Aura 免费实例 ([创建地址](https://neo4j.com/cloud/aura-free/))
- ✅ PDF 文献文件

### 2. 执行顺序

```
00 → 01 → 02 → 03 → 04
```

**按数字顺序依次打开并运行每个 notebook。**

### 3. 首次使用

1. 打开 `00_环境设置.ipynb`
2. 点击 "在 Colab 中打开"
3. 按照 notebook 中的指示操作
4. 配置 API Keys 和数据库连接
5. 依次运行后续 notebooks

## 📖 详细说明

请查看 **[COLAB\_使用指南.md](./COLAB_使用指南.md)** 获取：

- 详细的步骤说明
- 配置指南
- 常见问题解答
- Neo4j 查询示例
- 故障排除

## 🔑 必需配置

在 `00_环境设置.ipynb` 中配置以下信息：

```yaml
# OpenAI API
llm:
  api_key: "sk-..." # 你的 OpenAI API Key
  model: "gpt-3.5-turbo" # 或 'gpt-4'
  max_chunks: 30 # 限制处理量以控制成本

# Neo4j 数据库
neo4j:
  uri: "neo4j+s://..." # Neo4j Aura URI
  user: "neo4j"
  password: "..." # 数据库密码
```

## 💰 费用说明

| 项目         | 费用     | 说明                     |
| ------------ | -------- | ------------------------ |
| Google Colab | 免费     | 免费版有运行时间限制     |
| OpenAI API   | $1-5     | 取决于处理的文本量和模型 |
| Neo4j Aura   | 免费     | Free 层足够使用          |
| **总计**     | **$1-5** | 主要是 OpenAI API        |

**成本优化**:

- 使用 `gpt-3.5-turbo` 而非 `gpt-4`
- 限制 `max_chunks` 参数
- 先用少量数据测试

## 🎯 预期结果

完成所有步骤后，你将获得：

- ✅ 50-200 个去重后的概念节点
- ✅ 概念之间的关系网络
- ✅ 可在 Neo4j Browser 中交互查询的知识图谱
- ✅ 完整的中间数据文件（CSV、JSON）

## 📊 与原项目的区别

| 特性         | 原项目（本地）     | Colab 版本        |
| ------------ | ------------------ | ----------------- |
| **运行环境** | 本地 Python        | Google Colab      |
| **LLM**      | Ollama (本地)      | OpenAI API (云端) |
| **Neo4j**    | 本地实例           | Neo4j Aura (云端) |
| **费用**     | 免费（需本地资源） | $1-5（API 费用）  |
| **便携性**   | 需配置环境         | 浏览器即可运行    |
| **处理速度** | 取决于本地硬件     | 稳定云端资源      |

## 🔧 技术栈

- **Python 3.10+**
- **PyMuPDF** - PDF 文本提取
- **Sentence Transformers** - 语义嵌入
- **OpenAI GPT** - 概念提取
- **Neo4j** - 图数据库
- **pandas, numpy** - 数据处理

## 📁 输出文件

所有结果保存在 `output/` 目录：

```
output/
├── pdf_texts.json              # PDF 原始文本
├── text_chunks.json            # 分块后的文本
├── concepts_raw.csv            # 原始提取的概念
├── relationships_raw.csv       # 原始提取的关系
├── concepts_final.csv          # 去重后的最终概念
├── relationships_final.csv     # 最终关系
├── concept_mapping.json        # 概念映射表
├── extraction_stats.json       # 提取统计
├── extraction_llm_stats.json   # LLM 调用统计
├── deduplication_stats.json    # 去重统计
└── neo4j_import_stats.json     # Neo4j 导入统计
```

## ⚠️ 注意事项

1. **Colab 会话限制**: 免费版有 12 小时运行限制，超时需重新运行
2. **API 费用**: OpenAI API 按使用量计费，建议设置 billing limit
3. **数据安全**: 敏感数据请勿上传到云端
4. **网络连接**: 需要稳定的网络连接到 OpenAI 和 Neo4j

## 🆘 故障排除

### 连接问题

```python
# 测试 OpenAI API
import openai
openai.api_key = "your-key"
openai.Model.list()

# 测试 Neo4j 连接
from neo4j import GraphDatabase
driver = GraphDatabase.driver("neo4j+s://...", auth=("neo4j", "password"))
driver.verify_connectivity()
```

### 常见错误

- **API Key 无效**: 检查 OpenAI 账户余额和 key 有效性
- **Neo4j 连接失败**: 确认 URI 格式和密码正确
- **内存不足**: 减少 `max_chunks` 或使用 Colab Pro

## 📚 相关资源

- [原项目 README](../README.md)
- [OpenAI API 文档](https://platform.openai.com/docs)
- [Neo4j Cypher 文档](https://neo4j.com/docs/cypher-manual/)
- [Google Colab 文档](https://colab.research.google.com/notebooks/intro.ipynb)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 改进这些 notebooks。

## 📄 许可证

遵循原项目的许可证。

---

**开始使用**: 打开 `00_环境设置.ipynb` → 运行所有单元格 → 按顺序执行后续 notebooks

**需要帮助**: 查看 `COLAB_使用指南.md` 或提交 Issue

**祝你构建知识图谱顺利！** 🎉
