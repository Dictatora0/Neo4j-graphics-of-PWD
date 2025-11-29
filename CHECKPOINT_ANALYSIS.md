# 结果保存机制分析与改进方案

## 当前机制分析

### ✅ 已有保护措施

1. **PDF 提取缓存**（`pdf_extractor.py`）

   - 内存级缓存：`SimpleCache` 类
   - 避免重复提取同一 PDF
   - ⚠️ **限制**：仅在内存中，进程退出后丢失

2. **最终结果保存**（`enhanced_pipeline.py` 第 288-300 行）
   ```python
   def _save_results(self, concepts_df, relationships_df):
       concepts_df.to_csv(f"{self.output_dir}/concepts.csv", ...)
       relationships_df.to_csv(f"{self.output_dir}/relationships.csv", ...)
   ```
   - 时机：所有处理完成后保存一次
   - 格式：CSV 文件，UTF-8-sig 编码

### ❌ 存在的风险

#### 风险 1: 长时间运行无中间保存

**问题**：

- LLM 处理 100 个文本块约需 30-40 分钟
- 如果在第 95 个块时程序崩溃/断电/Ctrl+C，前 94 个块的结果**全部丢失**

**影响**：

```
处理时间线：
[PDF提取: 2分钟] ✅ 有缓存
    ↓
[文本分块: 10秒] ✅ 很快
    ↓
[LLM抽取: 30分钟] ❌ 无中间保存 ← 最大风险点
    ↓
[去重: 30秒] ✅ 很快
    ↓
[保存结果] ✅ 最终保存
```

#### 风险 2: 无异常恢复机制

**问题**：

- 没有 checkpoint 机制
- 无法从上次中断处继续
- 必须从头重新运行

#### 风险 3: Ollama 连接中断

**问题**：

- `concept_extractor.py` 调用 Ollama API
- 如果 Ollama 服务重启或网络抖动
- 当前无重试机制（已有 3 次重试，但整体无 checkpoint）

---

## 改进方案

### 方案 A：增量保存（推荐）

**实现逻辑**：
每处理 N 个文本块（如 10 个），自动保存中间结果

```python
# 在 concept_extractor.py 的 extract_from_chunks 中添加
CHECKPOINT_INTERVAL = 10  # 每 10 个块保存一次

for i, chunk in enumerate(chunks):
    # ... 处理逻辑 ...

    # 增量保存
    if (i + 1) % CHECKPOINT_INTERVAL == 0:
        checkpoint_path = f"output/checkpoint_concepts_{i+1}.csv"
        pd.DataFrame(all_concepts).to_csv(checkpoint_path, ...)
        logger.info(f"✓ Checkpoint saved at chunk {i+1}")
```

**优点**：

- 最多损失 10 个块的结果（约 3-5 分钟）
- 实现简单，不改变主流程
- 可以手动合并 checkpoint 文件恢复

**缺点**：

- 会生成多个临时文件
- 需要手动清理

### 方案 B：断点续传（最佳）

**实现逻辑**：
记录已处理的块 ID，下次运行时跳过

```python
# 保存进度文件
progress_file = "output/.progress.json"
{
    "processed_chunks": ["chunk_001", "chunk_002", ...],
    "timestamp": "2024-11-29 19:30:00"
}

# 启动时检查
if os.path.exists(progress_file):
    processed = load_progress()
    chunks = [c for c in chunks if c['chunk_id'] not in processed]
    logger.info(f"Resume from checkpoint: {len(processed)} chunks already processed")
```

**优点**：

- 完全无损恢复
- 自动续传，用户无需手动操作
- 节省时间

**缺点**：

- 实现稍复杂
- 需要额外的进度管理逻辑

### 方案 C：异常捕获 + 自动保存

**实现逻辑**：
在主循环外层捕获所有异常，强制保存已处理数据

```python
try:
    for chunk in chunks:
        # ... 处理 ...
except KeyboardInterrupt:
    logger.warning("User interrupted! Saving partial results...")
    self._save_results(concepts_df, relationships_df)
    raise
except Exception as e:
    logger.error(f"Error occurred: {e}. Saving partial results...")
    self._save_results(concepts_df, relationships_df)
    raise
```

**优点**：

- 即使崩溃也能保存部分结果
- 实现简单

**缺点**：

- 只在异常时保存，正常 Ctrl+C 可能来不及
- 部分结果可能不完整

---

## 推荐实施方案

