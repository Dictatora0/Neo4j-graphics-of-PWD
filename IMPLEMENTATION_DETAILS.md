# 实现细节与模块说明

> 本文档详细说明松材线虫病知识图谱构建系统的端到端数据流、核心模块源码位置与典型运行场景，为理解系统架构与生成技术汇报材料提供参考。

---

## 技术栈总览

| 技术领域        | 核心技术/库                                   | 版本要求 | 用途说明              |
| --------------- | --------------------------------------------- | -------- | --------------------- |
| **Python 环境** | Python                                        | 3.10.13+ | 基础运行环境          |
| **PDF 处理**    | PyMuPDF(fitz)                                 | latest   | 基础 PDF 解析         |
|                 | pdfplumber                                    | latest   | 表格提取优化          |
|                 | Marker                                        | latest   | AI 驱动解析（需 GPU） |
|                 | pytesseract                                   | latest   | OCR 回退机制          |
| **LLM 推理**    | Ollama                                        | latest   | 本地模型服务          |
|                 | qwen2.5-coder:7b                              | -        | 概念/关系抽取         |
|                 | qwen2-vl                                      | -        | 多模态图片理解        |
| **嵌入模型**    | sentence-transformers                         | latest   | MiniLM-L6-v2 加载     |
|                 | sentence-transformers/paraphrase-MiniLM-L6-v2 | -        | 语义去重              |
| **图处理**      | networkx                                      | latest   | 图结构操作            |
|                 | scikit-learn                                  | latest   | 聚类算法              |
| **数据存储**    | pandas                                        | latest   | CSV 数据处理          |
|                 | Neo4j                                         | 5.x+     | 图数据库              |
| **可视化**      | tqdm                                          | latest   | 进度条显示            |
|                 | tabulate                                      | latest   | 表格格式化            |
| **其他工具**    | requests                                      | latest   | HTTP 请求             |
|                 | PyYAML                                        | latest   | 配置文件解析          |
|                 | FAISS                                         | latest   | 向量相似度检索        |

---

