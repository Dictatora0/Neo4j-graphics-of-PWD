# 数据流程说明

## 📊 完整数据处理流程

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
           │  output/entities_clean.csv │ (清洗后，~1071条)
           │  output/relations_clean.csv│ (清洗后，~1502条)
           └──────────┬────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│  第 3 步：数据修正                                            │
│  python fix_and_import.py                                   │
│                                                             │
│  ① 修正无效实体（删除 50 个）                                │
│  ② 修正关系（删除 1101 条重复/噪声）                         │
│  ③ 保存修正结果                                              │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
           ┌──────────────────────────┐
           │  output/entities_fixed.csv │ ← 完整字段备份
           │  output/relations_fixed.csv│ ← 完整字段备份
           └──────────┬────────────────┘
                      │
                      │ (继续在 fix_and_import.py 中)
                      ↓
┌─────────────────────────────────────────────────────────────┐
│  第 4 步：转换为 Neo4j 格式                                   │
│  generate_neo4j_files(entities_fixed, relations_fixed)      │
│                                                             │
│  - 提取必要字段                                              │
│  - 转换实体 ID                                               │
│  - 生成 Neo4j 专用格式                                       │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
           ┌────────────────────────────────┐
           │  output/neo4j_import/nodes.csv     │ ← Neo4j 导入文件
           │  output/neo4j_import/relations.csv │ ← Neo4j 导入文件
           └──────────┬─────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│  第 5 步：导入到 Neo4j                                        │
│  python import_fixed_data.py                                │
│                                                             │
│  - 读取 Neo4j 格式文件                                       │
│  - 创建节点和关系                                            │
│  - 验证导入结果                                              │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
                 ┌─────────┐
                 │  Neo4j  │
                 │ 数据库   │
                 └─────────┘
```

---

## 📂 文件说明

### 原始数据文件

| 文件 | 说明 | 何时生成 |
|------|------|----------|
| `output/entities.csv` | 原始提取的实体 | `main.py` 第一次运行 |
| `output/relations.csv` | 原始提取的关系 | `main.py` 第一次运行 |

**字段**：id, name, type, source_pdf

---

### 清洗后数据文件

| 文件 | 说明 | 何时生成 |
|------|------|----------|
| `output/entities_clean.csv` | 清洗后的实体 | `main.py` 数据清洗阶段 |
| `output/relations_clean.csv` | 清洗后的关系 | `main.py` 数据清洗阶段 |

**字段**：id, name, type, source_pdf, confidence

---

### 修正后数据文件（备份）

| 文件 | 说明 | 何时生成 |
|------|------|----------|
| `output/entities_fixed.csv` | 修正后的实体（完整字段） | `fix_and_import.py` |
| `output/relations_fixed.csv` | 修正后的关系（完整字段） | `fix_and_import.py` |

**用途**：
- ✅ 保留完整信息用于备份
- ✅ 可用 Python/Pandas 分析
- ✅ 可用 Excel 查看编辑
- ✅ 记录数据修正过程

**字段**：完整保留（id, name, type, source_pdf, confidence 等）

---

### Neo4j 导入文件（优化格式）

| 文件 | 说明 | 何时生成 |
|------|------|----------|
| `output/neo4j_import/nodes.csv` | Neo4j 节点文件 | `fix_and_import.py` 中的 `generate_neo4j_files()` |
| `output/neo4j_import/relations.csv` | Neo4j 关系文件 | `fix_and_import.py` 中的 `generate_neo4j_files()` |

**用途**：
- ✅ **专门用于导入 Neo4j**
- ✅ 简化字段提升导入速度
- ✅ 标准化 ID 映射

**字段**：
- `nodes.csv`: `id, name, label`
- `relations.csv`: `start_id, relation, end_id, confidence`

---

## ❓ 常见问题

### Q1: 为什么要保存两份文件（*_fixed.csv 和 neo4j_import/*.csv）？

**A**: 因为用途不同：

1. **entities_fixed.csv / relations_fixed.csv**
   - 保留**完整信息**
   - 便于后续分析和修改
   - 可以追溯数据来源

2. **neo4j_import/nodes.csv / relations.csv**
   - **Neo4j 专用格式**
   - 只包含导入必需字段
   - 优化导入性能
   - ID 已映射完成

### Q2: import_fixed_data.py 为什么读取 neo4j_import/*.csv？

**A**: 因为这些文件已经是 Neo4j 格式：

```python
# entities_fixed.csv 格式
id,name,type,source_pdf
1,松材线虫病,Disease,paper1.pdf

