# 自动负载监控与清理功能指南

## 🎯 功能概述

`start.sh` v2.6 新增**自动负载监控与清理**功能，在运行过程中持续监测系统资源，当检测到 CPU 或内存过载时自动执行清理操作，无需手动干预。

## ⚙️ 工作原理

### 1. 启动前检查

运行 `./start.sh` 时会先检查当前系统状态：

```bash
[系统检查] 检测当前资源状态...
  内存使用: 45%
  CPU使用: 23%
[正常] 系统资源充足
```

**预警机制**:

- **内存 ≥ 85%**: 🔴 强烈建议先运行 `./cleanup_memory.sh`
- **内存 70-84%**: 🟡 提示偏高，但会启动自动清理
- **内存 < 70%**: 🟢 正常运行

### 2. 后台自动监控

启动后会创建一个后台监控进程：

```
[监控] 启动后台资源监控 (间隔: 60s)
[监控] 后台监控已启动 (PID: 12345)
  监控阈值: 内存 85%, CPU 90%
  监控日志: output/resource_monitor.log
```

**监控周期**: 每 60 秒检查一次

### 3. 自动清理触发

当检测到资源超过阈值时，自动执行清理：

```
[AUTO-CLEANUP] 检测到资源过载，执行自动清理...
  → 触发Python垃圾回收
  → 重启Ollama服务
  → 清理系统缓存
[AUTO-CLEANUP] 清理完成
```

**清理操作**:

1. **Python GC**: 释放 Python 进程的未使用内存
2. **重启 Ollama**: 完全释放模型占用的内存（最有效）
3. **清理系统缓存**: macOS 执行 `purge` 命令

### 4. 退出时清理

按 `Ctrl+C` 或程序结束时，自动停止后台监控进程，不留残留。

## 📊 监控阈值配置

在 `start.sh` 顶部可调整监控参数：

```bash
# 监控配置
MEMORY_THRESHOLD=85  # 内存使用率阈值 (%)
CPU_THRESHOLD=90     # CPU使用率阈值 (%)
CHECK_INTERVAL=60    # 检查间隔 (秒)
```

### 推荐配置

| 系统内存 | MEMORY_THRESHOLD | CHECK_INTERVAL | 说明       |
| -------- | ---------------- | -------------- | ---------- |
| < 8GB    | 80               | 30             | 更频繁监控 |
| 8-16GB   | 85               | 60             | 默认配置   |
| > 16GB   | 90               | 120            | 更宽松阈值 |

## 📝 监控日志

### 资源监控日志

位置: `output/resource_monitor.log`

示例内容:

```
[2025-12-01 20:30:15] Memory: 68%, CPU: 45%
[2025-12-01 20:31:15] Memory: 72%, CPU: 52%
[2025-12-01 20:32:15] Memory: 87%, CPU: 65%
[2025-12-01 20:32:15] ALERT: Memory 87%, CPU 65% - Triggering cleanup
[2025-12-01 20:32:20] Memory: 58%, CPU: 48%
```

### 查看实时日志

```bash
# 实时监控资源日志
tail -f output/resource_monitor.log

# 查看最近的清理记录
grep "ALERT" output/resource_monitor.log
```

## 🎮 使用示例

### 正常启动

```bash
./start.sh
```

系统会：

1. ✅ 检查当前资源状态
2. ✅ 启动后台监控
3. ✅ 运行主程序
4. ✅ 自动应对资源压力

### 资源不足时启动

```bash
./start.sh

[警告] 内存使用率过高 (87%)
建议: 运行 './cleanup_memory.sh' 清理后再启动
是否继续？(y/n)
```

**选择**:

- 输入 `n`: 退出，手动清理后重试
- 输入 `y`: 强制启动，依赖自动监控

### 运行中监控

```bash
# 终端1: 运行主程序
./start.sh

# 终端2: 实时查看资源
python monitor_memory.py

# 终端3: 查看自动清理日志
tail -f output/resource_monitor.log
```

## 🔍 故障排查

### 监控进程未启动

**症状**: 没有看到监控 PID 或日志

**检查**:

```bash
# 检查PID文件
cat /tmp/kg_monitor.pid

# 检查进程是否运行
ps -p $(cat /tmp/kg_monitor.pid)
```

**解决**:

