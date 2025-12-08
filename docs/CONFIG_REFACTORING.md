# 配置系统重构说明

## 改进概述

本次重构实现了三个重要的工程化改进：

### 1. 统一配置源 & 环境区分 ✅

**问题**：

- 批处理管线使用 `config/config.yaml` + 自定义 `Config` 类
- Web 后端使用 Pydantic Settings + `.env`
- 配置不统一，容易出错

**解决方案**：

- ✅ 创建多环境配置：`config.base.yaml`, `config.dev.yaml`, `config.prod.yaml`
- ✅ 使用 Pydantic Settings 统一验证
- ✅ 支持环境变量覆盖
- ✅ 向后兼容旧的 `Config` 类

**文件结构**：

```
config/
├── config.base.yaml      # 基础配置（所有环境共享）
├── config.dev.yaml       # 开发环境配置
├── config.prod.yaml      # 生产环境配置
└── config.yaml           # 保留（向后兼容）

pwdkg/
├── __init__.py
└── config.py             # 统一配置管理模块
```

**使用方式**：

```python
# 新方式（推荐）
from pwdkg import load_config

config = load_config(env="development")
print(config.pdf.input_directory)
print(config.llm.model)

# 旧方式（向后兼容）
from pwdkg.config import Config

config = Config()  # 自动加载开发环境配置
print(config.input_directory)
```

**环境切换**：

```bash
# 方式 1：环境变量
export PWD_ENV=production
python start.py

# 方式 2：代码指定
config = load_config(env="production")
```

**配置优先级**：

```
1. 环境变量 (PWD_*)
2. .env 文件
3. config.{env}.yaml (环境特定)
4. config.base.yaml (基础配置)
```

---

### 2. 入口脚本收敛 & 标记推荐路径 ✅

**问题**：

- 入口脚本太多：`main.py`, `run_pipeline.py`, `start.py`, `enhanced_pipeline.py`, `enhanced_pipeline_safe.py`
- README 推荐 `start.sh`，但代码层面不明确

**解决方案**：

- ✅ 在 README 中明确标记推荐路径
- ✅ 创建统一 CLI 入口框架（`pwdkg/cli.py`）
- ✅ 旧脚本标记为"示例/旧版"

**推荐使用路径**：

```bash
# ✅ 推荐：统一入口脚本
bash start.sh

# ✅ 推荐：直接运行 safe 管线
python enhanced_pipeline_safe.py

# 🔄 未来：统一 CLI（开发中）
python -m pwdkg run --env dev --batch-size 5

# ❌ 不推荐：旧版脚本（保留用于参考）
# python run_pipeline.py
# python enhanced_pipeline.py
```

**脚本分类**：

| 脚本                        | 状态    | 用途                     |
| --------------------------- | ------- | ------------------------ |
| `start.sh`                  | ✅ 推荐 | 统一启动脚本，带依赖检查 |
| `enhanced_pipeline_safe.py` | ✅ 推荐 | 主流程（稳定版）         |
| `start.py`                  | ✅ 可用 | 简化启动脚本             |
| `run_pipeline.py`           | 🔄 旧版 | 示例参考                 |
| `enhanced_pipeline.py`      | 🔄 旧版 | 示例参考                 |
| `main.py` (web)             | ✅ 推荐 | Web 后端入口             |

---

### 3. 脚本 → 包结构（规划中） 🔄

**问题**：

- 大量根目录脚本：`pdf_extractor.py`, `concept_extractor.py`, etc.
- 不便于 import 和测试

**解决方案**：

**目标结构**：

```
pwdkg/                    # 核心包
├── __init__.py
├── config.py            # ✅ 已完成
├── cli.py               # 🔄 CLI 入口（框架）
├── extractors/          # PDF & 概念提取
│   ├── pdf.py
│   └── concept.py
├── processing/          # 数据处理
│   ├── deduplicator.py
│   └── filter.py
├── graph/               # 图谱构建
│   ├── builder.py
│   └── importer.py
└── utils/               # 工具函数
    ├── logger.py
    └── checkpoint.py

# 根目录脚本变为薄的 CLI 层
pdf_extractor.py         # from pwdkg.extractors import PDFExtractor
concept_extractor.py     # from pwdkg.extractors import ConceptExtractor
...
```

**迁移计划**：

**Phase 1** (本次完成)：

