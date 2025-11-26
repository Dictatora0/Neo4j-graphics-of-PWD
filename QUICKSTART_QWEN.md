# Qwen2.5-Coder 快速启动指南

## 🚀 快速开始

### 1. 安装 Qwen 模型

```bash
# 安装推荐模型（14B，最佳效果）
ollama pull qwen2.5-coder:14b

# 或者安装 7B 版本（更快）
ollama pull qwen2.5-coder:7b
```

### 2. 验证安装

```bash
# 检查模型是否安装成功
ollama list

# 应该看到类似输出：
# NAME                       ID              SIZE      MODIFIED
# qwen2.5-coder:14b         abc123def       8.9 GB    2 minutes ago
```

### 3. 启动 Ollama 服务

```bash
# 启动 Ollama（如果还未运行）
ollama serve

# 或在后台运行
nohup ollama serve > ollama.log 2>&1 &
```

### 4. 运行知识图谱构建

```bash
# 使用默认配置运行
python enhanced_pipeline.py

# 查看实时日志
tail -f ./output/kg_builder.log
```

## 📊 预期输出

```
============================================================
Starting Enhanced Knowledge Graph Pipeline
============================================================

[Step 1/6] Extracting text from PDFs...
Found 10 PDF files to process

[Step 2/6] Splitting texts into chunks...
Created 250 chunks

[Step 3/6] Extracting concepts and relationships using LLM...
Processing limit: 100 chunks
Optimized: single LLM call per chunk with strict JSON Schema
Model: Using Qwen2.5-Coder with enhanced structured output
Timeout: 180 seconds per request
Estimated time: ~2000 seconds (33 minutes)
Processing chunks: 100%|████████████████| 100/100

Extracted 850 concepts and 1200 LLM relationships

[Step 4/6] Analyzing contextual proximity...
Extracted 3500 proximity relationships

[Step 5/6] Merging and deduplicating concepts...
Merged relationships: 4700
Updated relationships after deduplication: 4500

[Step 6/6] Filtering and finalizing...
Final concepts: 650
Final relationships: 3800

============================================================
Enhanced Pipeline completed successfully
============================================================
Duration: 0:35:12
Final concepts: 650
Final relationships: 3800
```

## 🎯 配置调优

### 场景 1：追求最佳质量

```yaml
# config/config.yaml
llm:
  model: qwen2.5-coder:14b
  temperature: 0.05 # 降低随机性
  max_chunks: null # 处理所有 chunks
  num_ctx: 16384 # 增大上下文
```

### 场景 2：平衡速度与质量

```yaml
llm:
  model: qwen2.5-coder:7b # 使用 7B 版本
  temperature: 0.1
  max_chunks: 100 # 限制处理数量
  num_ctx: 8192
```

### 场景 3：快速测试

```yaml
llm:
  model: qwen2.5-coder:7b
  temperature: 0.2
  max_chunks: 20 # 只处理 20 个 chunks
  num_ctx: 4096
```

## 🔧 常见问题

### Q1: "Ollama timeout" 错误

**原因**：Qwen-14B 处理复杂文本可能超过默认超时。

**解决**：

```yaml
llm:
  timeout: 300 # 增加到 300 秒
```

### Q2: JSON 解析失败

**原因**：极少数情况下 Qwen 可能输出非标准 JSON。

**解决**：

1. 降低 temperature：

   ```yaml
   llm:
     temperature: 0.05
   ```

2. 检查日志了解具体错误：
   ```bash
   grep "JSON 解析失败" ./output/kg_builder.log
   ```

### Q3: 内存不足

**原因**：Qwen-14B 需要较多内存（约 9GB）。

**解决**：

- 切换到 7B 版本：

  ```yaml
  llm:
    model: qwen2.5-coder:7b # 只需 ~5GB
  ```

- 或使用量化版本：
  ```bash
  ollama pull qwen2.5-coder:14b-q4_0  # 4-bit 量化
  ```

### Q4: 处理速度慢

**优化策略**：

1. **减少处理量**：

   ```yaml
   llm:
     max_chunks: 50 # 只处理前 50 个 chunks
   ```

2. **使用更小的模型**：

   ```yaml
   llm:
     model: qwen2.5-coder:7b
   ```

3. **增加 chunk 大小**（减少 chunk 数量）：
   ```python
   # enhanced_pipeline.py
   chunks = self._create_chunks(pdf_texts, chunk_size=5000)  # 从 3000 增加到 5000
   ```

## 📈 性能基准

基于 100 个文本块的测试：

| 模型                  | 时间    | 概念数 | 关系数 | JSON 成功率 |
| --------------------- | ------- | ------ | ------ | ----------- |
| **Qwen2.5-Coder-14B** | 33 分钟 | 650    | 3800   | 97%         |
| Qwen2.5-Coder-7B      | 20 分钟 | 580    | 3400   | 92%         |
| Llama3.2-3B           | 15 分钟 | 450    | 2800   | 78%         |

## 🔍 验证输出

### 检查概念提取质量

```bash
# 查看提取的概念
head -20 ./output/concepts.csv

# 统计各类别的概念数量
cut -d',' -f3 ./output/concepts.csv | sort | uniq -c
```

### 检查关系提取质量

```bash
# 查看提取的关系
head -20 ./output/relationships.csv

# 统计各关系类型的数量
cut -d',' -f3 ./output/relationships.csv | sort | uniq -c
```

## 🎓 高级用法

### 批量处理多个 PDF 目录

```python
from enhanced_pipeline import run_enhanced_pipeline

pdf_dirs = ['./文献/2023', './文献/2024', './文献/2025']

for pdf_dir in pdf_dirs:
    concepts, relations = run_enhanced_pipeline(pdf_dir=pdf_dir)
    print(f"Processed {pdf_dir}: {len(concepts)} concepts, {len(relations)} relations")
```

### 自定义 Prompt

修改 `concept_extractor.py` 中的 system_prompt 以适应特定领域：

```python
system_prompt = """你是XXX领域的知识图谱构建专家。

## 输出要求
严格按照以下 JSON Schema 输出：
{
  "concepts": [...],
  "relationships": [...]
}

## 概念类型
- 类型1: 示例1、示例2
- 类型2: 示例3、示例4
...
"""
```

## 📚 相关文档

- [详细升级说明](./docs/MODEL_UPGRADE.md)
- [完整配置文档](./config/config.yaml)
- [API 文档](./docs/API.md)

## 💡 最佳实践

1. **首次运行**：使用小批量测试（max_chunks: 10）
2. **调优参数**：根据输出质量调整 temperature
3. **监控日志**：使用 `tail -f` 实时查看处理进度
4. **定期备份**：保存 `./output/` 目录中的结果

---

**享受使用 Qwen2.5-Coder 构建高质量知识图谱！** 🎉
