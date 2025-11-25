# 项目文件整理说明

## 整理日期

2025-11-25

## 整理目标

将项目文件按功能分类，提高代码可维护性和可读性，使项目结构更加清晰。

---

## 新的目录结构

```
PWD/
├── README.md                      # 项目主文档
├── requirements.txt               # Python 依赖
├── .gitignore                     # Git 忽略规则
│
├── docs/                          # 📄 文档目录
│   ├── PROJECT_STRUCTURE.txt      # 项目结构说明
│   ├── PROJECT_ORGANIZATION.md    # 项目整理说明（本文件）
│   └── PWD_Knowledge_Graph_Analysis.html  # 分析报告HTML版本
│
├── notebooks/                     # 📓 Jupyter Notebooks
│   ├── PWD_Knowledge_Graph_Analysis.ipynb  # 主分析笔记本
│   └── PWD_KG_Notebook.ipynb      # 知识图谱笔记本
│
├── 核心脚本（主流程）              # 🔧 保持在项目根目录
│   ├── main.py                    # 主入口程序
│   ├── enhanced_pipeline.py       # LLM 概念与关系抽取管道
│   ├── concept_extractor.py       # 概念与关系抽取
│   ├── concept_deduplicator.py    # 嵌入式去重与合并
│   ├── data_cleaner.py            # 数据清洗与规范化
│   ├── neo4j_generator.py         # 生成 Neo4j 导入文件
│   ├── neo4j_manager.py           # Neo4j 备份、清空与回滚
│   ├── pdf_extractor.py           # PDF 文本提取
│   ├── ocr_processor.py           # OCR 处理
│   ├── entity_linker.py           # 实体链接
│   ├── parallel_processor.py      # 并行处理
│   ├── bio_semantic_review.py     # 三元组语义体检
│   └── import_to_neo4j_final.py   # 使用三元组导入最终图谱
│
├── scripts/                       # 📜 辅助脚本目录
│   ├── workflow/                  # 工作流脚本
│   │   ├── run_complete_workflow.sh  # 一键运行完整流程
│   │   ├── check_progress.sh      # 运行进度检查
│   │   ├── clean_project.sh       # 输出与缓存清理
│   │   └── organize_project.sh    # 项目文件整理
│   └── utils/                     # 工具脚本
│       ├── export_for_review.py   # 导出审查文件
│       ├── export_triples.py      # 导出三元组
│       ├── export_neo4j_to_csv.py # 从数据库导出 CSV
│       ├── export_notebook_to_pdf.py # 导出笔记本为PDF
│       ├── auto_disambiguate.py   # 自动消歧
│       ├── cache_manager.py       # 缓存管理
│       ├── config_loader.py       # 配置加载
│       ├── logger_config.py       # 日志配置
│       └── visualize_neo4j_graph.py # Neo4j 图可视化
│
├── config/                        # ⚙️ 配置文件
│   ├── config.yaml                # 主配置文件
│   ├── domain_dict.json           # 领域词典
│   └── stopwords.txt              # 停用词表
│
├── output/                        # 📊 输出目录
│   ├── concepts*.csv              # 概念相关中间结果
│   ├── relationships*.csv         # 关系相关中间结果
│   ├── entities_clean.csv         # 清洗后实体
│   ├── relations_clean.csv        # 清洗后关系
│   ├── neo4j_import/              # Neo4j 导入文件与脚本
│   ├── triples/                   # 三元组相关中间结果
│   ├── analysis_results/          # 分析结果
│   ├── cache/                     # 缓存文件
│   ├── neo4j_backups/             # Neo4j 备份
│   ├── statistics_report.txt      # 抽取/清洗阶段统计
│   └── *.md/*.json                # 数据检查与导入报告
│
├── archive/                       # 🗄️ 开发过程存档
│   ├── scripts/                   # 调试和中间版本脚本
│   │   ├── apoc_error_fix.py
│   │   ├── apoc_fix_notebook.py
│   │   ├── comprehensive_fix.py
│   │   ├── create_apoc_fix_guide.py
│   │   ├── fix_apoc_query.py
│   │   ├── fix_path_processing.py
│   │   ├── fix_remaining_relations.py
│   │   ├── fix_semantic_triples.py
│   │   └── refine_node_labels.py
│   └── docs/                      # 旧文档和报告
│
├── 文献/                          # 📚 PDF 文献目录
└── venv/                          # 🐍 虚拟环境（不纳入版本控制）
```

---

## 整理内容详情

### 1. 创建的新目录

- **`docs/`**: 存放所有项目文档和说明文件
- **`notebooks/`**: 存放所有 Jupyter Notebook 文件
- **`scripts/workflow/`**: 存放工作流相关的 Shell 脚本
- **`scripts/utils/`**: 存放工具类 Python 脚本

### 2. 移动的文件

#### 文档文件 → `docs/`

- `PROJECT_STRUCTURE.txt` - 项目结构说明
- `PWD_Knowledge_Graph_Analysis.html` - 分析报告 HTML 版本

#### Notebook 文件 → `notebooks/`

