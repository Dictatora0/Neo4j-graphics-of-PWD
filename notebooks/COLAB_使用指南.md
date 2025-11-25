# 📚 Google Colab 使用指南

## 项目简介

本项目提供了一套分步的 Jupyter Notebooks，用于在 Google Colab 环境中构建松材线虫病知识图谱。

## 🚀 快速开始

### 前置准备

1. **Google 账号** - 用于访问 Google Colab 和 Drive
2. **OpenAI API Key** - 用于 LLM 概念提取（[获取地址](https://platform.openai.com/api-keys)）
3. **Neo4j 数据库** - 推荐使用 [Neo4j Aura 免费实例](https://neo4j.com/cloud/aura-free/)
4. **PDF 文献** - 松材线虫病相关的学术文献

### 步骤流程

```
00_环境设置 → 01_PDF提取 → 02_概念提取 → 03_概念去重 → 04_Neo4j导入
```

## 📖 详细步骤

### 步骤 0：环境设置 (00\_环境设置.ipynb)

**目标**: 安装依赖、配置项目环境

**操作**:

1. 打开 `00_环境设置.ipynb` 在 Colab 中
2. 按顺序运行所有单元格
3. 挂载 Google Drive
4. 上传项目代码文件（.py 文件和 config 文件夹）
5. 配置 API Keys 和数据库连接：
   ```yaml
   llm:
     api_key: "sk-..." # OpenAI API Key
   neo4j:
     uri: "neo4j+s://..." # Neo4j Aura URI
     password: "..." # Neo4j 密码
   ```

**⏱️ 预计时间**: 5-10 分钟  
**💰 费用**: 免费

---

### 步骤 1：PDF 文本提取 (01_PDF 提取.ipynb)

**目标**: 从 PDF 文件中提取文本并分块

**操作**:

1. 确保 PDF 文件已上传到指定目录
2. 运行 notebook 中的所有单元格
3. 查看提取的文本样例
4. 结果保存在 `output/` 目录

**⏱️ 预计时间**: 2-10 分钟（取决于 PDF 数量）  
**💰 费用**: 免费  
**输出**: `pdf_texts.json`, `text_chunks.json`

---

### 步骤 2：LLM 概念提取 (02\_概念提取.ipynb)

**目标**: 使用 GPT 从文本中提取概念和关系

**操作**:

1. 确认 OpenAI API Key 已配置
2. 查看将处理的文本块数量（默认 30 块）
3. 运行提取（可随时中断，已处理数据会保留）
4. 查看提取的概念和关系样例

**⚠️ 重要**:

- 此步骤会调用 OpenAI API，产生费用
- 30 块约 $1-3（使用 gpt-3.5-turbo）
- 可在配置中修改 `max_chunks` 控制处理量

**⏱️ 预计时间**: 5-15 分钟  
**💰 费用**: $1-5（取决于块数和模型）  
**输出**: `concepts_raw.csv`, `relationships_raw.csv`

---

### 步骤 3：概念去重 (03\_概念去重.ipynb)

**目标**: 使用语义嵌入识别和合并相似概念

**操作**:

1. 运行 notebook，自动加载上一步的结果
2. 等待嵌入模型计算相似度
3. 查看去重统计和最终概念
4. 过滤低质量概念

**⏱️ 预计时间**: 2-5 分钟  
**💰 费用**: 免费  
**输出**: `concepts_final.csv`, `relationships_final.csv`, `concept_mapping.json`

---

### 步骤 4：导入 Neo4j (04_Neo4j 导入.ipynb)

**目标**: 将知识图谱导入 Neo4j 数据库

**操作**:

1. 确认 Neo4j 连接信息已配置
2. 选择是否清空现有数据（`CLEAR = True/False`）
3. 运行导入
4. 验证导入结果
5. 运行示例查询

**⏱️ 预计时间**: 1-3 分钟  
**💰 费用**: 免费（使用 Aura Free）  
**输出**: Neo4j 知识图谱数据库

---

## 🔧 配置说明

### OpenAI API Key

```python
CONFIG['llm']['api_key'] = 'sk-...'
CONFIG['llm']['model'] = 'gpt-3.5-turbo'  # 或 'gpt-4'
CONFIG['llm']['max_chunks'] = 30  # 限制处理块数以控制成本
```

**获取 API Key**:

1. 访问 https://platform.openai.com/api-keys
2. 创建新的 API Key
3. 复制并粘贴到配置中

**费用预估**:

- gpt-3.5-turbo: $0.03-0.10 / 30 块
- gpt-4: $0.30-1.00 / 30 块

### Neo4j 配置

```python
CONFIG['neo4j']['uri'] = 'neo4j+s://xxxxx.databases.neo4j.io'
CONFIG['neo4j']['user'] = 'neo4j'
CONFIG['neo4j']['password'] = '...'
```

**创建 Neo4j Aura 实例**:

1. 访问 https://neo4j.com/cloud/aura-free/
2. 注册并创建免费实例
3. 获取连接 URI 和密码
4. 填入配置

---

## 📁 文件结构

```
PWD_Project/
├── notebooks/              # Colab notebooks
│   ├── 00_环境设置.ipynb
│   ├── 01_PDF提取.ipynb
│   ├── 02_概念提取.ipynb
│   ├── 03_概念去重.ipynb
│   ├── 04_Neo4j导入.ipynb
│   └── COLAB_使用指南.md
├── pdf_files/             # PDF 文献
├── modules/               # Python 模块（从原项目复制）
├── config/                # 配置文件
├── output/                # 输出结果
│   ├── pdf_texts.json
│   ├── text_chunks.json
│   ├── concepts_raw.csv
│   ├── concepts_final.csv
│   ├── relationships_raw.csv
│   ├── relationships_final.csv
│   └── *.json            # 统计信息
└── cache/                 # 缓存文件
```

---

## 💡 使用技巧

### 1. 成本控制

- **限制处理块数**: 在 `00_环境设置.ipynb` 中设置 `max_chunks = 30`
- **使用缓存**: PDF 提取会自动缓存，避免重复处理
- **选择模型**: gpt-3.5-turbo 比 gpt-4 便宜 10 倍

### 2. 会话管理

- Colab 免费版有 12 小时运行限制
- 会话超时后需重新运行 `00_环境设置.ipynb`
- 所有中间结果都已保存，不会丢失

### 3. 调试技巧

- 每个 notebook 都可以独立运行（前提是完成了前置步骤）
- 查看 `output/` 目录中的统计文件了解每步的结果
- 出错时检查 API Key 和数据库连接配置

### 4. 数据管理

- **Google Drive**: 推荐将 PDF 和项目文件放在 Drive 中
- **本地上传**: 适合少量文件，但会话结束后丢失
- **结果下载**: 最后可将 `output/` 整个目录下载保存

---

## 🔍 Neo4j 查询示例

导入完成后，在 Neo4j Browser 中尝试：

### 查看所有概念

```cypher
MATCH (n:Concept)
RETURN n LIMIT 25
```

### 查看特定类别

```cypher
MATCH (n:Concept {category: '病原体'})
RETURN n
```

### 查看关系网络

```cypher
MATCH (a:Concept)-[r]->(b:Concept)
RETURN a, r, b LIMIT 50
```

### 查找核心概念

```cypher
MATCH (n:Concept)
RETURN n.name, n.importance, n.category
ORDER BY n.importance DESC
LIMIT 10
```

### 查找概念的邻居

```cypher
MATCH (n:Concept {name: '松材线虫'})-[r]-(m:Concept)
RETURN n, r, m
```

---

## ❓ 常见问题

### Q: OpenAI API 调用失败怎么办？

**A**: 检查：

1. API Key 是否正确
2. 账户是否有余额
3. 网络连接是否正常
4. 是否超过速率限制

### Q: Neo4j 连接失败？

**A**: 检查：

1. URI 格式是否正确（`neo4j+s://...`）
2. 用户名密码是否正确
3. Neo4j 实例是否运行
4. 网络是否允许访问

### Q: Colab 会话超时了怎么办？

**A**:

1. 重新运行 `00_环境设置.ipynb`
2. 从超时的步骤继续（之前的结果已保存）

### Q: 如何减少 API 费用？

**A**:

1. 减少 `max_chunks` 值
2. 使用 gpt-3.5-turbo 而非 gpt-4
3. 先用少量数据测试

### Q: 提取的概念质量不好？

**A**:

1. 调整 `similarity_threshold` (去重阈值)
2. 调整 `min_importance` (重要性过滤)
3. 优化 prompt（在 02 中修改）

---

## 📊 项目流程图

```
┌─────────────────┐
│  准备 PDF 文献  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  环境设置       │  ← 配置 API Keys
│  (00)           │  ← 上传项目文件
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PDF 文本提取   │  ← 缓存机制
│  (01)           │  ← 文本分块
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM 概念提取   │  ← OpenAI API
│  (02)           │  ← 产生费用 💰
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  概念去重       │  ← 语义嵌入
│  (03)           │  ← 过滤低质量
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Neo4j 导入     │  ← 知识图谱
│  (04)           │  ← 可视化查询
└─────────────────┘
```

---

## 🎯 成功标准

完成所有步骤后，你应该得到：

- ✅ Neo4j 数据库中有完整的知识图谱
- ✅ 节点数量合理（通常 50-200 个概念）
- ✅ 关系连接清晰
- ✅ 可以运行 Cypher 查询
- ✅ 所有中间文件已保存到 `output/`

---

## 📞 技术支持

如遇问题，请检查：

1. **日志文件**: 每个 notebook 都有详细日志输出
2. **统计文件**: `output/*_stats.json` 包含每步的统计信息
3. **配置文件**: `config/config_colab.yaml` 确认配置正确
4. **GitHub Issues**: 原项目的 issue 页面

---

## 📝 许可证

本项目遵循原项目的许可证。

---

**祝你构建知识图谱顺利！** 🎉