### 立即实施（优先级 P0）

#### 1. 异常捕获保护（5 分钟实现）

在 `enhanced_pipeline.py` 的 `run` 方法中添加：

```python
def run(self, pdf_dir: str):
    try:
        # ... 原有处理流程 ...
        return concepts_df, relationships_df

    except KeyboardInterrupt:
        logger.warning("\n⚠️  用户中断！正在保存已处理的数据...")
        if 'concepts_df' in locals() and not concepts_df.empty:
            self._save_results(concepts_df, relationships_df)
            logger.info("✓ 部分结果已保存到 output/")
        raise

    except Exception as e:
        logger.error(f"\n❌ 发生错误: {e}")
        logger.warning("正在尝试保存已处理的数据...")
        if 'concepts_df' in locals() and not concepts_df.empty:
            self._save_results(concepts_df, relationships_df)
        raise
```

#### 2. LLM 调用时增量保存（10 分钟实现）

在 `concept_extractor.py` 的 `extract_from_chunks` 中：

```python
CHECKPOINT_INTERVAL = 10

for i, chunk in enumerate(tqdm(chunks)):
    # ... 原有抽取逻辑 ...

    # 每 N 个块保存一次
    if (i + 1) % CHECKPOINT_INTERVAL == 0:
        temp_concepts = pd.DataFrame(all_concepts)
        temp_relationships = pd.DataFrame(all_relationships)

        checkpoint_dir = "output/checkpoints"
        os.makedirs(checkpoint_dir, exist_ok=True)

        temp_concepts.to_csv(f"{checkpoint_dir}/concepts_chunk{i+1}.csv",
                            index=False, encoding='utf-8-sig')
        temp_relationships.to_csv(f"{checkpoint_dir}/rels_chunk{i+1}.csv",
                                  index=False, encoding='utf-8-sig')

        logger.info(f"✓ Checkpoint: {i+1}/{len(chunks)} chunks processed")
```

### 后续优化（优先级 P1）

#### 3. 持久化进度跟踪（30 分钟实现）

创建 `checkpoint_manager.py`：

```python
import json
import os
from datetime import datetime

class CheckpointManager:
    def __init__(self, checkpoint_file="output/.progress.json"):
        self.checkpoint_file = checkpoint_file
        self.progress = self.load()

    def load(self):
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {"processed_chunks": [], "concepts": [], "relationships": []}

    def save(self, chunk_id, concepts, relationships):
        self.progress["processed_chunks"].append(chunk_id)
        self.progress["concepts"].extend(concepts)
        self.progress["relationships"].extend(relationships)
        self.progress["last_update"] = datetime.now().isoformat()

        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.progress, f, ensure_ascii=False, indent=2)

    def is_processed(self, chunk_id):
        return chunk_id in self.progress["processed_chunks"]

    def clear(self):
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
```

---

## 使用建议

### 当前运行（临时方案）

如果现在就要跑，建议：

1. **分批运行**
   ```python
   # 修改 config/config.yaml
   llm:
     max_chunks: 30  # 先跑 30 个块（约 10 分钟）
   ```
2. **多次运行合并**

   - 第一次：`max_chunks: 30` → 保存结果
   - 第二次：`max_chunks: 60` → 保存结果
   - 手动合并 CSV 文件

3. **使用 screen/tmux**
   ```bash
   # 防止 SSH 断开导致进程终止
   tmux new -s pwd_kg
   python enhanced_pipeline.py
   # Ctrl+B, D 分离会话
   ```

### 改进后运行

实施上述改进方案后：

- 每 10 个块自动保存
- 支持断点续传
- 异常时自动保存
- 最多损失 10 个块（约 3 分钟）

---

## 快速修复代码

我可以立即为你生成以下文件：

1. `enhanced_pipeline_safe.py` - 带异常保护的版本
2. `checkpoint_manager.py` - 进度管理器
3. `concept_extractor_incremental.py` - 带增量保存的版本

是否需要我立即生成这些改进版本？

---

## 总结

### 当前风险等级：⚠️ 中等

- **最大风险**：LLM 抽取阶段（30 分钟无保存）
- **建议**：立即实施异常捕获 + 增量保存
- **时间成本**：15 分钟实现，立即见效

### 改进后风险等级：✅ 低

- 每 10 个块保存一次（3 分钟间隔）
- 支持断点续传
- 异常自动保护
- 最多损失 3 分钟工作量