- `PWD_Knowledge_Graph_Analysis.ipynb` - 主分析笔记本
- `PWD_KG_Notebook.ipynb` - 知识图谱笔记本

#### 工作流脚本 → `scripts/workflow/`

- `run_complete_workflow.sh` - 一键运行完整流程
- `check_progress.sh` - 运行进度检查
- `clean_project.sh` - 输出与缓存清理
- `organize_project.sh` - 项目文件整理

#### 工具脚本 → `scripts/utils/`

- `export_for_review.py` - 导出审查文件
- `export_triples.py` - 导出三元组
- `export_neo4j_to_csv.py` - 从数据库导出 CSV
- `export_notebook_to_pdf.py` - 导出笔记本为 PDF
- `auto_disambiguate.py` - 自动消歧
- `cache_manager.py` - 缓存管理
- `config_loader.py` - 配置加载
- `logger_config.py` - 日志配置
- `visualize_neo4j_graph.py` - Neo4j 图可视化

#### 废弃脚本 → `archive/scripts/`

- `apoc_error_fix.py` - APOC 错误修复
- `apoc_fix_notebook.py` - APOC 修复笔记本
- `comprehensive_fix.py` - 综合修复
- `create_apoc_fix_guide.py` - 创建 APOC 修复指南
- `fix_apoc_query.py` - 修复 APOC 查询
- `fix_path_processing.py` - 修复路径处理
- `fix_remaining_relations.py` - 修复剩余关系
- `fix_semantic_triples.py` - 修复语义三元组
- `refine_node_labels.py` - 优化节点标签

### 3. 保留在根目录的核心文件

以下核心脚本保持在项目根目录，便于直接调用：

- `main.py` - 主入口程序
- `enhanced_pipeline.py` - 增强管道
- `concept_extractor.py` - 概念抽取
- `concept_deduplicator.py` - 概念去重
- `data_cleaner.py` - 数据清洗
- `neo4j_generator.py` - Neo4j 生成器
- `neo4j_manager.py` - Neo4j 管理器
- `pdf_extractor.py` - PDF 提取器
- `ocr_processor.py` - OCR 处理器
- `entity_linker.py` - 实体链接器
- `parallel_processor.py` - 并行处理器
- `bio_semantic_review.py` - 语义审查
- `import_to_neo4j_final.py` - 最终导入脚本

---

## 使用说明

### 运行主程序

```bash
# 直接运行（路径不变）
python main.py

# 使用工作流脚本（新路径）
./scripts/workflow/run_complete_workflow.sh
```

### 查看文档

```bash
# 项目结构说明
cat docs/PROJECT_STRUCTURE.txt

# 项目整理说明
cat docs/PROJECT_ORGANIZATION.md
```

### 运行 Jupyter Notebook

```bash
# 启动 Jupyter
./venv/bin/jupyter notebook

# 在浏览器中打开
# notebooks/PWD_Knowledge_Graph_Analysis.ipynb
```

### 使用工具脚本

```bash
# 导出 Neo4j 数据
python scripts/utils/export_neo4j_to_csv.py

# 可视化图谱
python scripts/utils/visualize_neo4j_graph.py

# 清理项目
./scripts/workflow/clean_project.sh
```

---

## 更新的文件引用

### README.md 中的路径更新

已更新以下路径引用：

1. Jupyter Notebook 路径：`PWD_Knowledge_Graph_Analysis.ipynb` → `notebooks/PWD_Knowledge_Graph_Analysis.ipynb`
2. 工作流脚本路径：`run_complete_workflow.sh` → `scripts/workflow/run_complete_workflow.sh`
3. 清理脚本路径：`clean_project.sh` → `scripts/workflow/clean_project.sh`
4. 项目结构文档：`PROJECT_STRUCTURE.txt` → `docs/PROJECT_STRUCTURE.txt`

---

## 整理优势

### 1. 更清晰的项目结构

- 文档、笔记本、脚本分类存放
- 核心代码保持在根目录，便于导入
- 辅助工具统一管理

### 2. 更好的可维护性

- 废弃代码归档，不影响主流程
- 工作流脚本集中管理
- 工具脚本易于查找和复用

### 3. 更专业的项目组织

- 符合 Python 项目最佳实践
- 便于版本控制和协作
- 易于新成员理解项目结构

---

## 注意事项

1. **导入路径无需更改**：核心 Python 模块仍在根目录，相互导入路径不变
2. **脚本调用需更新**：调用工作流脚本时需使用新路径 `scripts/workflow/`
3. **工具脚本调用**：使用工具脚本时需使用新路径 `scripts/utils/`
4. **文档查看**：文档文件现在位于 `docs/` 目录
5. **Notebook 访问**：Jupyter Notebook 现在位于 `notebooks/` 目录

---

## 后续建议

1. 考虑创建 `tests/` 目录存放测试文件
2. 可以创建 `data/` 目录存放示例数据
3. 考虑添加 `setup.py` 或 `pyproject.toml` 使项目可安装
4. 可以添加 `Makefile` 简化常用命令

---

## 版本信息

- 整理版本：v1.0
- 整理日期：2025-11-25
- 整理人员：Cascade AI Assistant
