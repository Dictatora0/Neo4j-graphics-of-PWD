# 松材线虫病知识图谱构建系统 - 核心技术挑战与解决方案

> 项目：基于大语言模型的领域知识图谱自动化构建系统  
> 技术栈：Python, Ollama (Qwen2.5), Neo4j, PyTorch

---

## 项目概述

### 目标

从松材线虫病相关 PDF 文献中，自动构建结构化知识图谱，包括：

- 概念实体抽取
- 关系识别
- 语义去重
- 图谱可视化

### 技术难点

1. **长时间运行的稳定性** - 预计需要数小时处理时间
2. **LLM 推理性能** - 平衡速度与质量
3. **数据一致性** - 增量保存与断点续传
4. **用户体验** - 可观测性与易用性

---

## 核心挑战一：长时间运行的数据安全性

### 问题背景

**初始设计**：

```python
# 一次性处理所有数据
all_results = []
for chunk in chunks:
    result = llm_extract(chunk)  # 每块耗时 30-60s
    all_results.append(result)

save_to_file(all_results)  # 最后统一保存
```

**问题暴露**：

- 处理大量文本块需要数小时
- 中途任何错误（断电、网络、程序崩溃）导致**全部数据丢失**
- 用户无法中途停止（Ctrl+C 会丢失所有进度）

### 技术分析

**根本原因**：

1. **原子性失败** - 要么全部成功，要么全部失败
2. **无状态追踪** - 无法知道处理到哪里
3. **内存风险** - 大量数据累积在内存中

**影响评估**：

- 时间成本：每次失败需重新运行数小时
- 用户体验：无法容忍，项目不可用
- 资源浪费：计算资源和时间的双重浪费

### 解决方案：Checkpoint 机制

#### 设计原则

1. **增量保存** - 每处理 N 个块保存一次
2. **进度追踪** - JSON 记录已处理的块 ID
3. **断点续传** - 启动时恢复未完成的工作
4. **安全退出** - Ctrl+C 保存当前进度

#### 实现架构

```python
class CheckpointManager:
    """
    核心职责：
    1. 维护进度文件 (.progress.json)
    2. 增量保存 CSV (追加模式)
    3. 定期创建完整快照
    """

    def __init__(self, checkpoint_dir):
        self.progress_file = checkpoint_dir / '.progress.json'
        self.concepts_file = checkpoint_dir / 'concepts_incremental.csv'
        self.relationships_file = checkpoint_dir / 'relationships_incremental.csv'
        self.progress = self._load_progress()

    def save_chunk_results(self, chunk_id, concepts, relationships):
        """增量保存单个块的结果"""
        # 1. 追加到 CSV
        self._append_to_csv(self.concepts_file, concepts)
        self._append_to_csv(self.relationships_file, relationships)

        # 2. 更新进度
        self.progress['processed_chunks'].append(chunk_id)
        self.progress['total_concepts'] += len(concepts)
        self.progress['total_relationships'] += len(relationships)

        # 3. 持久化进度
        self._save_progress()

    def save_checkpoint(self, chunk_num, concepts_df, relationships_df):
        """定期保存完整快照"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        concepts_df.to_csv(
            f'checkpoint_concepts_{chunk_num}_{timestamp}.csv',
            index=False
        )
        # 同样保存 relationships
```

#### 主管道集成

```python
class SafePipeline:
    def __init__(self, config, checkpoint_interval=10):
        self.checkpoint_manager = CheckpointManager(config['checkpoint_dir'])
        self.checkpoint_interval = checkpoint_interval

    def run(self):
        try:
            chunks = self._split_texts()

            # 过滤已处理的块
            processed = self.checkpoint_manager.get_processed_chunks()
            remaining = [c for c in chunks if c['chunk_id'] not in processed]

            logger.info(f"Total: {len(chunks)}, Processed: {len(processed)}, "
                       f"Remaining: {len(remaining)}")

            # 增量处理
            for i, chunk in enumerate(remaining):
                try:
                    concepts, rels = self.llm_extract(chunk)

                    # 立即保存
                    self.checkpoint_manager.save_chunk_results(
                        chunk['chunk_id'], concepts, rels
                    )

                    # 定期快照
                    if (i + 1) % self.checkpoint_interval == 0:
                        self._create_snapshot(i + 1)

                except Exception as e:
                    logger.error(f"Failed chunk {chunk['chunk_id']}: {e}")
                    continue  # 继续处理下一个

        except KeyboardInterrupt:
            logger.info("User interrupted, saving progress...")
            self._finalize()
            raise
```

