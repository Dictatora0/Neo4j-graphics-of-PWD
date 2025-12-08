# GraphRAG 问答 & 领域配置外置化

## 概述

本文档介绍两个重要的系统改进：

1. **GraphRAG 智能问答** - 在 Web 界面中集成 Local Search 和社区摘要功能
2. **领域配置外置化** - 将实体别名映射和类型层级从代码中提取到可编辑的配置文件

---

## 1. GraphRAG 智能问答功能

### 1.1 功能概述

将 `graph_rag.py` 中实现的 Local Search 和 Community Summary 功能通过 Web API 和前端界面暴露给用户。

**核心能力**：

- 自然语言问答
- 基于向量检索的精确召回
- 子图可视化高亮
- LLM 生成回答

### 1.2 架构

```
用户提问 → FastAPI /api/rag/local-search
         → LocalSearchEngine.retrieve()
         → 向量检索 + 子图扩展
         → LLM 生成答案
         → 前端展示 + 节点高亮
```

### 1.3 后端 API

#### 文件位置

- `web/backend/app/routers/rag.py`

#### 接口列表

**1. Local Search 问答**

```http
POST /api/rag/local-search
Content-Type: application/json

{
  "query": "松材线虫病的主要传播媒介是什么？",
  "top_k": 5,
  "expand_depth": 1
}
```

**响应**：

```json
{
  "answer": "松材线虫病的主要传播媒介是松褐天牛...",
  "relevant_nodes": [
    {
      "id": "node_123",
      "name": "松褐天牛",
      "category": "Vector",
      "similarity": 0.92
    }
  ],
  "relevant_edges": [...],
  "confidence": 0.85,
  "sources": ["松褐天牛", "松材线虫", "传播途径"]
}
```

**2. 社区摘要**

```http
POST /api/rag/community-summary
Content-Type: application/json

{
  "algorithm": "louvain",
  "resolution": 1.0
}
```

**响应**：

```json
[
  {
    "id": 0,
    "title": "病原体与传播媒介",
    "summary": "这个社区包含松材线虫、松褐天牛等核心概念...",
    "size": 25,
    "core_concepts": ["松材线虫", "松褐天牛", "传播", "感染", "寄主"]
  }
]
```

**3. RAG 状态检查**

```http
GET /api/rag/stats
```

### 1.4 前端界面

#### 组件位置

- `web/frontend/src/components/RAGPanel.tsx`

#### 功能特性

1. **问答输入框**

   - 支持多行输入
   - Enter 键快速提交
   - 示例问题快速填充

2. **AI 回答展示**

   - 高亮显示答案
   - 置信度百分比
   - 渐变背景区分

3. **相关概念列表**

   - 概念名称 + 类别标签
   - 相似度进度条
   - 按相似度排序

4. **信息来源**

   - 标签形式展示
   - 点击可跳转（待实现）

5. **节点高亮**
   - 自动高亮图谱中的相关节点
   - 视觉反馈增强

#### 使用方式

1. 点击顶部导航栏的"知识问答"按钮
2. 输入自然语言问题
3. 查看 AI 生成的答案和相关概念
4. 相关节点会在图谱中高亮显示

### 1.5 配置要求

#### 后端依赖

```python
# graph_rag.py 中的类
from graph_rag import LocalSearchEngine, CommunityDetector, CommunitySummarizer
```

#### 向量索引构建

首次使用前需要构建节点向量索引：

```python
from graph_rag import LocalSearchEngine
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
search_engine = LocalSearchEngine(driver, embedding_model="BAAI/bge-m3")

# 构建索引（只需运行一次）
search_engine.build_node_index()
```

或在知识图谱构建完成后自动构建（已集成到 `start.sh` 中）。

### 1.6 示例问题

- "松材线虫病的主要传播媒介是什么？"
- "如何防治松材线虫病？"
- "松材线虫病有哪些症状？"
- "哪些松树品种容易感染松材线虫病？"
- "松褐天牛和松材线虫的关系是什么？"

---

## 2. 领域配置外置化

### 2.1 功能概述

将实体别名映射（`canonical_names`）和类型层级（`type_hierarchy`）从 Python 代码中提取到独立的 JSON 配置文件，方便领域专家编辑和维护。

**优势**：

