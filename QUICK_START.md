# 快速启动指南

## 🚀 三种启动方式

### 方式 1: 使用 Python 启动器（推荐）⭐

**最详细的信息展示，包括环境检查、配置展示、时间估算**

```bash
python run_pipeline.py
```

**功能：**

- ✅ 自动环境检查（Ollama、模型、依赖）
- ✅ 显示详细配置信息
- ✅ 估算运行时间
- ✅ 实时进度显示
- ✅ 美观的输出格式
- ✅ 交互式确认

---

### 方式 2: 使用 Shell 脚本

**简洁的命令行方式**

```bash
bash run.sh
# 或
./run.sh
```

**功能：**

- ✅ 快速环境检查
- ✅ 自动调用 Python 启动器
- ✅ 适合脚本调用

---

### 方式 3: 直接运行

**最简单的方式**

```bash
# 安全模式（带 checkpoint）
python enhanced_pipeline_safe.py

# 或原版（无 checkpoint）
python enhanced_pipeline.py
```

---

## 📊 实时监控

在运行管道的同时，可以在另一个终端窗口中监控进度：

### 使用监控脚本（推荐）

```bash
bash monitor.sh
# 或
./monitor.sh
```

**监控信息：**

- 进程状态（PID、CPU、内存）
- Checkpoint 进度（已处理块数、概念数、关系数）
- 最近日志（最新 5 条）
- 输出文件状态
- 完成时间估算

**交互操作：**

- 按 `r` 刷新
- 按 `l` 查看完整日志
- 按 `q` 退出

---

### 手动查看进度

```bash
# 1. 实时查看日志
tail -f output/kg_builder.log

# 2. 查看 checkpoint 进度（需要 jq）
cat output/checkpoints/.progress.json | jq '.'

# 3. 查看已处理块数
cat output/checkpoints/.progress.json | jq '.processed_chunks | length'

# 4. 查看输出文件
ls -lh output/*.csv
```

---

## 🎯 完整流程示例

### 终端 1: 运行管道

```bash
# 启动
python run_pipeline.py

# 输出示例：
╔══════════════════════════════════════════════════════════════════════╗
║        松材线虫病知识图谱构建系统 v2.5                                  ║
╚══════════════════════════════════════════════════════════════════════╝

🔍 环境检查
══════════════════════════════════════════════════════════════════════
  ✓ Python 版本      3.10.13
  ✓ Ollama 服务      运行中
  ✓ LLM 模型         qwen2.5-coder:7b
  ✓ PyTorch 版本     2.9.1
  ✓ Apple GPU (MPS)  可用
  ✓ PDF 文件         21 个

⚙️  运行配置
══════════════════════════════════════════════════════════════════════
📝 LLM 配置:
  • 模型: qwen2.5-coder:7b
  • 处理块数: 100
  • 超时时间: 180 秒

🔄 去重配置:
  • 引擎: BGE-M3 (混合检索)
  • 相似度阈值: 0.85

⏱️  时间估算
══════════════════════════════════════════════════════════════════════
  • 单块耗时: ~92 秒
  • 处理块数: 100 个
  • 预计总耗时: 153.3 分钟 (2.6 小时)

💡 进度监控
══════════════════════════════════════════════════════════════════════
在另一个终端窗口中，可以使用以下命令监控进度:
  tail -f output/kg_builder.log
  bash monitor.sh

按 Enter 开始运行，或按 Ctrl+C 取消...
```

### 终端 2: 监控进度

```bash
bash monitor.sh

# 输出示例：
════════════════════════════════════════════════════════════════════════
 📊 知识图谱构建进度监控
 更新时间: 2024-11-29 20:30:15
════════════════════════════════════════════════════════════════════════

✓ 管道进程: 运行中
  PID: 12345, CPU: 95.5%, 内存: 2.3%

📝 Checkpoint 进度:
  已处理块数: 45
  总概念数: 523
  总关系数: 412
  最后更新: 2024-11-29 20:30:10

⏱️  时间估算:
  已运行: 68 分钟
  平均速度: 91 秒/块
  剩余时间: 约 83 分钟

📁 输出文件:
  ✓ concepts.csv: 47K (523 行)
  ✓ relationships.csv: 38K (412 行)
  ✓ .progress.json: 2.1K (1 行)

📋 最近日志:
  2024-11-29 20:30:10 - SafePipeline - INFO - ✓ Checkpoint: 45/100 chunks processed
  2024-11-29 20:30:08 - CheckpointManager - INFO - Saved results for chunk: chunk_045

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 快捷操作: [r] 刷新  [l] 查看完整日志  [q] 退出
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## ⚡ 快速测试

如果想快速验证功能，可以只处理少量文本块：

### 测试 15 个块（约 23 分钟）

```bash
python test_safe_with_bge.py --clear
```

### 测试 5 个块（约 8 分钟）

修改 `config/config.yaml`：

```yaml
llm:
  max_chunks: 5