#### 进度文件格式

```json
{
  "processed_chunks": ["doc1_chunk_1", "doc1_chunk_2", "doc2_chunk_1"],
  "total_concepts": 132,
  "total_relationships": 93,
  "last_checkpoint": 30,
  "last_update": "2025-11-29T21:48:15"
}
```

### 效果评估

| 指标         | 改进前 | 改进后    | 提升     |
| ------------ | ------ | --------- | -------- |
| 最大损失时间 | 数小时 | < 10 分钟 | 显著提升 |
| 可中断性     | 否     | 是        | 支持     |
| 用户信心     | 低     | 高        | 显著提升 |

### 技术亮点

1. **增量式设计** - 每个块独立保存，失败影响最小化
2. **双重保险** - 增量 CSV + 定期快照
3. **状态可追踪** - 进度文件提供完整状态视图
4. **优雅降级** - LLM 单次失败不影响整体流程

---

## 核心挑战二：LLM 推理性能优化

### 问题背景

**初始配置**：

```yaml
llm:
  model: qwen2.5-coder:32b
  timeout: 120
  max_chunks: 50
```

**性能表现**（基于早期测试数据）：

```
实测单块耗时: 较长
超时率: 较高
预计总时间: 需要数小时处理
```

**不可接受**：用户无法等待一天完成。

> 注：以上数据基于项目早期使用 32B 模型的测试，详见 README.md 中的优化决策

### 问题分析

#### 1. 模型规模与速度的矛盾

| 模型              | 参数量 | 单块耗时 | 质量 | 总时间(500 块) |
| ----------------- | ------ | -------- | ---- | -------------- |
| qwen2.5-coder:32b | 32B    | 180-240s | 高   | 25-33 小时     |
| qwen2.5-coder:14b | 14B    | 80-120s  | 中高 | 11-16 小时     |
| qwen2.5-coder:7b  | 7B     | 30-50s   | 中   | 4-7 小时       |

> 注：以上数据基于项目早期性能测试，详见 IMPLEMENTATION_DETAILS.md 中的性能分析章节

#### 2. 超时策略问题

**根本矛盾**：

- 设置太短 → 正常请求被杀死
- 设置太长 → 卡死情况等待时间长

**实测数据**（基于项目早期测试）：

```
32B 模型实际需要: 较长时间
配置 timeout=120: 导致较高超时率
调整 timeout=300: 解决超时，但速度仍慢
```

> 注：以上数据记录在项目早期测试阶段，具体测试环境见 IMPLEMENTATION_DETAILS.md

#### 3. Ollama 本地推理的限制

**硬件限制**：

- CPU 推理（无 GPU）
- 内存带宽瓶颈
- 大模型量化后仍慢

### 解决方案：多维度优化

#### 方案 1: 模型降级

**决策逻辑**：

```
质量 vs 速度权衡:
- 32B: 质量最高, 速度较慢  → 总价值较低
- 7B:  质量较高, 速度很快  → 总价值更高 (更优)
```

**实施**：

```yaml
llm:
  model: qwen2.5-coder:7b # 从 32b 降级
  timeout: 600 # 增加超时上限，避免慢块失败
```

**效果**（基于 README.md 中的优化决策）：

- 单块耗时：显著降低 → 大幅提升
- 总时间：大幅缩短 → 可接受范围
- 超时率：较高 → 大幅降低

> 注：具体性能数据详见 README.md 的"LLM 性能优化"章节

#### 方案 2: 自适应超时

```python
class LLMExtractor:
    def __init__(self, base_timeout=300):
        self.base_timeout = base_timeout
        self.timeout_stats = []

    def extract(self, text):
        # 根据历史数据调整超时
        if len(self.timeout_stats) > 10:
            avg_time = np.mean(self.timeout_stats)
            timeout = min(avg_time * 2, self.base_timeout)
        else:
            timeout = self.base_timeout

        start = time.time()
        result = self._call_llm(text, timeout=timeout)
        elapsed = time.time() - start

        self.timeout_stats.append(elapsed)
        return result
```

#### 方案 3: 并行处理 (未实施)

**潜在方案**：

```python
# 多进程并行
from concurrent.futures import ProcessPoolExecutor

def process_batch(chunks):
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = executor.map(llm_extract, chunks)
    return list(results)
```

**未采用原因**：

