# 📦 分批处理功能指南

## 功能概述

v2.7 版本新增**分批处理机制**，可以将大规模 PDF 处理任务分成多个小批次，每批次间自动清理内存、重启 Ollama，有效解决内存不足导致的崩溃问题。

---

## 核心特性

- ✅ **批次大小控制**: 自定义每批处理的 chunk 数量
- ✅ **三种运行模式**: 自动/手动/单批
- ✅ **批次间自动清理**: 重启 Ollama、垃圾回收
- ✅ **进度追踪**: 批次日志、状态恢复
- ✅ **失败重试**: 支持批次重试和跳过
- ✅ **断点续传**: 与 checkpoint 完美集成

---

## 快速开始

### 基础用法

```bash
# 默认配置（每批50个chunks，自动模式）
./start.sh

# 自定义批次大小
./start.sh --batch-size 30

# 手动确认模式
./start.sh --batch-mode manual

# 单批测试模式
./start.sh --batch-mode single --batch-size 10
```

---

## 参数说明

### 命令行参数

| 参数                  | 说明                 | 默认值 |
| --------------------- | -------------------- | ------ |
| `--batch-size <N>`    | 每批处理 N 个 chunks | 50     |
| `--batch-mode <mode>` | 批次模式（见下表）   | auto   |
| `--no-cleanup`        | 禁用批次间自动清理   | false  |
| `--help`              | 显示帮助信息         | -      |

### 批次模式

| 模式     | 行为                 | 适用场景                        |
| -------- | -------------------- | ------------------------------- |
| `auto`   | 自动连续处理所有批次 | 🚀 **推荐**：系统稳定，无人值守 |
| `manual` | 每批完成后需手动确认 | 👀 监控运行状态，调整策略       |
| `single` | 只处理一批后停止     | 🧪 测试、调试、增量更新         |

---

## 使用场景

### 场景 1：首次运行（内存受限）

```bash
# 1. 小批量测试
./start.sh --batch-size 10 --batch-mode single

# 2. 检查结果
cat output/batch_progress.log

# 3. 确认无误后，自动模式批量处理
./start.sh --batch-size 30 --batch-mode auto
```

**优势**:

- 快速发现配置问题
- 避免大规模崩溃
- 及时调整参数

---

### 场景 2：夜间长时间运行

```bash
# 自动模式 + 大批次
./start.sh --batch-size 100 --batch-mode auto > output/night_run.log 2>&1 &

# 监控进度
tail -f output/batch_progress.log
```

**优势**:

- 无需人工干预
- 批次间自动清理
- 日志完整记录

---

### 场景 3：调试特定批次

```bash
# 单批模式，逐批检查
./start.sh --batch-size 5 --batch-mode single

# 第1批完成后，手动检查
cat output/concepts.csv

# 继续下一批
./start.sh --batch-size 5 --batch-mode single
```

**优势**:

- 精细控制
- 逐步验证
- 问题定位

---

### 场景 4：失败恢复

```bash
# 如果某批次失败，会提示:
#   1. 重试当前批次
#   2. 跳过当前批次
#   3. 退出

# 选择1: 重试（Ollama重启后可能成功）
# 选择2: 跳过损坏的chunk
# 选择3: 退出检查日志
```

---

## 工作原理

### 处理流程

```
开始
  ↓
批次N开始
  ↓
处理最多BATCH_SIZE个chunks
  ↓
批次N完成
  ↓
批次间清理（可选）
  ├─ 重启Ollama（释放内存）
  ├─ 等待系统稳定（3秒）
  └─ 检查内存状态
  ↓
根据模式决定下一步
  ├─ auto: 自动继续
  ├─ manual: 等待用户确认
  └─ single: 退出
  ↓
批次N+1开始...
```

### 批次间清理详解

```bash
# 清理动作（每批次间执行）
1. 停止Ollama进程
   pkill ollama

2. 等待3秒（让系统回收资源）
   sleep 3

3. 重启Ollama
   ollama serve &

4. 等待5秒（模型加载）
   sleep 5

5. 显示当前内存使用率
   check_system_resources
```

---

## 日志和监控

### 批次日志

```bash
# 查看批次进度
cat output/batch_progress.log

# 实时监控
tail -f output/batch_progress.log
```

**示例输出**:

```
[2025-12-01 22:00:00] Batch 1 started (size: 50)
[2025-12-01 22:05:30] Batch 1 completed
[2025-12-01 22:06:00] Batch 2 started (size: 50)
[2025-12-01 22:11:45] Batch 2 completed
[2025-12-01 22:12:15] All batches completed. Total processed: 100 chunks
```

### 系统日志

```bash
# Pipeline详细日志
tail -f output/kg_builder.log

# 资源监控日志
tail -f output/resource_monitor.log
```

---

## 性能优化

### 批次大小建议

| 系统内存 | 推荐批次大小 | 说明               |
| -------- | ------------ | ------------------ |
| < 4GB    | 10-20        | 频繁清理，稳定优先 |
| 4-8GB    | 30-50        | **推荐配置**       |
| > 8GB    | 50-100       | 提高效率           |

### 优化技巧