- ✅ 无需修改代码即可更新领域知识
- ✅ 支持版本控制和协作编辑
- ✅ 配置验证工具确保数据正确性
- ✅ 易于扩展到新的领域

### 2.2 配置文件

#### 文件位置

```
config/
├── domain_dict.json       # 实体别名映射
└── type_hierarchy.json    # 类型层级配置
```

#### domain_dict.json 格式

```json
{
  "Disease": [
    "松材线虫病", // 第一个是标准名称
    "PWD", // 后续是别名
    "Pine Wilt Disease",
    "pine wilt"
  ],
  "Pathogen": [
    "松材线虫",
    "Bursaphelenchus xylophilus",
    "B. xylophilus",
    "pine wood nematode"
  ],
  "Host": ["马尾松", "Pinus massoniana", "黑松", "Pinus thunbergii"]
}
```

**规则**：

- 每个类别的第一个元素是**标准名称**
- 所有别名（包括标准名称）都会映射到标准名称
- 支持中英文混合
- 大小写不敏感（自动标准化）

#### type_hierarchy.json 格式

```json
{
  "comment": "类型层级配置 - 用于Neo4j多级Label",
  "hierarchy": {
    "Organism": {
      "description": "生物",
      "children": {
        "Pathogen": {
          "description": "病原体",
          "children": {
            "Nematode": {
              "description": "线虫"
            }
          }
        },
        "Host": {
          "description": "寄主",
          "children": {
            "Pine": {
              "description": "松树"
            }
          }
        }
      }
    }
  }
}
```

**规则**：

- 树形结构，支持多级嵌套
- 每个类型包含 `description` 和可选的 `children`
- 用于生成 Neo4j 节点的多级 Label

### 2.3 配置验证工具

#### 工具位置

- `tools/validate_domain_config.py`

#### 使用方法

```bash
python tools/validate_domain_config.py
```

#### 检查项

1. **文件存在性** - 检查配置文件是否存在
2. **JSON 格式** - 验证 JSON 语法正确性
3. **实体别名**
   - 检查空别名
   - 查找重复别名
   - 统计各类别数量
4. **类型层级**
   - 计算深度和节点数
   - 检测循环依赖
5. **交叉验证** - 检查两个文件的一致性

#### 输出示例

```
✅ 没有发现错误

⚠️  发现 3 个警告:
   • 发现 1 组重复别名
   •   - 'pine wilt disease' 出现在: Disease, Disease
   • 以下类型在 type_hierarchy 中但不在 domain_dict 中: Chemical, Fungus, ...

📊 统计信息:
   - categories: 8
   - total_aliases: 139
   - duplicates: 1
   - root_types: 8
   - all_types: 31
   - max_depth: 2
```

### 2.4 配置加载工具

#### 工具位置

- `tools/domain_config_loader.py`

#### 使用示例

```python
from tools.domain_config_loader import DomainConfigLoader

# 初始化加载器
loader = DomainConfigLoader()

# 1. 加载实体别名
domain_dict = loader.load_domain_dict()
# {'Disease': ['松材线虫病', 'PWD', ...], ...}

# 2. 获取别名映射
canonical_mapping = loader.get_canonical_mapping()
print(canonical_mapping['PWD'])  # '松材线虫病'
print(canonical_mapping['B. xylophilus'])  # '松材线虫'

# 3. 获取类型层级
type_hierarchy = loader.get_type_hierarchy_map()
print(type_hierarchy['Nematode'])  # ['Organism', 'Pathogen', 'Nematode']

# 4. 查询实体类别
category = loader.get_category_for_entity('松材线虫')
print(category)  # 'Pathogen'

# 5. 导出给 CanonicalResolver 使用
config = loader.export_for_canonical_resolver()
# {
#   'canonical_names': {alias: canonical},
#   'category_mapping': {canonical: category}
# }
```

### 2.5 集成到现有代码

#### 更新 CanonicalResolver

```python
from tools.domain_config_loader import DomainConfigLoader

class CanonicalResolver:
    def __init__(self, use_external_config=True):
        if use_external_config:
            loader = DomainConfigLoader()
            config = loader.export_for_canonical_resolver()
            self.canonical_names = config['canonical_names']
            self.category_mapping = config['category_mapping']
        else:
            # 使用硬编码配置（向后兼容）
            self.canonical_names = {...}
```