1. Ollama 单实例限制
2. 内存压力增大
3. 7B 模型已足够快

### 性能对比

```
优化前（32B）:
├─ 单块: 200s
├─ 处理块数: 需要很长时间
└─ 超时率: 较高

优化后（7B + timeout=600）:
├─ 单块: 大幅缩短
├─ 总时间: 显著减少
└─ 超时率: 大幅降低
```

### 技术启示

1. **帕累托原则** - 7B 模型提供较高质量，但速度快很多倍
2. **业务优先** - 可用性 > 极致质量
3. **数据优于算法** - 更多样本 > 更大模型

---

## 核心挑战三：错误处理与容错设计

### 问题背景

**典型错误场景**：

```python
# LLM 抽取失败返回 None
concepts, relationships = llm_extract(chunk)
# concepts = None, relationships = None

# Checkpoint 保存时崩溃
len(concepts)  # TypeError: object of type 'NoneType' has no len()
```

**影响**：

- 单个块失败导致整个管道崩溃
- 已处理的数据丢失
- 用户体验极差

### 技术分析

#### 错误传播链

```
LLM API 错误
  ↓
返回 None
  ↓
checkpoint_manager.save_chunk_results(None, None)
  ↓
len(None) → TypeError
  ↓
管道崩溃，数据丢失
```

#### 根本问题

1. **缺少防御性编程** - 未验证输入
2. **错误边界不清** - 异常向上传播
3. **无降级策略** - 全或无的逻辑

### 解决方案：多层防御

#### Layer 1: LLM 调用层

```python
def extract_concepts_and_relationships(self, text, chunk_id):
    """
    LLM 抽取，带重试和降级
    """
    try:
        response = self.call_ollama(prompt, timeout=self.config['timeout'])

        if response is None:
            logger.warning(f"Chunk {chunk_id}: LLM returned None")
            return [], []  # 降级：返回空列表

        concepts, rels = self.parse_response(response)
        return concepts or [], rels or []  # 确保非 None

    except requests.Timeout:
        logger.error(f"Chunk {chunk_id}: Timeout after {self.config['timeout']}s")
        return [], []

    except Exception as e:
        logger.error(f"Chunk {chunk_id}: Unexpected error: {e}")
        return [], []  # 降级，不影响流程
```

#### Layer 2: Checkpoint 保存层

```python
def save_chunk_results(self, chunk_id, concepts, relationships):
    """
    保存结果，带输入验证
    """
    # 输入验证和标准化
    if concepts is None:
        concepts = []
    if relationships is None:
        relationships = []

    # 更新统计
    self.progress['processed_chunks'].append(chunk_id)
    self.progress['total_concepts'] += len(concepts)  # 现在安全了
    self.progress['total_relationships'] += len(relationships)

    # 保存（即使是空结果）
    self._append_to_csv(self.concepts_file, concepts)
    self._append_to_csv(self.relationships_file, relationships)
    self._save_progress()
```

#### Layer 3: 主循环层

```python
def _extract_with_checkpoints(self, chunks):
    """
    主提取循环，最外层防护
    """
    all_concepts = []
    all_relationships = []

    for i, chunk in enumerate(chunks):
        try:
            # 单块处理
            concepts, relationships = self.concept_extractor.extract(
                chunk['text'], chunk['chunk_id']
            )

            # 安全累积
            if concepts:
                all_concepts.extend(concepts)
            if relationships:
                all_relationships.extend(relationships)

            # 保存（即使当前块失败）
            self.checkpoint_manager.save_chunk_results(
                chunk['chunk_id'], concepts, relationships
            )

        except Exception as e:
            # 最外层捕获
            logger.error(f"Failed to process chunk {chunk['chunk_id']}: {e}")
            # 记录失败但继续处理
            continue

    return all_concepts, all_relationships
```

### 容错策略矩阵

| 层级          | 错误类型  | 处理策略        | 影响范围 |
| ------------- | --------- | --------------- | -------- |
| LLM 层        | Timeout   | 返回 []         | 单块     |
| LLM 层        | 解析失败  | 返回 []         | 单块     |
| Checkpoint 层 | None 输入 | 转为 []         | 无影响   |
| 主循环层      | 任意异常  | 记录 + continue | 单块     |

### 效果

**改进前**：

- 单点失败 → 管道崩溃
- 错误率 5% → 丢失所有数据

**改进后**：

- 单点失败 → 记录并继续
- 错误率 5% → 仅丢失 5% 数据
- **可用性显著提升，系统稳定可靠**