```

然后运行：

```bash
python enhanced_pipeline_safe.py --clear
```

---

## 🔧 常见操作

### 清除进度重新开始

```bash
# 手动删除
rm -rf output/checkpoints/

# 或使用参数
python enhanced_pipeline_safe.py --clear
```

### 从断点继续

```bash
# 直接运行即可，会自动检测并继续
python enhanced_pipeline_safe.py
```

### 修改配置

编辑 `config/config.yaml`：

```yaml
# 减少处理数量
llm:
  max_chunks: 50  # 只处理 50 个块

# 增加超时时间
llm:
  timeout: 300  # 如果经常超时

# 切换模型
llm:
  model: qwen2.5-coder:14b  # 更强但更慢
```

### 查看结果

```bash
# 查看概念
head -20 output/concepts.csv

# 查看关系
head -20 output/relationships.csv

# 统计数量
wc -l output/*.csv
```

---

## 🛠️ 故障排查

### 问题 1: Ollama 服务未运行

```bash
# 启动 Ollama
ollama serve
```

### 问题 2: 模型未安装

```bash
# 下载 7B 模型（推荐）
ollama pull qwen2.5-coder:7b

# 或下载 14B 模型（更强但更慢）
ollama pull qwen2.5-coder:14b
```

### 问题 3: LLM 超时

**现象：**

```
Ollama timeout (attempt 1/3), retrying...
```

**解决：**

1. 增加超时时间（`config/config.yaml`）：

   ```yaml
   llm:
     timeout: 300 # 改为 300 秒
   ```

2. 减小文本块大小：
   ```yaml
   system:
     chunk_size: 2000 # 从 3000 降至 2000
   ```

### 问题 4: 内存不足

**解决：**

1. 减少并行度
2. 使用更小的模型
3. 减少批处理大小

### 问题 5: 进度丢失

**不用担心！**

- 每 10 个块会自动保存 checkpoint
- 最多损失 10 个块的进度（约 15 分钟）
- 重新运行会自动从断点继续

---

## 📋 依赖检查

### 安装所有依赖

```bash
pip install -r requirements.txt
```

### 验证关键依赖

```bash
# PyTorch
python -c "import torch; print(f'PyTorch: {torch.__version__}')"

# SentenceTransformers
python -c "import sentence_transformers; print('SentenceTransformers: OK')"

# BGE-M3
python test_bge_m3.py
```

---

## 🎓 进阶使用

### 在代码中调用

```python
from enhanced_pipeline_safe import run_safe_pipeline
from config_loader import load_config

# 加载配置
config = load_config()

# 自定义配置
config['llm']['max_chunks'] = 50
config['deduplication']['use_bge_m3'] = True

# 运行
concepts_df, relationships_df = run_safe_pipeline(
    config=config,
    checkpoint_interval=10,  # 每 10 个块保存
    resume=True,             # 断点续传
    clear_checkpoint=False   # 不清除旧进度
)

print(f"提取了 {len(concepts_df)} 个概念")
print(f"提取了 {len(relationships_df)} 个关系")
```

### 使用 tmux（防止 SSH 断开）

```bash
# 创建会话
tmux new -s pwd_kg

# 运行管道
python run_pipeline.py

# 分离会话：Ctrl+B, D
# 重新连接
tmux attach -t pwd_kg

# 查看所有会话
tmux ls

# 结束会话
tmux kill-session -t pwd_kg
```

---

## 📞 获取帮助

### 查看文档

- **完整文档**: `README.md`
- **升级说明**: `UPGRADE_SUMMARY.md`
- **安全模式**: `SAFE_MODE_GUIDE.md`
- **风险分析**: `CHECKPOINT_ANALYSIS.md`

### 查看日志

```bash
# 实时查看
tail -f output/kg_builder.log

# 查看错误
grep ERROR output/kg_builder.log

# 查看警告
grep WARNING output/kg_builder.log
```

---

## ✅ 快速检查清单

开始运行前，确认以下项目：

- [ ] Ollama 服务已启动 (`ollama serve`)
- [ ] 模型已下载 (`ollama list | grep qwen`)
- [ ] PDF 文件已放入 `文献/` 目录
- [ ] 依赖已安装 (`pip install -r requirements.txt`)
- [ ] PyTorch 版本 >= 2.1 (`python -c "import torch; print(torch.__version__)"`)
- [ ] 磁盘空间充足（至少 10GB）

全部确认后，运行：

```bash
python run_pipeline.py
```

---

**祝你构建知识图谱顺利！** 🎉