1. **动态调整**

   ```bash
   # 首批小规模测试
   ./start.sh --batch-size 10 --batch-mode single

   # 根据内存情况调整
   # 如果内存充足：
   ./start.sh --batch-size 50

   # 如果内存紧张：
   ./start.sh --batch-size 20
   ```

2. **禁用清理（高配置机器）**

   ```bash
   # 内存充足时可禁用清理，提高速度
   ./start.sh --batch-size 100 --no-cleanup
   ```

3. **配合监控使用**

   ```bash
   # 终端1：运行pipeline
   ./start.sh --batch-mode manual

   # 终端2：实时监控
   watch -n 5 'free -h; pgrep ollama'
   ```

---

## 故障排查

### 问题 1：批次一直失败

**症状**: 每批次都失败，无法继续

**原因**:

- Ollama 服务无法启动
- 模型文件损坏
- 磁盘空间不足

**解决**:

```bash
# 1. 检查Ollama
pgrep ollama || ollama serve &

# 2. 测试模型
ollama run llama3.2:1b "test"

# 3. 检查磁盘
df -h output/

# 4. 手动清理
./cleanup_memory.sh
```

---

### 问题 2：批次间清理失败

**症状**: 清理阶段卡住或报错

**原因**: Ollama 重启失败

**解决**:

```bash
# 强制重启Ollama
pkill -9 ollama
sleep 3
ollama serve > /tmp/ollama.log 2>&1 &
sleep 5
```

---

### 问题 3：批次处理过慢

**症状**: 单批次耗时超过预期

**原因**:

- 批次过大
- LLM 响应慢
- 系统资源不足

**解决**:

```bash
# 1. 减小批次
./start.sh --batch-size 20

# 2. 检查系统负载
top -l 1 | grep "CPU usage"
vm_stat | grep "Pages free"

# 3. 使用更小的模型
# 编辑 config/config.yaml
# model: llama3.2:1b
```

---

## 高级用法

### 组合多个选项

```bash
# 最保守配置（适合低配机器）
./start.sh --batch-size 10 --batch-mode manual

# 高效配置（适合高配机器）
./start.sh --batch-size 100 --no-cleanup

# 调试配置
./start.sh --batch-size 5 --batch-mode single
```

### 脚本自动化

```bash
#!/bin/bash
# auto_batch.sh - 自动分批处理脚本

BATCH_SIZES=(10 20 30)

for size in "${BATCH_SIZES[@]}"; do
    echo "Testing batch size: $size"
    ./start.sh --batch-size $size --batch-mode single

    # 检查结果
    if [ $? -eq 0 ]; then
        echo "✓ Batch size $size succeeded"
    else
        echo "✗ Batch size $size failed"
    fi

    sleep 10
done
```

---

## 与其他功能集成

### 1. 断点续传

分批处理完美支持断点续传：

```bash
# 批次1-3完成，Ctrl+C中断
./start.sh --batch-size 50

# 再次运行，自动从批次4开始
./start.sh --batch-size 50
```

### 2. 自动监控

批次处理时，后台监控同时运行：

```
批次处理循环
  ├─ 批次N执行
  └─ 后台监控
      ├─ 每60秒检查资源
      └─ 超阈值自动清理
```

### 3. 内存优化

分批处理配合内存优化措施：

```yaml
# config/config.yaml
llm:
  model: llama3.2:1b # 轻量级模型
  num_ctx: 3072 # 减小上下文
  max_chunks: 50 # 配合start.sh的--batch-size

pdf:
  enable_image_captions: false # 禁用图片描述
  parallel_workers: 4
```

---

## 最佳实践

### 1. 首次运行

```bash
# Step 1: 小批测试
./start.sh --batch-size 5 --batch-mode single

# Step 2: 检查输出
ls -lh output/concepts.csv
head output/batch_progress.log

# Step 3: 正式运行
./start.sh --batch-size 30 --batch-mode auto
```

### 2. 生产环境

```bash
# 推荐配置
./start.sh \
  --batch-size 50 \
  --batch-mode auto \
  > output/production_$(date +%Y%m%d).log 2>&1 &

# 后台运行，日志归档
```

### 3. 调试环境

```bash
# 详细日志 + 手动控制
./start.sh \
  --batch-size 10 \
  --batch-mode manual
```

---

## 性能对比

| 模式       | 批次大小  | 内存峰值 | 崩溃概率 | 总耗时           |
| ---------- | --------- | -------- | -------- | ---------------- |
| 无分批     | N/A       | 高       | 高       | 快（如果不崩溃） |
| 小批次     | 10        | 低       | 极低     | 慢（频繁清理）   |
| **中批次** | **30-50** | **中**   | **低**   | **适中（推荐）** |
| 大批次     | 100+      | 高       | 中       | 快（偶尔崩溃）   |

---

## 相关文档

- [内存优化指南](MEMORY_OPTIMIZATION.md)
- [完整优化总结](FINAL_OPTIMIZATION_SUMMARY.md)
- [Checkpoint 指南](output/checkpoints/README.md)

---

## 更新历史

- **v2.7** (2025-12-01): 新增分批处理机制
  - 三种运行模式（auto/manual/single）
  - 批次间自动清理
  - 失败重试和跳过
  - 详细批次日志

---

**💡 提示**: 分批处理是解决内存不足的最佳方案，推荐所有低配机器使用！