---

## 核心挑战四：用户体验与可观测性

### 问题背景

**初始状态**：

```bash
$ python main.py
Processing...
(无输出，运行数小时)
```

**用户困惑**：

- 程序是否在运行？
- 处理到哪里了？
- 还需要多久？
- 如何监控？

### 技术分析

#### 可观测性缺失

1. **无进度反馈** - 黑盒处理
2. **无状态查询** - 无法了解当前状态
3. **无性能指标** - 无法优化
4. **多入口混乱** - 多个启动方式，用户不知道用哪个

### 解决方案：多维度可观测性

#### 1. 实时进度条

```python
from tqdm import tqdm

def _extract_with_checkpoints(self, chunks):
    for i, chunk in enumerate(tqdm(chunks, desc="Extracting concepts")):
        # 处理...
        pass

# 输出:
# Extracting concepts:  7%|██▏                   | 36/507 [30:30<7:28:57, 57.19s/it]
```

**信息密度**：

- 当前进度：36/507 (7%)
- 已用时间：30:30
- 预计剩余：7:28:57
- 平均速度：57.19s/it

#### 2. 结构化日志

```python
import logging

# 分级日志
logger.info(f"Checkpoint: {i+1}/{len(chunks)} chunks processed")
logger.debug(f"Saved results for chunk: {chunk_id}")
logger.warning(f"Chunk {chunk_id}: LLM returned None")
logger.error(f"Failed to process chunk {chunk_id}: {e}")

# 日志输出
INFO - Checkpoint: 30/507 chunks processed
INFO -   Concepts: 202
INFO -   Relationships: 153
```

#### 3. 状态监控脚本

```bash
#!/bin/bash
# status.sh - 快速查看状态

echo "知识图谱构建状态"
echo "========================================"

# 读取进度
if [ -f "output/checkpoints/.progress.json" ]; then
    processed=$(jq '.processed_chunks | length' output/checkpoints/.progress.json)
    concepts=$(jq '.total_concepts' output/checkpoints/.progress.json)
    relationships=$(jq '.total_relationships' output/checkpoints/.progress.json)

    echo "[INFO] 已处理块数: $processed"
    echo "[INFO] 提取概念: $concepts"
    echo "[INFO] 提取关系: $relationships"
else
    echo "[WARN] 未找到进度文件"
fi

# 检查进程
if pgrep -f "enhanced_pipeline" > /dev/null; then
    echo "[INFO] 管道正在运行"
else
    echo "[WARN] 管道未运行"
fi
```

#### 4. 实时监控脚本

```bash
#!/bin/bash
# monitor.sh - 实时监控

watch -n 5 './status.sh'

# 每5秒刷新显示:
# =====================================
# 知识图谱构建状态
# =====================================
# [INFO] 已处理块数: 36
# [INFO] 提取概念: 241
# [INFO] 提取关系: 187
# [INFO] 管道正在运行
# =====================================
```

#### 5. 统一启动入口

**问题**：多个启动方式混乱

```bash
python main.py
python enhanced_pipeline.py
python enhanced_pipeline_safe.py
./run.sh
./start.py
```

**解决**：单一启动脚本 + 清晰文档

```bash
#!/bin/bash
# start.sh - 唯一推荐的启动方式

echo "====================================="
echo "知识图谱构建系统 v2.5"
echo "====================================="

# 环境检查
if [ ! -f "$PYTHON_BIN" ]; then
    echo "Python 3.10.13 未找到"
    exit 1
fi

# 进度恢复
if [ -f "output/checkpoints/.progress.json" ]; then
    processed=$(python -c "import json; print(len(json.load(open('output/checkpoints/.progress.json'))['processed_chunks']))")
    echo "[INFO] 发现 checkpoint, 将从断点继续"
    echo "  已处理块数: $processed"
fi

# 启动
echo "====================================="
echo "提示:"
echo "  - 按 Ctrl+C 可安全退出并保存进度"
echo "  - 在另一个终端运行 './monitor.sh' 查看进度"
echo "  - 日志文件: output/kg_builder.log"
echo "====================================="

exec "$PYTHON_BIN" enhanced_pipeline_safe.py "$@"
```

**START_HERE.md 文档**：

