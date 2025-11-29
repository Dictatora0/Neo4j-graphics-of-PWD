# 超时问题修复总结

## 📊 问题诊断

### 发现的问题

1. **LLM 超时频繁**

   - 实际速度：~254 秒/块
   - 预期速度：~92 秒/块
   - 超时设置：180 秒（不够）

2. **NoneType 错误**

   - LLM 超时后返回 `None`
   - `checkpoint_manager.py` 没有处理 `None` 情况
   - 报错：`'NoneType' has no len()`

3. **进度情况**
   - ✅ 已成功处理 17 个块
   - ✅ 提取了 141 个概念、103 个关系
   - ❌ 有 3 个块处理失败
   - ⏱️ 总运行时间：72 分钟

---

## ✅ 已完成的修复

### 1. 增加超时时间

**文件：`config/config.yaml`**

```yaml
# 修改前
timeout: 180  # 不够用

# 修改后
timeout: 300  # 5分钟，足够处理慢速块
```

### 2. 减少处理块数（适应实际速度）

```yaml
# 修改前
max_chunks: 100  # 预计 2.6 小时

# 修改后
max_chunks: 50  # 实际需要 3.5 小时
```

### 3. 修复 NoneType 错误处理 ⭐

**文件：`checkpoint_manager.py`**

```python
# 修改前（会崩溃）
def save_chunk_results(self, chunk_id, concepts, relationships):
    self.progress["total_concepts"] += len(concepts)  # ❌ concepts 可能是 None

# 修改后（安全）
def save_chunk_results(self, chunk_id, concepts, relationships):
    # 处理 None 情况
    if concepts is None:
        concepts = []
    if relationships is None:
        relationships = []

    self.progress["total_concepts"] += len(concepts)  # ✅ 现在安全了
```

---

## 🚀 重新启动步骤

### 步骤 1: 停止当前进程（如果还在运行）

```bash
# 查找进程
ps aux | grep "enhanced_pipeline\|test_safe"

# 停止进程（替换 <PID>）
kill <PID>

# 或直接在终端按 Ctrl+C
```

### 步骤 2: 验证修复

```bash
# 检查当前状态
python check_status.py
```

### 步骤 3: 重新启动（会自动从第 18 个块继续）

选择以下任一方式：

```bash
# 方式 1: 快速启动（推荐）
python start.py

# 方式 2: 交互式启动
python run_pipeline.py

# 方式 3: 直接运行
python enhanced_pipeline_safe.py
```

**注意：**

- ✅ 会自动跳过已处理的 17 个块
- ✅ 从第 18 个块开始继续
- ✅ 之前的数据（141 概念、103 关系）已保存

### 步骤 4: 监控进度（可选）

在另一个终端运行：

```bash
bash monitor.sh
```

或手动查看：

```bash
# 实时日志
tail -f output/kg_builder.log

# 进度文件
cat output/checkpoints/.progress.json | python -m json.tool
```

---

## 📈 预期结果

### 修复后的表现

| 项目          | 修复前   | 修复后        |
| ------------- | -------- | ------------- |
| 超时设置      | 180 秒   | 300 秒        |
| NoneType 错误 | ❌ 崩溃  | ✅ 跳过失败块 |
| 失败块处理    | 中断运行 | 记录并继续    |
| 进度保存      | ✅ 正常  | ✅ 更稳定     |

### 预计运行时间

```
已处理：17 块（72 分钟）
剩余：33 块（50 块配置 - 17 已处理）
预计剩余时间：33 × 4.2 分钟 = 138.6 分钟（~2.3 小时）
总计：72 + 138.6 = 210.6 分钟（~3.5 小时）
```

### 最终输出

```
预计最终结果（50 块）：
- 概念数：~400-500 个
- 关系数：~300-400 个
- 去重后会更少
```

---

## 🎯 关键改进点

### 1. 鲁棒性提升 ⭐

- **修复前**: LLM 失败 → 程序崩溃 → 丢失进度
- **修复后**: LLM 失败 → 跳过该块 → 继续处理

### 2. 错误处理

```python
# 现在的处理流程
try:
    concepts, relationships = llm_extract(text)
except Exception as e:
    logger.error(f"Failed: {e}")
    concepts, relationships = None, None  # 返回 None

# checkpoint_manager 现在能安全处理 None
save_chunk_results(chunk_id, concepts, relationships)
# ✅ None 被转换为空列表 []
# ✅ 块被标记为已处理（避免重复）
# ✅ 继续处理下一个块
```

### 3. 超时适配

- 增加到 300 秒适应实际速度
- 避免频繁超时重试
- 减少不必要的等待

---

## 💡 优化建议（可选）

### 如果还想提速

#### 选项 1: 使用更小的模型

```bash
# 下载 3B 模型（更快但质量稍低）
ollama pull llama3.2:3b

# 修改配置
# config/config.yaml
model: llama3.2:3b
```

#### 选项 2: 减小文本块大小

```yaml
# config/config.yaml
system:
  chunk_size: 2000 # 从 3000 降至 2000
```

**效果：**

- 每块处理更快（~120 秒/块）
- 但总块数增加

#### 选项 3: 减少处理数量（测试用）

```yaml
llm:
  max_chunks: 20 # 先测试 20 块
```

---

## 📋 检查清单

重新启动前确认：

- [x] 超时时间已增加到 300 秒
- [x] max_chunks 已调整为 50
- [x] NoneType 错误已修复
- [x] checkpoint_manager.py 已更新
- [ ] 旧进程已停止
- [ ] 准备重新启动

---

## 🎉 总结

**问题根源：**

1. 超时设置太短（180 秒）
2. 代码未处理 LLM 失败（None）情况
3. 实际速度比测试慢 2.8 倍

**解决方案：**

1. ✅ 增加超时到 300 秒
2. ✅ 修复 None 处理逻辑
3. ✅ 调整预期（50 块 vs 100 块）

**现在可以：**

- 安全地重新启动
- 从第 18 个块继续
- 失败的块会被跳过而不是崩溃
- 预计 2-3 小时完成剩余任务

---

**准备好了就运行：**

```bash
python start.py
```

或先查看状态：

```bash
python check_status.py
```

Good luck! 🚀