- ✅ 创建 `pwdkg/` 包结构
- ✅ 实现统一配置管理 `pwdkg/config.py`
- ✅ CLI 框架 `pwdkg/cli.py`

**Phase 2** (下一步)：

- 🔄 迁移核心类到 `pwdkg/`
- 🔄 更新现有脚本为薄 CLI 层
- 🔄 添加单元测试

**Phase 3** (未来)：

- 📋 完整的包文档
- 📋 PyPI 发布
- 📋 pip install pwdkg

---

## 配置示例

### config.base.yaml（基础配置）

```yaml
app:
  name: "PWD Knowledge Graph"
  version: "3.0"

pdf:
  chunk_size: 2000
  chunk_overlap: 200
  # ...

llm:
  model: llama3.2:3b
  fallback_models:
    - llama3.2:3b
    - qwen2.5-coder:7b
```

### config.dev.yaml（开发环境）

```yaml
environment: development

pdf:
  input_directory: ./文献
  parallel_workers: 2
  enable_image_captions: false # 开发时禁用

logging:
  log_level: DEBUG # 开发环境详细日志

llm:
  max_chunks: 10 # 开发时只处理少量
```

### config.prod.yaml（生产环境）

```yaml
environment: production

pdf:
  input_directory: /data/documents
  parallel_workers: 4
  enable_image_captions: true # 生产环境完整功能

neo4j:
  uri: ${NEO4J_URI:neo4j://neo4j:7687}
  password: ${NEO4J_PASSWORD} # 从环境变量读取

logging:
  log_level: INFO
  log_to_console: false
```

---

## 使用指南

### 1. 开发环境

```bash
# 设置环境
export PWD_ENV=development

# 或在代码中
from pwdkg import load_config
config = load_config(env="development")

# 运行管线
bash start.sh
```

### 2. 生产环境

```bash
# 设置环境变量
export PWD_ENV=production
export NEO4J_PASSWORD=secure_password
export OLLAMA_HOST=http://ollama-service:11434

# 运行
python enhanced_pipeline_safe.py
```

### 3. 配置验证

```python
from pwdkg.config import load_config, validate_config

config = load_config()
errors = validate_config(config)

if errors:
    for error in errors:
        print(f"❌ {error}")
else:
    print("✅ 配置有效")
```

---

## 迁移指南

### 从旧配置迁移

**步骤 1**: 确定当前使用的配置

```bash
# 如果使用 config/config.yaml
cp config/config.yaml config/config.dev.yaml.backup
```

**步骤 2**: 适配新的多环境结构

- 公共配置 → `config.base.yaml`
- 开发特定 → `config.dev.yaml`
- 生产特定 → `config.prod.yaml`

**步骤 3**: 更新代码

```python
# 旧方式
from config_loader import load_config
config = load_config("config/config.yaml")

# 新方式
from pwdkg import load_config
config = load_config(env="development")

# 或向后兼容
from pwdkg.config import Config
config = Config()  # 自动加载
```

**步骤 4**: 测试验证

```bash
python pwdkg/config.py  # 运行配置测试
```

---

## 优势总结

### ✅ 配置统一

- 批处理和 Web 后端使用相同的配置结构
- Pydantic 自动验证，避免类型错误
- 环境变量支持，适合容器化部署

### ✅ 环境隔离

- 开发/测试/生产配置分离
- 敏感信息（密码）从环境变量读取
- 便于 CI/CD 集成

### ✅ 向后兼容

- 保留旧的 `Config` 类接口
- 现有脚本无需大幅修改
- 渐进式迁移

### ✅ 可维护性

- 配置集中管理
- 类型检查和验证
- 清晰的优先级规则

---

## 相关文件

- `pwdkg/__init__.py` - 包入口
- `pwdkg/config.py` - 统一配置管理（305 行）
- `config/config.base.yaml` - 基础配置
- `config/config.dev.yaml` - 开发环境配置
- `config/config.prod.yaml` - 生产环境配置

---

## 测试

```bash
# 测试配置加载
python pwdkg/config.py

# 应该看到
📋 开发环境配置:
   环境: Environment.DEVELOPMENT
   PDF 输入: ./文献
   并发数: 2
   LLM 模型: llama3.2:3b
   日志级别: DEBUG

✅ 配置验证通过
✅ 配置管理模块测试完成
```

---

最后更新：2024-12-08