`````

````markdown
# 快速开始

## 唯一推荐的启动方式

```bash
./start.sh
`````

````

## 状态查看

```bash
./status.sh    # 一次性查看
./monitor.sh   # 实时监控
```

## 常见问题

Q: 如何中途停止？
A: Ctrl+C，进度会自动保存

Q: 如何恢复？
A: 再次运行 ./start.sh，自动从断点继续

````

### 效果对比

| 维度       | 改进前   | 改进后     | 提升     |
| ---------- | -------- | ---------- | -------- |
| 进度可见性 | 无       | 实时进度条 | 显著     |
| 状态查询   | 无       | status.sh  | 显著     |
| 实时监控   | 无       | monitor.sh | 显著     |
| 启动复杂度 | 多种方式 | 1 种方式   | 显著简化 |
| 用户满意度 | 低       | 高         | 提升     |

---

## 核心挑战五：Python 环境管理

### 问题背景

**错误现象**：

```bash
$ python3 enhanced_pipeline_safe.py
Traceback (most recent call last):
  File "enhanced_pipeline_safe.py", line 3, in <module>
    import pandas as pd
ModuleNotFoundError: No module named 'pandas'
```

**困惑**：

- 明明已经 `pip install pandas`
- 但程序找不到

### 技术分析

**根本原因**：Python 环境隔离

```
系统 Python (/usr/bin/python3)
  ├─ 无第三方包
  └─ 系统级，不应污染

pyenv Python (~/.pyenv/versions/3.10.13/bin/python)
  ├─ 项目依赖已安装
  └─ 但未正确激活
```

**问题链**：

```
用户执行: python3 script.py
  ↓
系统解析: /usr/bin/python3
  ↓
环境查找: 系统 site-packages (无第三方包)
  ↓
结果: ModuleNotFoundError
```

### 解决方案

#### 方案 1: 启动脚本指定完整路径

```bash
#!/bin/bash
# start.sh

# 硬编码 pyenv Python 路径
PYTHON_BIN="$HOME/.pyenv/versions/3.10.13/bin/python"

# 检查存在性
if [ ! -f "$PYTHON_BIN" ]; then
    echo "[ERROR] Python 3.10.13 未找到"
    exit 1
fi

# 使用完整路径执行
exec "$PYTHON_BIN" enhanced_pipeline_safe.py "$@"
```

**优点**：

- 明确无歧义
- 不依赖环境变量
- 对用户透明

#### 方案 2: Shebang (未采用)

```python
#!/usr/bin/env python3
# enhanced_pipeline_safe.py
```

**问题**：

- 仍依赖 PATH
- 无法保证用对环境

#### 方案 3: 文档说明 (辅助)

```markdown
# 依赖安装

## 1. 安装 pyenv

brew install pyenv

## 2. 安装 Python 3.10.13

pyenv install 3.10.13

## 3. 设置项目环境

pyenv local 3.10.13

## 4. 安装依赖

pip install -r requirements.txt

## 5. 启动

./start.sh # 自动使用正确的 Python
```

### 技术启示

1. **显式优于隐式** - 硬编码路径比依赖 PATH 更可靠
2. **降低用户负担** - 启动脚本处理复杂性
3. **防御性编程** - 检查环境存在性

---

## 系统架构演进

### v1.0: 原始版本

```
PDF → 文本提取 → LLM 抽取 → 一次性保存 → Neo4j
```

**问题**：

- 无容错
- 数据易丢失
- 不可中断

### v2.0: 增加 Checkpoint

```
PDF → 文本提取 → LLM 抽取 → 增量保存 → Neo4j
                    ↓
                Checkpoint Manager
```

**改进**：

- 断点续传
- 数据安全
- 可中断

### v2.5: 完整优化 (当前)

```
PDF → 文本提取 → 分块 → LLM 抽取(7B) → 去重 → 保存 → Neo4j
                  ↓         ↓           ↓      ↓
              进度条   Checkpoint   BGE-M3  监控脚本
                      (每10块)