## 系统架构图

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PDF文献输入   │───▶│   文本提取层    │───▶│   文本预处理    │
│  ./文献/*.pdf   │    │  Marker/PyMuPDF │    │  清洗/分块/OCR  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Neo4j可视化   │◀───│   图谱构建层    │◀───│   知识抽取层    │
│  样式/索引/查询 │    │  去重/过滤/导入 │    │  LLM/BGE-M3     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   高级功能扩展  │    │   容错监控层    │    │   配置管理层    │
│ GraphRAG/多模态 │    │ Checkpoint/日志 │    │  YAML/环境检查  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 1. 端到端数据流（从 PDF 到 Neo4j）

### 完整流程概览

```
PDF文献(./文献/*.pdf)
  ↓
[1] PDFExtractor.extract_from_directory
    → Layout-Aware解析(Marker/pdfplumber/PyMuPDF)
    → 结构化清洗(页眉页脚/参考文献/表格转文本)
    → OCR回退(Tesseract, 文本量<500字符时)
    → 返回 {filename: cleaned_text}
  ↓
[2] _create_chunks
    → 固定窗口3000字符+重叠300字符
    → 智能边界检测(避免切断句子/段落)
    → 生成唯一chunk_id: {pdf_name}_{counter}
    → 过滤空块(<50字符)与纯数字块
  ↓
[3] _extract_with_checkpoints (tqdm进度条)
    → ConceptExtractor.extract_concepts_and_relationships
    → Ollama API调用(qwen2.5-coder:7b, temperature=0.1)
    → JSON Schema验证(9类概念, 5级重要性)
    → CheckpointManager.save_chunk_results (增量CSV)
    → 每10块保存完整checkpoint快照
  ↓
[4] ContextualProximityAnalyzer
    → 滑动窗口内概念共现检测
    → 生成co-occurs关系(weight=0.5)
    → 为GraphRAG提供稠密图结构
  ↓
[5] ConceptDeduplicator (BGE-M3)
    → BGE-M3混合嵌入(dense+sparse, α=0.7)
    → FAISS相似度检索(阈值0.85)
    → 层次聚类算法对齐同义概念
    → RelationshipDeduplicator更新关系端点
  ↓
[6] ConceptImportanceFilter
    → 基于LLM评分(importance≥2)
    → 基于图连通度(degree≥1)
    → OR逻辑保留重要或高连接概念
  ↓
[7] _save_results
    → UTF-8-SIG编码(Excel友好)
    → concepts.csv(5列): entity,importance,category,chunk_id,type
    → relationships.csv(6列): node_1,node_2,edge,weight,chunk_id,source
  ↓
[8] import_to_neo4j_final.py (可选)
    → Cypher批量导入(UNWIND+MERGE优化)
    → 节点样式(category→color/icon)
    → 关系样式(edge→width/color)
    → 创建索引(CREATE INDEX node_name)
    → 计算图统计(度数分布/权重分析)
```

### 详细阶段说明

#### 阶段 1：PDF 文本提取

- **模块**：`pdf_extractor.PDFExtractor`
- **方法**：`extract_from_directory(directory)`
- **输入**：`./文献/` 目录下的所有 .pdf 文件
- **处理流程**：
  1. **文件遍历与验证**：
     - 使用 `glob.glob("*.pdf")` 获取文件列表
     - 验证 PDF 文件完整性（PyMuPDF 打开测试）
     - 跳过损坏或加密文件
  2. **三级解析策略**（自适应选择）：
     - **Level 1**: Marker（AI 驱动，需 GPU）
     ```python
     import marker
     markdown, metadata = marker.convert(pdf_path)
     text = self._extract_text_from_markdown(markdown)
     ```
     - **Level 2**: pdfplumber（表格优化）
       ```python
       import pdfplumber
       with pdfplumber.open(pdf_path) as pdf:
           for page in pdf.pages:
               text += page.extract_text() or ""
               tables += page.extract_tables() or []
       ```
     - **Level 3**: PyMuPDF（基础解析）
       ```python
       import fitz
       doc = fitz.open(pdf_path)
       text = "\n".join([page.get_text() for page in doc])
       ```
  3. **结构化后处理**：
     - **页眉页脚移除**：基于 Y 坐标位置（<5%或>95%页面高度）
     - **参考文献检测**：正则匹配"参考文献"、"References"等关键词
     - **表格转描述**：使用 `tabulate` 库转换为自然语言
     - **文本规范化**：Unicode 标准化(NFKC)、去除控制字符
  4. **OCR 回退机制**（文本量<500 字符）：
     ```python
     import pytesseract
     from PIL import Image
     images = pdf2image.convert_from_path(pdf_path)
     ocr_text = "\n".join([pytesseract.image_to_string(img, lang='chi_sim') for img in images])
     ```
- **输出**：`Dict[str, str]` 格式，如 `{"paper1.pdf": "清洗后的完整文本..."}`
- **日志格式示例**：
  ```
  INFO - 找到 X 个PDF文件
  INFO - 开始提取: paperX.pdf
  INFO - 使用pdfplumber进行表格提取和优化解析
  INFO - 提取完成: paperX.pdf, XXXXX 字符
  ```

#### 阶段 2：文本分块

- **模块**：`enhanced_pipeline_safe.EnhancedKnowledgeGraphPipelineSafe`
- **方法**：`_create_chunks(pdf_texts, chunk_size=3000, overlap=300)`
- **处理逻辑**：

  ```python
  def _create_chunks(self, pdf_texts: Dict[str, str], chunk_size: int = 3000,
                    overlap: int = 300) -> List[Dict]:
      """分块"""
      chunks = []
      chunk_id_counter = 0

      for pdf_name, text in pdf_texts.items():
          for i in range(0, len(text), chunk_size - overlap):
              chunk_text = text[i:i + chunk_size]

              if len(chunk_text.strip()) > 50:
                  chunks.append({
                      'text': chunk_text,
                      'chunk_id': f"{pdf_name}_{chunk_id_counter}",
                      'source_pdf': pdf_name,
                      'concepts': []
                  })
                  chunk_id_counter += 1

      return chunks
  ```

- **关键技术**：
  - **重叠策略**：300 字符重叠确保上下文连续性
  - **质量过滤**：过滤长度小于 50 字符的文本块
  - **唯一标识**：生成格式为 `{pdf_name}_{counter}` 的 chunk_id
- **输出**：`List[Dict]`，每个元素包含 `text`, `chunk_id`, `source_pdf`, `concepts`
- **日志格式示例**：
  ```
  INFO - Created XXX chunks
  ```

#### 阶段 3：LLM 概念/关系抽取（核心阶段）

- **模块**：`concept_extractor.ConceptExtractor`
- **方法**：`extract_concepts_and_relationships(text, chunk_id)`
- **LLM 配置**：
  - 模型：`qwen2.5-coder:7b` (通过 Ollama 本地推理)
  - 超时：600 秒
  - 温度：0.1（低随机性）
  - JSON 模式：严格 Schema 输出
- **Prompt 结构**：

  - **System Prompt**（角色定义）：

    ```python
    system_prompt = """你是专业的松材线虫病知识图谱构建系统。你的任务是从科学文献中同时提取概念和关系。

    ## 输出要求
    严格按照以下 JSON Schema 输出，不得添加任何解释或 markdown：

    {
      "concepts": [
        {"entity": "概念名称", "importance": 1-5整数, "category": "类别"}
      ],
      "relationships": [
        {"node_1": "源实体", "node_2": "目标实体", "edge": "关系类型"}
      ]
    }

    ## 概念提取范围
    **病原** (pathogen): 松材线虫、Bursaphelenchus xylophilus、伴生细菌
    **寄主** (host): 马尾松、黑松、湿地松、赤松、云南松
    **媒介** (vector): 松褐天牛、云杉花墨天牛、Monochamus alternatus
    **症状** (symptom): 萎蔫、针叶变色、树脂分泌异常、枯死
    **防治** (treatment): 阿维菌素、噻虫啉、诱捕器、生物防治
    **环境** (environment): 温度、湿度、降水、海拔
    **地点** (location): 疫区、省份、分布区
    **机制** (mechanism): 侵染途径、致病机理
    **化合物** (compound): 萜烯、酚类、杀虫剂成分

    ## 关系类型
    **因果**: 引起、导致、诱发
    **传播**: 传播、携带、扩散
    **寄生**: 感染、寄生于、侵染
    **防治**: 防治、控制、抑制、杀灭
    **影响**: 影响、促进、抑制
    **分布**: 分布于、发生于

    ## 重要性评分
    5-核心概念, 4-重要概念, 3-一般概念, 2-次要概念, 1-边缘概念

    只输出 JSON 对象！"""
    ```

  - **User Prompt**（任务指令）：

    ```python
    user_prompt = f"""从以下松材线虫病科学文本中提取概念和关系：

    {text}

    输出格式示例：
    {{
      "concepts": [
        {{"entity": "松材线虫", "importance": 5, "category": "pathogen"}},
        {{"entity": "松褐天牛", "importance": 5, "category": "vector"}},
        {{"entity": "马尾松", "importance": 4, "category": "host"}}
      ],
      "relationships": [
        {{"node_1": "松材线虫", "node_2": "马尾松", "edge": "感染"}},
        {{"node_1": "松褐天牛", "node_2": "松材线虫", "edge": "传播"}}
      ]
    }}"""
    ```

- **调用流程**：

  ```python
  for i, chunk in enumerate(tqdm(chunks, desc="Extracting concepts")):
      text = chunk.get('text', '')
      chunk_id = chunk.get('chunk_id', '')

      if not text or len(text.strip()) < 20:
          continue

      # 核心抽取
      concepts, relationships = self.concept_extractor.extract_concepts_and_relationships(
          text, chunk_id
      )

      if concepts:
          all_concepts.extend(concepts)
          logger.debug(f"Extracted {len(concepts)} concepts")

      if relationships:
          all_relationships.extend(relationships)
          logger.debug(f"Extracted {len(relationships)} relationships")

      # 增量保存
      self.checkpoint_manager.save_chunk_results(chunk_id, concepts, relationships)

      # 定期快照
      if (i + 1) % self.checkpoint_interval == 0:
          logger.info(f"Checkpoint: {i+1}/{len(chunks)} chunks processed")
  ```

- **容错处理机制**：

  - LLM 返回 None → 转为空列表 `[]`
  - JSON 解析失败 → 记录错误，返回 None
  - 超时/网络错误 → 重试 3 次，失败后 continue

- **日志格式示例**（数值仅为示意）：
  ```
  INFO - Extracting concepts from XXX chunks...
  INFO - Processing chunks: X%|██▏  | XX/XXX [mm:ss<hh:mm:ss, XX.XXs/it]
  INFO - Checkpoint: XX/XXX chunks processed
  DEBUG - Extracted X concepts, X relationships from chunk paperX.pdf_X
  ```

#### 阶段 4：增量保存与进度追踪

- **模块**：`checkpoint_manager.CheckpointManager`
- **核心方法**：
  - `save_chunk_results(chunk_id, concepts, relationships)`：追加写入 CSV，更新进度 JSON
  - `save_checkpoint(chunk_num, concepts_df, relationships_df)`：保存完整快照
  - `get_processed_chunks()`：返回已处理块列表，用于断点续传
- **文件结构**：
  ```
  output/checkpoints/
  ├── .progress.json                              # 进度追踪
  ├── concepts_incremental.csv                    # 增量概念
  ├── relationships_incremental.csv               # 增量关系
  ├── checkpoint_concepts_40_20251129_223048.csv  # 快照
  └── checkpoint_relationships_40_20251129_223048.csv
  ```
- **.progress.json 格式**：
  ```json
  {
    "processed_chunks": ["paper1.pdf_0", "paper1.pdf_1", ...],
    "total_concepts": 320,
    "total_relationships": 250,
    "started_at": "2025-11-29T19:30:00",
    "last_update": "2025-11-29T20:48:15"
  }
  ```
- **断点续传逻辑**：
  ```python
  processed_chunks = checkpoint_manager.get_processed_chunks()
  remaining = [c for c in chunks if c['chunk_id'] not in processed_chunks]
  logger.info(f"Skipping {len(processed_chunks)} already processed chunks")
  ```

#### 阶段 5：语境近邻关系

- **模块**：`concept_extractor.ContextualProximityAnalyzer`
- **方法**：`extract_proximity_relationships(chunks)`
- **逻辑**：

  ```python
  @staticmethod
  def extract_proximity_relationships(chunks: List[Dict]) -> pd.DataFrame:
      """Extract relationships based on contextual proximity"""
      proximity_relationships = []

      for chunk in chunks:
          concepts = chunk.get('concepts', [])
          chunk_id = chunk.get('chunk_id', '')

          # Create pairwise relationships for all concepts in the chunk
          for i, concept1 in enumerate(concepts):
              for concept2 in concepts[i+1:]:
                  if concept1 != concept2:
                      proximity_relationships.append({
                          'node_1': concept1.lower(),
                          'node_2': concept2.lower(),
                          'edge': 'co-occurs in',
                          'weight': 0.5,  # W2 weight for contextual proximity
                          'chunk_id': chunk_id,
                          'source': 'proximity'
                      })

      return pd.DataFrame(proximity_relationships) if proximity_relationships else pd.DataFrame()
  ```

- **目的**：为 GraphRAG 社区检测提供更稠密的图结构

#### 阶段 6：语义去重与实体对齐

- **模块**：`concept_deduplicator.ConceptDeduplicator` + `SentenceTransformerEmbedding`
- **方法**：`deduplicate_concepts(concepts_df)`
- **技术实现**：

  ```python
  def deduplicate_concepts(self, concepts_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
      """Deduplicate concepts based on semantic similarity"""
      if concepts_df.empty:
          return concepts_df, {}

      # Get unique concepts
      unique_concepts = concepts_df['entity'].unique()

      if len(unique_concepts) < 2:
          return concepts_df, {concept: concept for concept in unique_concepts}

      # Generate embeddings using sentence-transformers
      embeddings = self.embedding_provider.embed(list(unique_concepts))

      # Calculate similarity matrix
      similarity_matrix = cosine_similarity(embeddings)

      # Find duplicate clusters using hierarchical clustering
      clusters = self._cluster_similar_concepts(similarity_matrix, unique_concepts)

      # Create concept mapping
      concept_mapping = {}
      for cluster in clusters:
          if len(cluster) > 1:
              # Select canonical concept (highest importance)
              cluster_concepts = concepts_df[concepts_df['entity'].isin(cluster)]
              canonical = cluster_concepts.loc[cluster_concepts['importance'].idxmax(), 'entity']

              for concept in cluster:
                  if concept != canonical:
                      concept_mapping[concept] = canonical

      # Apply mapping to concepts
      deduplicated_df = concepts_df.copy()
      deduplicated_df['entity'] = deduplicated_df['entity'].map(
          lambda x: concept_mapping.get(x, x)
      )

      return deduplicated_df, concept_mapping
  ```

- **关系更新策略**：

  ```python
  @staticmethod
  def update_relationships(relationships_df: pd.DataFrame,
                          concept_mapping: Dict[str, str]) -> pd.DataFrame:
      """Update relationships to use canonical concept names"""
      # Map node_1 and node_2 to canonical names
      relationships_df['node_1'] = relationships_df['node_1'].map(
          lambda x: concept_mapping.get(x, x)
      )
      relationships_df['node_2'] = relationships_df['node_2'].map(
          lambda x: concept_mapping.get(x, x)
      )

      # Remove self-loops
      relationships_df = relationships_df[
          relationships_df['node_1'] != relationships_df['node_2']
      ]

      return relationships_df
  ```

- **效果示例**：
  - `"松材线虫"` ↔ `"Bursaphelenchus xylophilus"` → `"松材线虫"`
  - `"马尾松"` ↔ `"Pinus massoniana"` → `"马尾松"`
  - `"松褐天牛"` ↔ `"Monochamus alternatus"` → `"松褐天牛"`
- **日志示例**：
  ```
  INFO - Deduplicating XXX concepts...
  INFO - Using sentence-transformers for semantic similarity
  INFO - Updated relationships after deduplication: XXX relationships
  ```

#### 阶段 7：重要性与连通度过滤

- **模块**：`concept_deduplicator.ConceptImportanceFilter`
- **方法**：`filter_concepts(concepts_df, relationships_df, min_importance=2, min_connections=1)`
- **过滤逻辑**：

  ```python
  def filter_concepts(concepts_df: pd.DataFrame,
                     relationships_df: pd.DataFrame,
                     min_importance: int = 2,
                     min_connections: int = 1) -> pd.DataFrame:
      """Filter concepts based on importance and connectivity"""
      filtered_df = concepts_df.copy()

      # Filter out generic concepts
      initial_count = len(filtered_df)
      filtered_df = filtered_df[
          ~filtered_df['entity'].isin(self.GENERIC_CONCEPTS)
      ]

      # Filter by importance
      filtered_df = filtered_df[
          filtered_df['importance'] >= min_importance
      ]

      # Filter by connectivity (if relationships provided)
      if not relationships_df.empty:
          # Count connections for each concept
          node1_counts = relationships_df['node_1'].value_counts()
          node2_counts = relationships_df['node_2'].value_counts()
          connection_counts = (node1_counts + node2_counts).fillna(0)

          # Apply connectivity filter
          filtered_df = filtered_df[
              filtered_df['entity'].map(connection_counts) >= min_connections
          ]

      return filtered_df
  ```

- **目的**：去除孤立节点与低权重噪声

#### 阶段 8：结果落盘

- **文件**：`output/concepts.csv`, `output/relationships.csv`
- **格式**：UTF-8-SIG 编码（Excel 友好），包含 header
- **concepts.csv 列**：`entity, importance, category, chunk_id, type`
- **relationships.csv 列**：`node_1, node_2, edge, weight, chunk_id, source`

#### 阶段 9：Neo4j 图谱导入（可选）

- **模块**：`neo4j_generator.Neo4jGenerator`
- **流程**：
  1. 读取 concepts.csv 和 relationships.csv
  2. 生成 Cypher 导入脚本
  3. 创建约束和索引
  4. 批量导入节点和关系
- **关键代码**：

  ```python
  class Neo4jGenerator:
      def __init__(self, config):
          self.config = config

      def generate_cypher_script(self, concepts_df, relationships_df):
          """Generate Cypher script for bulk import"""
          script = []

          # Create constraints
          script.append("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE")

          # Import nodes
          script.append("""
          UNWIND $concepts AS concept
          MERGE (c:Concept {name: concept.entity})
          SET c.importance = concept.importance,
              c.category = concept.category,
              c.chunk_id = concept.chunk_id
          """)

          # Import relationships
          script.append("""
          UNWIND $relationships AS rel
          MATCH (a:Concept {name: rel.node_1})
          MATCH (b:Concept {name: rel.node_2})
          MERGE (a)-[r:RELATED {type: rel.edge}]->(b)
          SET r.weight = rel.weight,
              r.chunk_id = rel.chunk_id
          """)

          return "\\n".join(script)
  ```

---

## 2. 核心模块与源码位置速查表

| 功能阶段              | 主要文件                      | 核心类/函数                                            | 说明                                           |
| --------------------- | ----------------------------- | ------------------------------------------------------ | ---------------------------------------------- |
| **PDF 解析与结构化**  | `pdf_extractor.py`            | `PDFExtractor`                                         | Layout-Aware、表格转文本、OCR 回退             |
| **文本分块**          | `enhanced_pipeline_safe.py`   | `EnhancedKnowledgeGraphPipelineSafe._create_chunks`    | 固定窗口+overlap 生成 chunk_id                 |
| **LLM 概念/关系抽取** | `concept_extractor.py`        | `ConceptExtractor.extract_concepts_and_relationships`  | Ollama+Qwen2.5，严格 JSON Schema               |
| **语境近邻关系**      | `concept_extractor.py`        | `ContextualProximityAnalyzer`                          | 块内共现生成 co-occurs 关系                    |
| **语义去重与对齐**    | `concept_deduplicator.py`     | `ConceptDeduplicator`, `SentenceTransformerEmbedding`  | sentence-transformers 语义相似度，对齐同义概念 |
| **关系端点更新**      | `concept_deduplicator.py`     | `RelationshipDeduplicator.update_relationships`        | 将关系两端替换为规范名                         |
| **重要性过滤**        | `concept_deduplicator.py`     | `ConceptImportanceFilter.filter_concepts`              | 基于 importance 与度数筛选                     |
| **安全流水线**        | `enhanced_pipeline_safe.py`   | `EnhancedKnowledgeGraphPipelineSafe`                   | 增量保存、断点续传、多层容错                   |
| **进度管理**          | `checkpoint_manager.py`       | `CheckpointManager`                                    | 追踪 processed_chunks，保存快照                |
| **启动与环境检查**    | `run_pipeline.py`, `start.sh` | `main()`, shell 脚本                                   | 检查 Ollama、模型、依赖，打印时间估算          |
| **状态监控**          | `status.sh`, `monitor.sh`     | shell 脚本                                             | 读取.progress.json，展示实时状态               |
| **Neo4j 导入**        | `import_to_neo4j_final.py`    | 主流程脚本                                             | 应用样式、创建索引、计算度数                   |
| **Cypher 生成**       | `neo4j_generator.py`          | `Neo4jGenerator`                                       | 生成 nodes.csv、relations.csv、import.cypher   |
| **Agentic Workflow**  | `agentic_extractor.py`        | `AgenticExtractor`, `CriticAgent`, `RefineAgent`       | Extract→Critic→Refine 三阶段质量提升           |
| **GraphRAG 社区摘要** | `graph_rag.py`                | `GraphRAG`, `CommunityDetector`, `CommunitySummarizer` | Louvain/Leiden 社区检测+LLM 摘要               |
| **多模态扩展**        | `multimodal_extractor.py`     | `MultimodalExtractor`                                  | 图片描述生成（Qwen2-VL），可选功能             |

---

## 3. 典型运行场景与监控

### 场景 1：首次完整运行

**步骤**：

1. 准备数据：将 PDF 文献放入 `./文献/` 目录
2. 检查配置：编辑 `config/config.yaml`
   ```yaml
   llm:
     model: qwen2.5-coder:7b
     max_chunks: 100 # 或null表示全部处理
     timeout: 600
   deduplication:
     use_bge_m3: true
     similarity_threshold: 0.85
   ```
3. 启动服务：`ollama serve` （另一终端）
4. 启动管道：`./start.sh`
5. 监控进度：`./monitor.sh` （另一终端）

**预期输出格式**（数值仅为示意）：

```
============================================================
知识图谱构建系统 v2.5
============================================================

[INFO] Python版本: X.XX.XX
[INFO] Ollama服务: 运行中
[INFO] LLM模型: qwen2.5-coder:7b
[INFO] PDF文件: XX 个

============================================================
提示:
  - 按 Ctrl+C 可安全退出并保存进度
  - 在另一个终端运行 './monitor.sh' 查看进度
  - 日志文件: output/kg_builder.log
============================================================

[Step 1/6] Extracting text from PDFs...
找到 XX 个PDF文件
提取PDF文本: 100%|████████████████████| XX/XX [mm:ss<00:00]

[Step 2/6] Splitting texts into chunks...
Created XXX chunks

[Step 3/6] Extracting concepts with checkpoint support...
Extracting concepts:  X%|██▏         | XX/XXX [mm:ss<hh:mm:ss, XX.XXs/it]
Checkpoint: XX/XXX chunks processed
```

### 场景 2：中途中断后恢复

**场景描述**：运行过程中按 Ctrl+C 或程序崩溃

**恢复步骤**：

1. 直接再次运行 `./start.sh`
2. 系统自动检测 checkpoint

**输出示例**：

```
============================================================
RESUMING from previous checkpoint:
  - Processed chunks: XX
  - Total concepts: XXX
  - Total relationships: XXX
============================================================

[Step 2/6] Splitting texts into chunks...
Skipping XX already processed chunks
Remaining chunks to process: XXX

[Step 3/6] Extracting concepts with checkpoint support...
Extracting concepts:  0%|          | 0/462 [00:00<?, ?it/s]
```

### 场景 3：实时监控（monitor.sh）

**运行**：`./monitor.sh`

**输出格式示例**（数值仅为示意）：

```
════════════════════════════════════════════════════════════════════════
 📊 知识图谱构建进度监控
 更新时间: YYYY-MM-DD HH:MM:SS
════════════════════════════════════════════════════════════════════════

✓ 管道进程: 运行中
  PID: XXXXX, CPU: XX.X%, 内存: X.X%

📝 Checkpoint 进度:
  已处理块数: XX
  总概念数: XXX
  总关系数: XXX
  最后更新: YYYY-MM-DD HH:MM:SS

⏱️  时间估算:
  已运行: XX 分钟
  平均速度: XX 秒/块
  剩余时间: 约 XXX 分钟

📁 输出文件:
  ✓ concepts.csv: XXK (XXX 行)
  ✓ relationships.csv: XXK (XXX 行)
  ✓ .progress.json: X.XK

📋 最近日志:
  YYYY-MM-DD HH:MM:SS - SafePipeline - INFO - Checkpoint: XX/XXX chunks processed
  YYYY-MM-DD HH:MM:SS - CheckpointManager - INFO - Saved results for chunk: paperX.pdf_XX

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 快捷操作: [r] 刷新  [l] 查看完整日志  [q] 退出
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 4. 关键日志模式与调试

### 正常运行日志

```
2025-11-29 19:30:00 - SafePipeline - INFO - Starting Safe Enhanced Pipeline with Checkpoint Support
2025-11-29 19:30:01 - SafePipeline - INFO - [Step 1/6] Extracting text from PDFs...
2025-11-29 19:30:45 - SafePipeline - INFO - [Step 2/6] Splitting texts into chunks...
2025-11-29 19:30:46 - SafePipeline - INFO - Created 507 chunks
2025-11-29 19:30:46 - SafePipeline - INFO - [Step 3/6] Extracting concepts with checkpoint support...
2025-11-29 19:32:18 - CheckpointManager - INFO - Saved results for chunk: paper1.pdf_0
2025-11-29 19:33:50 - CheckpointManager - INFO - Saved results for chunk: paper1.pdf_1
...
2025-11-29 20:30:10 - SafePipeline - INFO - Checkpoint: 40/507 chunks processed
2025-11-29 20:30:10 - CheckpointManager - INFO - Checkpoint saved at chunk 40
```

### 异常模式与处理

**1. LLM 超时**

```
ERROR - Ollama API timeout after 3 attempts for chunk paper5.pdf_23
WARNING - Chunk paper5.pdf_23: LLM returned None, using empty results
INFO - Checkpoint: saved chunk paper5.pdf_23 with 0 concepts, 0 relationships
```

→ 系统继续处理下一块，不中断

**2. JSON 解析失败**

```
ERROR - JSON 解析失败 [paper8.pdf_15] - Qwen 未正确输出 JSON
ERROR - 原始响应（前500字符）: Here are the concepts: {...
```

→ 返回 None，记录日志，继续

**3. Ctrl+C 用户中断**

```
WARNING - User interrupted (Ctrl+C)
WARNING - ============================================================
INFO - Checkpoint已自动保存，下次运行将从中断处继续
INFO - 进度保存位置: output/checkpoints
```

→ 优雅退出，保存进度

---

## 5. 性能指标与实验数据

> **说明**：以下数据来源于项目 README.md 中的性能评估章节与技术挑战文档，具体数值会因硬件环境、文本复杂度而有所差异。

### 关键性能指标（来自 README）

**模型选型**（参见 README "核心创新点 - LLM 性能优化"）：

- 项目最终选择 `qwen2.5-coder:7b` 模型
- 处理时间：相比更大模型显著优化
- 超时率：通过参数优化和重试机制大幅降低

**嵌入模型对比**（参见 README "性能指标 - 嵌入模型对比"）：

- 使用 BGE-M3 替代 MiniLM-L6
- 中文语义相似度识别能力提升
- 专业术语对齐效果增强
- 支持中英文混合场景的实体对齐

**Checkpoint 机制效果**（参见 README "核心创新点 - Checkpoint 机制"）：

- 最大损失时间：显著减少处理中断时的数据损失
- 数据丢失风险：通过增量保存机制大幅降低
- 系统可用性：断点续传功能显著提升稳定性

**处理时间分布**（参考 README "性能指标"）：

- PDF 提取：占用较小部分时间
- 文本分块：处理速度较快
- LLM 推理：主要时间消耗（取决于文本量和模型性能）
- 语义去重：相对较快
- GraphRAG（可选）：额外处理时间
- 总处理时间：取决于文献数量和硬件配置

> 注：实际运行时间受硬件配置（CPU/GPU）、文献数量、文本复杂度等因素影响。

---

## 6. 扩展阅读与高级功能

### Agentic Workflow（可选功能）

- **文件**：`agentic_extractor.py`
- **工作流**：Extract Agent → Critic Agent → Refine Agent
- **启用方式**：
  ```yaml
  agentic:
    enable_llm_review: true
    review_confidence_range: [0.6, 0.85]
  ```
- **效果**（参考 README "Agentic Workflow 说明"）：
  - 通过三阶段质量审查提升抽取准确性
  - 减少逻辑错误和实体识别问题
  - 注意：会增加处理时间和计算资源消耗

### GraphRAG 社区摘要（可选，支持全局查询）

- **文件**：`graph_rag.py`
- **功能**：
  1. 社区检测：Louvain/Leiden 算法
  2. LLM 摘要：为每个社区生成主题与描述
- **启用方式**：
  ```yaml
  agentic:
    enable_graph_rag: true
    community_algorithm: louvain
  ```
- **使用场景**：回答"防治策略整体格局"等宏观问题

### 多模态扩展（预留接口）

- **文件**：`multimodal_extractor.py`
- **功能**：提取 PDF 图片 → Qwen2-VL 生成描述 → 作为文本块抽取
- **启用方式**：
  ```yaml
  pdf:
    enable_image_captions: true
    caption_model: qwen2-vl
  ```

---

## 7. 故障排查速查

| 问题              | 日志模式                                    | 解决方案                            |
| ----------------- | ------------------------------------------- | ----------------------------------- |
| Ollama 服务未启动 | `ConnectionError: Cannot connect to Ollama` | 运行 `ollama serve`                 |
| 模型未安装        | `Model 'qwen2.5-coder:7b' not found`        | 运行 `ollama pull qwen2.5-coder:7b` |
| LLM 超时          | `Ollama API timeout after 3 attempts`       | 增加 `llm.timeout` 或换更小模型     |
| JSON 解析失败     | `JSON 解析失败 - Qwen 未正确输出 JSON`      | 检查 temperature 设置，降至 0.05    |
| BGE-M3 加载失败   | `Failed to initialize embeddings`           | 检查磁盘空间，模型需~2GB            |
| Neo4j 连接失败    | `Unable to connect to Neo4j`                | 检查服务状态与密码                  |

---

## 8. 高级功能技术实现

### 8.1 Agentic Workflow 三阶段质量提升

- **文件**：`agentic_extractor.py`
- **核心类**：
  - `ExtractAgent`: 初次抽取概念和关系
  - `CriticAgent`: 审查抽取质量，识别错误和逻辑谬误
  - `RefineAgent`: 根据审稿意见修正和优化结果
- **工作流程**：
  1. Extract Agent 使用 LLM 初步抽取
  2. Critic Agent 检查本体符合性、逻辑一致性
  3. Refine Agent 根据审查结果优化输出
- **本体定义**：
  ```python
  self.ontology = {
      'valid_categories': ['pathogen', 'host', 'vector', 'symptom', 'treatment',
                         'environment', 'location', 'mechanism', 'compound'],
      'valid_relations': ['引起', '导致', '诱发', '传播', '携带', '扩散',
                        '感染', '寄生于', '侵染', '防治', '控制', '抑制',
                        '杀灭', '影响', '促进', '分布于', '发生于'],
  }
  ```

### 8.2 GraphRAG 社区检测与摘要

- **文件**：`graph_rag.py`
- **核心类**：`CommunityDetector`
- **支持算法**：
  - Louvain: 快速模块度优化算法（需要 NetworkX）
  - Leiden: 改进的 Louvain 算法（需要 igraph）
  - Label Propagation: 标签传播算法
  - Connected Components: 连通分量（基础算法）
- **算法流程**：

  ```python
  def detect_communities(self, concepts_df: pd.DataFrame,
                        relationships_df: pd.DataFrame) -> Dict[int, List[str]]:
      """检测知识图谱中的社区"""
      if concepts_df.empty or relationships_df.empty:
          return {}

      if self.algorithm == 'louvain':
          return self._detect_louvain(concepts_df, relationships_df)
      elif self.algorithm == 'leiden':
          return self._detect_leiden(concepts_df, relationships_df)
      elif self.algorithm == 'label_propagation':
          return self._detect_label_propagation(concepts_df, relationships_df)
      else:
          return self._detect_connected_components(concepts_df, relationships_df)
  ```

- **社区摘要 Prompt**：

  ```python
  summary_prompt = f"""基于以下知识图谱社区信息，生成简洁的摘要：

  社区节点：{', '.join(nodes)}
  核心概念：{core_concepts}
  主要关系：{key_relationships}

  请生成100字以内的社区主题描述，突出该社区的核心特征。
  """
  ```

### 8.3 多模态扩展（图片知识抽取）

- **文件**：`multimodal_extractor.py`
- **核心类**：`ImageExtractor`
- **功能**：
  - 从 PDF 中提取图片（显微镜照片、统计图表、分布地图）
  - 使用 VLM（Vision-Language Models）生成图片描述
  - 从图片描述中抽取知识三元组
- **支持模型**：
  - Qwen2-VL-7B（本地 Ollama）
  - LLaVA-Next（本地 Ollama）
  - transformers（本地 GPU）
- **图片提取流程**：

  ```python
  def extract_images_from_pdf(self, pdf_path: str) -> List[Dict]:
      """从 PDF 中提取图片"""
      doc = fitz.open(pdf_path)
      images_info = []

      for page_num in range(len(doc)):
          page = doc[page_num]
          image_list = page.get_images()

          for img_index, img in enumerate(image_list):
              xref = img[0]
              pix = fitz.Pixmap(doc, xref)

              # 质量过滤
              if pix.width < self.min_width or pix.height < self.min_height:
                  pix = None
                  continue

              # 保存图片
              img_path = f"{self.output_dir}/{pdf_name}_p{page_num}_{img_index}.png"
              pix.save(img_path)

              images_info.append({
                  'path': img_path,
                  'page': page_num,
                  'size': (pix.width, pix.height)
              })

              pix = None
      return images_info
  ```

              f"{self.ollama_host}/api/generate",
              json={
                  "model": "qwen2-vl",
                  "prompt": prompt,
                  "images": [image_data],
                  "stream": False
              },
              timeout=120
          )

          return response.json().get('response', '')

  ```

  ```

### 8.4 Neo4j 高级查询与可视化

- **Cypher 查询优化**：

  ```cypher
  // 批量创建节点（使用UNWIND优化）
  UNWIND $concepts AS concept
  MERGE (c:Concept {name: concept.entity})
  SET c.importance = concept.importance,
      c.category = concept.category,
      c.source = concept.chunk_id

  // 批量创建关系
  UNWIND $relationships AS rel
  MATCH (a:Concept {name: rel.node_1})
  MATCH (b:Concept {name: rel.node_2})
  MERGE (a)-[r:RELATED {type: rel.edge}]->(b)
  SET r.weight = rel.weight,
      r.source = rel.chunk_id

  // 创建全文索引
  CREATE FULLTEXT INDEX concept_fulltext FOR (c:Concept) ON EACH [c.name]
  ```

- **高级分析查询**：

  ```cypher
  // 查找关键路径（病原体→寄主→症状）
  MATCH path = (p:Concept {category:'pathogen'})-[]->(h:Concept {category:'host'})-[]->(s:Concept {category:'symptom'})
  RETURN path, length(path) as path_length
  ORDER BY path_length
  LIMIT 10

  // 社区影响力分析
  MATCH (c:Concept)-[r]-(n:Concept)
  WITH c, count(n) as connections, sum(r.weight) as total_weight
  WHERE c.importance >= 4
  RETURN c.name, c.category, connections, total_weight
  ORDER BY total_weight DESC

  // 防治方法效果评估
  MATCH (p:Concept {category:'prevention'})-[r:PREVENTS]->(d:Concept {category:'pathogen'})
  RETURN p.name, r.weight, d.name
  ORDER BY r.weight DESC
  ```

---

**本文档持续更新中，如有疑问请参考 `docs/TECHNICAL_CHALLENGES.md` 或项目 README。**