# nodes.csv 格式（Neo4j 优化）
id,name,label
1,松材线虫病,Disease
```

Neo4j 导入只需要简化字段，所以使用 `nodes.csv`。

### Q3: 能否直接从 entities_fixed.csv 导入到 Neo4j？

**A**: 可以，但不推荐：

```python
# 可以这样做（不推荐）
entities_df = pd.read_csv('output/entities_fixed.csv')
# 需要手动转换字段名和格式

# 推荐做法（已优化）
nodes_df = pd.read_csv('output/neo4j_import/nodes.csv')
# 字段已经是 Neo4j 格式
```

### Q4: 如果我只想修改数据，不想导入 Neo4j，怎么办？

**A**: 可以分步执行：

```bash
# 只修正数据
python fix_and_import.py
# 选择 'n' 跳过导入

# 修正后的数据在：
# - output/entities_fixed.csv
# - output/relations_fixed.csv
```

### Q5: 数据流程能否简化？

**A**: 当前设计的优点：

| 优点 | 说明 |
|------|------|
| 🔒 **数据安全** | 每步都有备份 |
| 🔍 **可追溯** | 可以查看每一步的结果 |
| ⚡ **性能优化** | Neo4j 文件格式专门优化 |
| 🔄 **灵活性** | 可以在任何阶段重新开始 |

---

## 🎯 推荐使用方式

### 方式 1：完整流程（推荐）

```bash
# 一键执行从修正到导入
python fix_and_import.py
# 选择 'y' 自动导入到 Neo4j
```

**优点**：自动化，一步到位

### 方式 2：分步执行

```bash
# 步骤 1：修正数据
python fix_and_import.py
# 选择 'n' 跳过导入

# （可选）检查修正结果
cat output/entities_fixed.csv
cat output/relations_fixed.csv

# 步骤 2：导入到 Neo4j
python import_fixed_data.py
```

**优点**：可以在导入前检查数据

### 方式 3：只清理数据库

```bash
# 如果数据已导入，只想清理
python clean_neo4j_database.py
```

---

## 📋 文件用途总结

| 文件 | 格式 | 用途 | 推荐操作 |
|------|------|------|----------|
| `entities_clean.csv` | 完整 | 输入数据 | 保留备份 |
| `relations_clean.csv` | 完整 | 输入数据 | 保留备份 |
| **`entities_fixed.csv`** | **完整** | **数据分析** | **保留用于分析** |
| **`relations_fixed.csv`** | **完整** | **数据分析** | **保留用于分析** |
| `neo4j_import/nodes.csv` | Neo4j | Neo4j 导入 | 导入后可删除 |
| `neo4j_import/relations.csv` | Neo4j | Neo4j 导入 | 导入后可删除 |

---

## 💡 最佳实践

1. **首次运行**：
   ```bash
   python main.py                # 生成 *_clean.csv
   python fix_and_import.py      # 生成 *_fixed.csv 和 neo4j_import/*.csv
   python import_fixed_data.py   # 导入到 Neo4j
   ```

2. **数据分析**：
   - 使用 `entities_fixed.csv` 和 `relations_fixed.csv`
   - 包含完整字段，便于分析

3. **重新导入**：
   - 如果需要重新导入，直接运行：
     ```bash
     python import_fixed_data.py
     ```
   - 因为 `neo4j_import/*.csv` 已经存在

4. **数据更新**：
   - 修改 `entities_clean.csv` 或 `relations_clean.csv`
   - 重新运行 `fix_and_import.py`
   - 会自动更新所有下游文件

---

**总结**：`import_fixed_data.py` 读取的是修正后数据的 **Neo4j 格式版本**，而不是"另外的数据"。这是设计的数据流程，确保数据格式适配 Neo4j 导入需求。