```

**特性**：

- 多层容错
- 性能优化 (显著提升)
- 完整可观测性
- 用户友好

---

## 技术总结

### 核心原则

1. **稳定性优先**

   - 增量保存胜过批量保存
   - 容错设计胜过完美执行
   - 降级策略胜过失败中断

2. **用户体验第一**

   - 可观测性至关重要
   - 单一入口降低复杂度
   - 文档与代码同等重要

3. **性能与质量平衡**

   - 7B 模型较高质量 + 很高速度 > 32B 模型最高质量
   - 可用性优于完美性
   - 业务价值导向

4. **工程化思维**
   - 防御性编程
   - 多层防护
   - 显式配置

### 技术栈选择

| 组件      | 选型             | 理由             |
| --------- | ---------------- | ---------------- |
| LLM       | Qwen2.5-Coder:7B | 速度与质量平衡   |
| Embedding | BGE-M3           | 中文语义理解最佳 |
| 图数据库  | Neo4j            | 知识图谱标准     |
| 日志      | Python logging   | 结构化 + 分级    |
| 进度      | tqdm             | 直观 + 易用      |
| 配置      | YAML             | 可读性强         |

### 性能指标

| 指标       | 目标     | 实际效果 | 状态     |
| ---------- | -------- | -------- | -------- |
| 总运行时间 | 显著优化 | 大幅缩短 | 超额完成 |
| 数据丢失率 | 0%       | 大幅降低 | 达标     |
| 错误容忍   | > 99.9%  | 显著提升 | 达标     |
| 可中断恢复 | 支持     | 支持     | 达标     |
| 用户满意度 | 高       | 高       | 达标     |

> 注：具体性能数据基于 README.md 中的优化结果

### 未来优化方向

1. **并行处理**

   - 多 GPU 并行推理
   - 分布式处理

2. **增量更新**

   - 新文献自动合并
   - 图谱版本管理

3. **交互式优化**

   - Web UI
   - 实时结果预览

4. **质量评估**
   - 自动化质量检查
   - 人工标注反馈

---

## 经验教训

### 技术层面

1. **不宜过早优化**

   - 先保证可用性，再追求性能
   - 32B → 7B 的决策证明正确

2. **重视使用体验**

   - "这是卡死了吗" → 加进度条
   - "怎么启动" → 统一入口

3. **复杂性必须封装**
   - Python 环境 → start.sh
   - 状态查询 → status.sh
   - 实时监控 → monitor.sh

### 工程层面

1. **文档驱动开发**

   - README.md 整合关键信息，降低上手成本
   - FIX_SUMMARY.md 记录问题历程

2. **渐进式交付**

   - v1.0 → v2.0 → v2.5
   - 每次解决一个核心问题

3. **用户视角设计**
   - 不是程序员的用户也能轻松使用
   - 一个命令完成所有操作

---

## 附录：代码位置与日志速查

### A. 核心挑战与源码映射表

| 挑战编号 | 技术挑战             | 核心文件                    | 关键类/函数                                                    | 日志关键词                                      |
| -------- | -------------------- | --------------------------- | -------------------------------------------------------------- | ----------------------------------------------- | --- | ---------------------------------- |
| 挑战一   | 长时间运行的数据安全 | `checkpoint_manager.py`     | `CheckpointManager.save_chunk_results`                         | `Checkpoint saved at chunk`, `processed_chunks` |
|          |                      | `enhanced_pipeline_safe.py` | `EnhancedKnowledgeGraphPipelineSafe._extract_with_checkpoints` | `RESUMING from previous checkpoint`             |
| 挑战二   | LLM 推理性能优化     | `concept_extractor.py`      | `ConceptExtractor._call_ollama`                                | `Ollama timeout`, `Processing chunks`, `s/it`   |
|          |                      | `config/config.yaml`        | `llm.model`, `llm.timeout`                                     | `Model: qwen2.5-coder:7b`, `timeout: 600s`      |
| 挑战三   | 错误处理与容错设计   | `enhanced_pipeline_safe.py` | `_extract_with_checkpoints` (try-except-continue)              | `Failed to process chunk`, `LLM returned None`  |
|          |                      | `checkpoint_manager.py`     | `save_chunk_results` (None 检查与标准化)                       | `Saved results for chunk: X with 0 concepts`    |
|          |                      | `concept_extractor.py`      | `extract_concepts_and_relationships` (降级返回空列表)          | `JSON 解析失败`, `返回 empty results`           |
| 挑战四   | 用户体验与可观测性   | `run_pipeline.py`           | `main()`, `check_environment()`                                | `环境检查`, `预计总耗时`, `按 Enter 开始运行`   |
|          |                      | `status.sh`, `monitor.sh`   | shell 脚本读取`.progress.json`                                 | `已处理块数: X`, `剩余时间: 约 Y 分钟`          |
|          |                      | `enhanced_pipeline_safe.py` | `tqdm(chunks, desc="Extracting concepts")`                     | `7%                                             | ██▏ | 36/507 [30:30<7:28:57, 57.19s/it]` |
| 挑战五   | Python 环境管理      | `start.sh`                  | shell 脚本指定完整 Python 路径                                 | `Python 3.10.13 未找到`, `使用完整路径执行`     |

### B. 典型日志模式与对应代码

#### 1. 正常启动与进度日志

**日志片段**：

```
2025-11-29 19:30:00 - SafePipeline - INFO - Starting Safe Enhanced Pipeline with Checkpoint Support
2025-11-29 19:30:01 - SafePipeline - INFO - [Step 3/6] Extracting concepts with checkpoint support...
2025-11-29 19:32:18 - CheckpointManager - INFO - Saved results for chunk: paper1.pdf_0
2025-11-29 20:30:10 - SafePipeline - INFO - Checkpoint: 40/507 chunks processed
```

**对应代码**：

- `enhanced_pipeline_safe.py` - `EnhancedKnowledgeGraphPipelineSafe.run()` 方法：
  ```python
  logger.info("Starting Safe Enhanced Pipeline with Checkpoint Support")
  ```
- `enhanced_pipeline_safe.py` - `run()` 方法中的 Step 3：
  ```python
  logger.info("\n[Step 3/6] Extracting concepts with checkpoint support...")
  ```
- `checkpoint_manager.py` - `CheckpointManager.save_chunk_results()` 方法：
  ```python
  logger.debug(f"Saved results for chunk: {chunk_id}")
  ```
- `enhanced_pipeline_safe.py` - `_extract_with_checkpoints()` 方法：
  ```python
  logger.info(f"Checkpoint: {i+1}/{len(chunks)} chunks processed")
  ```

#### 2. 断点续传恢复日志

**日志片段**：

```
============================================================
RESUMING from previous checkpoint:
  - Processed chunks: 45
  - Total concepts: 352
  - Total relationships: 280