#### 更新 import_to_neo4j_final.py

```python
from tools.domain_config_loader import DomainConfigLoader

# 加载类型层级
loader = DomainConfigLoader()
TYPE_HIERARCHY = loader.export_for_import_script()

# 使用
labels = TYPE_HIERARCHY.get(node_type, [node_type])
```

### 2.6 维护工作流

#### 添加新领域知识

1. **添加实体别名**

   ```bash
   # 编辑 config/domain_dict.json
   vim config/domain_dict.json

   # 添加新类别或别名
   {
     "Medicine": [
       "阿维菌素",
       "Avermectin",
       "甲维盐"
     ]
   }
   ```

2. **添加类型层级**

   ```bash
   # 编辑 config/type_hierarchy.json
   vim config/type_hierarchy.json

   # 在合适的位置添加
   {
     "Chemical": {
       "children": {
         "Medicine": {
           "description": "药物"
         }
       }
     }
   }
   ```

3. **验证配置**

   ```bash
   python tools/validate_domain_config.py
   ```

4. **重新构建图谱**
   ```bash
   bash start.sh
   ```

#### 配置版本控制

```bash
# 提交配置更改
git add config/domain_dict.json config/type_hierarchy.json
git commit -m "Add medicine category and aliases"

# 查看配置历史
git log --oneline -- config/domain_dict.json
```

### 2.7 最佳实践

1. **命名规范**

   - 标准名称优先使用中文
   - 别名包含常见英文名、缩写
   - 保持一致的命名风格

2. **类别划分**

   - 遵循领域本体论
   - 避免类别重叠
   - 保持合理的粒度

3. **定期验证**

   - 修改后立即验证
   - 集成到 CI/CD 流程
   - 维护测试用例

4. **文档同步**
   - 重大更改更新 README
   - 维护变更日志
   - 注释复杂的层级关系

---

## 3. 使用指南

### 3.1 启动完整功能

```bash
# 1. 构建知识图谱（包含向量索引）
bash start.sh

# 2. 启动 Web 应用
cd web
./start.sh

# 3. 访问应用
open http://localhost:5173
```

### 3.2 测试 GraphRAG 问答

1. 点击"知识问答"按钮
2. 输入："松材线虫病如何传播？"
3. 查看 AI 回答和相关概念
4. 观察图谱中高亮的节点

### 3.3 编辑领域配置

```bash
# 1. 编辑配置
vim config/domain_dict.json

# 2. 验证配置
python tools/validate_domain_config.py

# 3. 测试加载
python tools/domain_config_loader.py

# 4. 重新构建图谱
bash start.sh --batch-size 3
```

---

## 4. 故障排查

### 4.1 GraphRAG 问答失败

**问题**: "Local Search 索引未就绪"

**解决**:

```python
from graph_rag import LocalSearchEngine
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "12345678"))
search_engine = LocalSearchEngine(driver, "BAAI/bge-m3")
search_engine.build_node_index()
```

### 4.2 配置验证失败

**问题**: "JSON 格式错误"

**解决**:

1. 使用 JSON 验证工具检查语法
2. 确保没有尾随逗号
3. 检查中文字符编码

### 4.3 别名映射不生效

**问题**: 实体未正确标准化

**检查**:

```python
from tools.domain_config_loader import DomainConfigLoader

loader = DomainConfigLoader()
mapping = loader.get_canonical_mapping()
print(mapping.get('your_alias'))  # 应返回标准名称
```

---

## 5. 扩展计划

### 5.1 GraphRAG 增强

- [ ] 多轮对话支持
- [ ] 历史问题记录
- [ ] 答案质量评分
- [ ] 引用文献追溯

### 5.2 配置管理增强

- [ ] Web 界面配置编辑器
- [ ] 配置热加载（无需重启）
- [ ] 多领域配置切换
- [ ] 配置模板库

---

## 6. 相关文档

- `README.md` - 系统总体介绍
- `docs/IMPROVEMENTS_2024.md` - 第一阶段改进
- `docs/IMPROVEMENTS_PHASE2.md` - 第二阶段改进
- `graph_rag.py` - GraphRAG 核心实现
- `concept_deduplicator.py` - CanonicalResolver 实现

---

最后更新：2024-12-08
