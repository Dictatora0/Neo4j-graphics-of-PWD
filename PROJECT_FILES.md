# 项目文件说明

## 核心文件（必需）

### 主程序

- `main_enhanced.py` - **增强型主程序**（推荐使用，包含 LLM 概念提取）
- `main.py` - 传统主程序（用于对比测试）

### 管道模块

- `enhanced_pipeline.py` - 增强型管道（LLM + 去重 + 邻近性分析）
- `concept_extractor.py` - LLM 概念和关系提取
- `concept_deduplicator.py` - 语义去重和过滤

### 传统模块

- `entity_recognizer.py` - 传统实体识别（TF-IDF, YAKE, KeyBERT, spaCy）
- `relation_extractor.py` - 传统关系抽取（正则 + 共现）
- `entity_linker.py` - 实体链接和消歧

### 数据处理

- `pdf_extractor.py` - PDF 文本提取
- `ocr_processor.py` - OCR 处理（图片文字识别）
- `data_cleaner.py` - 数据清洗和规范化

### Neo4j 集成

- `neo4j_generator.py` - 生成 Neo4j 导入文件
- `neo4j_manager.py` - **Neo4j 数据库管理**（备份、清空、回滚）

### 工具模块

- `config_loader.py` - 配置文件加载
- `logger_config.py` - 日志配置
- `cache_manager.py` - 缓存管理
- `parallel_processor.py` - 并行处理

## 脚本文件

### 主要脚本

- `run_complete_workflow.sh` - **一键运行脚本**（推荐）
- `check_progress.sh` - 查看处理进度
- `view_results.sh` - 查看结果摘要
- `clean_project.sh` - **项目清理工具**

## 配置文件

- `config/config.yaml` - **主配置文件**
- `requirements.txt` - Python 依赖

## 文档文件

- `README.md` - 项目说明
- `PROJECT_FILES.md` - 本文件

## 目录结构

```
PWD/
├── config/              # 配置文件
│   └── config.yaml
├── 文献/                # PDF 文献输入目录
├── output/              # 输出目录
│   ├── *.csv           # 提取的概念和关系
│   ├── neo4j_import*/  # Neo4j 导入文件
│   ├── neo4j_backups/  # 数据库备份
│   ├── cache/          # 缓存文件
│   └── *.log           # 日志文件
├── venv/               # Python 虚拟环境
└── __pycache__/        # Python 缓存
```

## 使用建议

### 日常使用

```bash
# 运行增强型管道
bash run_complete_workflow.sh start

# 查看进度
bash check_progress.sh

# 查看结果
bash view_results.sh
```

### 数据库管理

```bash
# 备份数据库
python neo4j_manager.py backup

# 清空数据库
python neo4j_manager.py clear

# 恢复备份
python neo4j_manager.py restore

# 列出所有备份
python neo4j_manager.py list
```

### 项目清理

```bash
# 交互式清理
bash clean_project.sh

# 清理所有输出
bash clean_project.sh 5

# 查看文件大小
bash clean_project.sh 6
```

## 已删除的文件

以下文件已被删除（功能已整合或不再需要）：

- `ENHANCED_PIPELINE_GUIDE.md` - 内容已整合到 README
- `INDEX_ENHANCED.md` - 重复文档
- `INTEGRATION_COMPLETE.md` - 重复文档
- `MODULES_README.md` - 重复文档
- `OPTIMIZATION_SUMMARY.md` - 重复文档
- `QUICK_START_ENHANCED.md` - 重复文档
- `setup_enhanced.sh` - 功能已整合到 run_complete_workflow.sh
- `import_fixed_data.py` - 不再使用
- `incremental_updater.py` - 功能未完善
- `workflow_manager.py` - 功能已整合

## 文件依赖关系

### 增强型管道

```
main_enhanced.py
  ├── enhanced_pipeline.py
  │   ├── concept_extractor.py (LLM)
  │   ├── concept_deduplicator.py (去重)
  │   └── pdf_extractor.py
  ├── data_cleaner.py
  ├── neo4j_generator.py
  └── neo4j_manager.py (新增)
```

### 传统管道

```
main.py
  ├── pdf_extractor.py
  ├── entity_recognizer.py
  ├── relation_extractor.py
  ├── entity_linker.py
  ├── data_cleaner.py
  └── neo4j_generator.py
```

## 核心改进

### 新增功能

1. **Neo4j 数据库管理** (`neo4j_manager.py`)

   - 自动备份当前数据
   - 清空数据库
   - 失败时自动回滚

2. **项目清理工具** (`clean_project.sh`)

   - 清理输出文件
   - 清理缓存
   - 保留备份

3. **自动回滚机制**
   - 运行前自动备份
   - 失败或中断时自动回滚
   - 保证数据安全

### 工作流程

```
1. 启动 → 备份 Neo4j 数据库
2. 清空数据库
3. 运行管道提取数据
4. 生成 Neo4j 导入文件
5. 成功 → 保留新数据
   失败 → 自动回滚到备份
```