============================================================
Skipping 45 already processed chunks
Remaining chunks to process: 462
```

**对应代码**：

- `enhanced_pipeline_safe.py` - `run()` 方法中的断点续传逻辑：
  ```python
  if summary['processed_chunks'] > 0:
      logger.info("RESUMING from previous checkpoint:")
      logger.info(f"  - Processed chunks: {summary['processed_chunks']}")
      # ... 显示概念与关系统计
  ```
- `enhanced_pipeline_safe.py` - `run()` 方法中的块过滤逻辑：
  ```python
  if skipped > 0:
      logger.info(f"Skipping {skipped} already processed chunks")
      logger.info(f"Remaining chunks to process: {len(chunks)}")
  ```

#### 3. 异常处理与容错日志

**日志片段（LLM 超时）**：

```
WARNING - Ollama timeout (attempt 1/3), retrying...
WARNING - Ollama timeout (attempt 2/3), retrying...
ERROR - Ollama API timeout after 3 attempts
WARNING - Chunk paper5.pdf_23: LLM returned None, using empty results
INFO - Saved results for chunk: paper5.pdf_23 with 0 concepts, 0 relationships
```

**对应代码**：

- `concept_extractor.py` - `ConceptExtractor._call_ollama()` 方法（重试逻辑）：
  ```python
  except requests.exceptions.Timeout:
      if attempt < max_retries - 1:
          logger.warning(f"Ollama timeout (attempt {attempt + 1}/{max_retries}), retrying...")
          continue
      else:
          logger.error(f"Ollama API timeout after {max_retries} attempts")
          return None
  ```
- `concept_extractor.py` - `extract_concepts()` 方法（降级处理）：
  ```python
  if not response:
      return None  # 降级返回，不中断流程
  ```
- `enhanced_pipeline_safe.py` - `_extract_with_checkpoints()` 方法（主循环容错）：
  ```python
  except Exception as e:
      logger.error(f"Failed to process chunk {chunk_id}: {e}")
      continue  # 跳过失败块，继续处理
  ```

#### 4. 用户中断（Ctrl+C）日志

**日志片段**：

```
WARNING - ============================================================
WARNING - User interrupted (Ctrl+C)
WARNING - ============================================================
INFO - Checkpoint已自动保存，下次运行将从中断处继续
INFO - 进度保存位置: output/checkpoints
```

**对应代码**：

- `enhanced_pipeline_safe.py` - `run()` 方法中的 KeyboardInterrupt 异常处理：
  ```python
  except KeyboardInterrupt:
      logger.warning("User interrupted (Ctrl+C)")
      logger.info("Checkpoint已自动保存，下次运行将从中断处继续")
      logger.info(f"进度保存位置: {self.checkpoint_manager.checkpoint_dir}")
      raise  # 重新抛出，确保程序正常退出
  ```

### C. 关键配置文件与参数说明

#### config/config.yaml 核心参数

```yaml
llm:
  model: qwen2.5-coder:7b # 模型选择：7b(快)、14b(平衡)、32b(慢但准)
  ollama_host: http://localhost:11434
  timeout: 600 # API超时（秒），大模型需更长
  temperature: 0.1 # 降低随机性，提高JSON稳定性
  num_ctx: 8192 # 上下文窗口大小