```bash
# 手动清理
rm -f /tmp/kg_monitor.pid

# 重新启动
./start.sh
```

### 自动清理未触发

**症状**: 内存持续增长，未见清理操作

**原因**:

1. 未达到阈值（85%内存或 90% CPU）
2. 监控进程意外退出
3. Python 进程名称不匹配

**检查**:

```bash
# 查看日志是否有记录
tail output/resource_monitor.log

# 手动执行清理测试
./cleanup_memory.sh
```

### 清理后仍过载

**原因**: 数据量过大或系统资源真的不足

**解决方案**:

1. **降低并发**:

   ```yaml
   # config/config.yaml
   pdf:
     parallel_workers: 2
   ```

2. **使用更小模型**:

   ```yaml
   llm:
     model: qwen2.5-coder:7b
   ```

3. **分批处理**:
   ```yaml
   llm:
     max_chunks: 20
   ```

## 🆚 对比

### 无自动监控 vs 有自动监控

| 场景                | 无监控               | 有监控             |
| ------------------- | -------------------- | ------------------ |
| **内存逐渐增长**    | 最终卡死，需手动重启 | 自动清理，持续运行 |
| **Ollama 内存泄漏** | 占用 10GB+不释放     | 定期重启释放       |
| **长时间运行**      | 需人工监控           | 无人值守           |
| **清理时机**        | 手动判断             | 自动最佳时机       |

### 手动监控 vs 自动监控

| 功能           | `monitor_memory.py` | `start.sh` 自动监控 |
| -------------- | ------------------- | ------------------- |
| **实时可视化** | ✅ 实时图表         | ❌ 后台日志         |
| **自动清理**   | ❌ 仅监控           | ✅ 自动清理         |
| **易用性**     | 需额外终端          | 一键启动            |
| **适用场景**   | 调试分析            | 生产运行            |

**建议**: 两者结合使用

```bash
# 终端1: 自动监控运行
./start.sh

# 终端2: 实时可视化监控（可选）
python monitor_memory.py
```

## 📈 性能影响

### 监控开销

- **CPU 占用**: < 1%
- **内存占用**: < 10MB
- **磁盘 I/O**: 每分钟写入一行日志 (~50 bytes)

### 清理耗时

- **Python GC**: 即时（< 1 秒）
- **重启 Ollama**: 约 5 秒
- **系统 purge**: 2-5 秒

**总影响**: 可忽略不计

## 🚀 最佳实践

### 启动前

```bash
# 1. 检查系统状态
python monitor_memory.py --once

# 2. 如果内存>80%，先清理
./cleanup_memory.sh

# 3. 启动（自动监控已启用）
./start.sh
```

### 运行中

- ✅ 定期查看 `output/resource_monitor.log`
- ✅ 如有性能问题，检查是否频繁触发清理
- ✅ 根据日志调整阈值配置

### 完成后

```bash
# 检查是否有异常清理记录
grep "ALERT" output/resource_monitor.log | wc -l

# 清理监控日志（可选）
rm output/resource_monitor.log
```

## 🎯 进阶配置

### 更激进的清理策略

```bash
# 降低阈值，更早清理
MEMORY_THRESHOLD=75
CPU_THRESHOLD=80
CHECK_INTERVAL=30
```

### 更保守的清理策略

```bash
# 提高阈值，减少干预
MEMORY_THRESHOLD=90
CPU_THRESHOLD=95
CHECK_INTERVAL=120
```

### 仅监控不清理（调试模式）

注释掉 `auto_cleanup` 调用，仅记录日志：

```bash
# 第96-98行
if [ $mem_usage -ge $MEMORY_THRESHOLD ] || [ $cpu_usage -ge $CPU_THRESHOLD ]; then
    echo "[$timestamp] ALERT: Memory ${mem_usage}%, CPU ${cpu_usage}%" >> output/resource_monitor.log
    # auto_cleanup >> output/resource_monitor.log 2>&1  # 注释掉
fi
```

## 📚 相关文档

- **优化详情**: `MEMORY_OPTIMIZATION.md`
- **手动监控**: `monitor_memory.py --help`
- **手动清理**: `./cleanup_memory.sh`
- **完整文档**: `README.md`

---

**版本**: v2.6.0  
**更新**: 2025-12-01  
**状态**: ✅ 生产就绪  
**测试**: ✅ 已验证