deduplication:
  use_bge_m3: true # 启用BGE-M3混合检索
  similarity_threshold: 0.85 # 概念聚类阈值
  hybrid_alpha: 0.7 # dense与sparse权重（0.7表示70% dense）

filtering:
  min_importance: 2 # 最低重要性得分（1-5）
  min_connections: 1 # 最低连接数（度数）

system:
  enable_cache: true # PDF提取缓存
  enable_parallel: false # 并行处理（当前禁用）
```

**调优建议**：

- 速度优先：`model: qwen2.5-coder:7b`, `timeout: 300`
- 质量优先：`model: qwen2.5-coder:14b`, `timeout: 600`, `temperature: 0.05`
- 中文优化：`use_bge_m3: true`, `hybrid_alpha: 0.7`

### D. 输出文件结构与格式

#### 1. 进度文件（.progress.json）

**路径**：`output/checkpoints/.progress.json`

**格式**：

```json
{
  "processed_chunks": ["paper1.pdf_0", "paper1.pdf_1", "paper2.pdf_0"],
  "total_concepts": 352,
  "total_relationships": 280,
  "started_at": "2025-11-29T19:30:00",
  "last_update": "2025-11-29T20:30:10"
}
```

**用途**：

- 断点续传：读取`processed_chunks`判断哪些块已处理
- 状态监控：`status.sh`/`monitor.sh`读取展示进度

#### 2. 最终概念文件（concepts.csv）

**路径**：`output/concepts.csv`

**格式示例**：

```csv
entity,importance,category,chunk_id,type
松材线虫,5,pathogen,paper1.pdf_0,concept
马尾松,4,host,paper1.pdf_2,concept
松褐天牛,5,vector,paper1.pdf_1,concept
```

**字段说明**：

- `entity`：概念名称（已去重对齐）
- `importance`：1-5 分，LLM 评估的重要性
- `category`：概念类别（pathogen, host, vector 等）
- `chunk_id`：来源文本块
- `type`：固定为`concept`

#### 3. 最终关系文件（relationships.csv）

**路径**：`output/relationships.csv`

**格式示例**：

```csv
node_1,node_2,edge,weight,chunk_id,source
松材线虫,马尾松,感染,0.8,paper1.pdf_0,llm
松褐天牛,松材线虫,传播,0.8,paper1.pdf_1,llm
松材线虫,马尾松,co-occurs in,0.5,paper1.pdf_0,proximity
```

**字段说明**：

- `node_1`, `node_2`：关系两端实体（已对齐）
- `edge`：关系类型（感染、传播、co-occurs in 等）
- `weight`：关系权重（LLM 抽取 0.8，近邻关系 0.5）
- `source`：来源（llm 或 proximity）

### E. 故障排查决策树

```
程序无法启动？
├─ 提示"Python未找到"
│  └─ 检查start.sh中的PYTHON_BIN路径
├─ 提示"Ollama连接失败"
│  └─ 运行：ollama serve
└─ 提示"模型未找到"
   └─ 运行：ollama pull qwen2.5-coder:7b

程序运行缓慢？
├─ 单块耗时>120秒
│  └─ 配置：llm.model改为7b
├─ 频繁超时
│  └─ 配置：llm.timeout增加到600
└─ JSON解析失败率>10%
   └─ 配置：llm.temperature降至0.05

结果质量不佳？
├─ 概念重复多
│  └─ 配置：deduplication.similarity_threshold降至0.80
├─ 关系稀疏
│  └─ 检查：是否启用proximity关系
└─ 噪声概念多
   └─ 配置：filtering.min_importance提高到3

中断后数据丢失？
└─ 检查：是否使用enhanced_pipeline_safe.py
   └─ 是：查看output/checkpoints/.progress.json
   └─ 否：改用安全版本
```

---

**附录更新日期**：2025-11-29  
**对应项目版本**：v2.5  
**维护者**：知识工程第二组
