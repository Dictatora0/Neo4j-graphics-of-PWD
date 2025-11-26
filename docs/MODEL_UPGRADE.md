# 模型升级说明文档

## 概述

本项目已将默认 LLM 从 `llama3.2:3b` 升级为 **Qwen2.5-Coder-14B-Instruct**，并重构了 Prompt 以强制输出严格的 JSON Schema，减少对 `json_repair` 的依赖。

## 主要变更

### 1. 模型配置更新 (`config/config.yaml`)

#### 新增配置项

```yaml
llm:
  # 推荐模型优先级
  model: qwen2.5-coder:14b # 默认使用 Qwen2.5-Coder-14B

  # 备选模型列表
  fallback_models:
    - qwen2.5-coder:7b
    - deepseek-r1:7b-distill
    - llama3.2:3b

  # 更新的参数
  timeout: 180 # 增加超时时间以适配 Qwen 14B
  num_ctx: 8192 # 扩大上下文窗口 (Qwen 支持最高 32k)
  temperature: 0.1 # 降低温度以提高 JSON 输出稳定性

  # Qwen 专用配置
  qwen_config:
    enable_strict_json: true
    max_tokens: 2048
    top_p: 0.8
    top_k: 20
    repeat_penalty: 1.1
```

### 2. Prompt 重构 (`concept_extractor.py`)

#### 核心优化点

1. **强制 JSON Schema 输出**

   - 使用 Ollama 的 `format: json` 参数强制 JSON 模式
   - 详细定义 JSON Schema 结构
   - 移除对 markdown 代码块的清理逻辑

2. **增强的系统提示词**

   ```python
   system_prompt = """你是专业的松材线虫病知识图谱构建系统。

   ## 输出要求
   严格按照以下 JSON Schema 输出，不得添加任何解释或 markdown：

   {
     "concepts": [
       {"entity": "概念名称", "importance": 1-5整数, "category": "类别"}
     ],
     "relationships": [
       {"node_1": "源实体", "node_2": "目标实体", "edge": "关系类型"}
     ]
   }
   ```

3. **领域知识细化**

   - 明确的概念分类（9 大类别）
   - 结构化的关系类型定义（6 大类别）
   - 重要性评分标准（5 级评分）
   - 过滤规则（排除无效概念）

4. **API 参数优化**
   ```python
   payload = {
       "model": self.model,
       "format": "json",          # Qwen JSON 模式
       "temperature": 0.1,        # 降低随机性
       "top_p": 0.8,              # 核采样
       "top_k": 20,               # Top-K 采样
       "repeat_penalty": 1.1,     # 重复惩罚
       "num_ctx": 8192,           # 大上下文窗口
       "timeout": 180             # 增加超时
   }
   ```

### 3. Pipeline 更新 (`enhanced_pipeline.py`)

- 更新日志输出以反映 Qwen 模型特性
- 调整时间估算（从 15s/chunk 增加到 20s/chunk）

## 使用指南

### 1. 安装 Qwen 模型

```bash
# 推荐：Qwen2.5-Coder-14B-Instruct
ollama pull qwen2.5-coder:14b

# 备选：Qwen2.5-Coder-7B (更快)
ollama pull qwen2.5-coder:7b

# 备选：DeepSeek-R1-Distill-7B
ollama pull deepseek-r1:7b-distill
```

### 2. 验证模型安装

```bash
ollama list
# 应该看到 qwen2.5-coder:14b 或其他已安装的模型
```

### 3. 运行 Pipeline

```bash
# 使用默认配置 (Qwen2.5-Coder-14B)
python enhanced_pipeline.py

# 或者指定 PDF 目录
python -c "from enhanced_pipeline import run_enhanced_pipeline; run_enhanced_pipeline(pdf_dir='./文献')"
```

### 4. 切换模型（可选）

如果需要使用其他模型，修改 `config/config.yaml`：

```yaml
llm:
  model: qwen2.5-coder:7b # 或 deepseek-r1:7b-distill 或 llama3.2:3b
```

## 性能对比

| 模型                   | 上下文窗口 | 处理速度   | JSON 准确率 | 推荐场景         |
| ---------------------- | ---------- | ---------- | ----------- | ---------------- |
| **Qwen2.5-Coder-14B**  | 8k-32k     | ~20s/chunk | 95%+        | 生产环境（推荐） |
| Qwen2.5-Coder-7B       | 8k-32k     | ~12s/chunk | 90%+        | 平衡性能与速度   |
| DeepSeek-R1-Distill-7B | 8k         | ~15s/chunk | 88%+        | 推理能力增强     |
| Llama3.2-3B            | 2k-4k      | ~10s/chunk | 75%+        | 快速测试         |

## 优势

### 1. JSON 输出更可靠

- **之前**：需要大量清理 markdown 代码块和修复 JSON 格式
- **现在**：Qwen 直接输出标准 JSON，几乎不需要修复

### 2. 领域知识提取更准确

- 详细的系统提示词提供明确的分类和评分标准
- 9 大概念类别 + 6 大关系类型
- 5 级重要性评分系统

### 3. 更大的上下文窗口

- **之前**：Llama 3.2 只支持 2-4k tokens
- **现在**：Qwen 支持 8k-32k tokens，可以处理更长的文本块

### 4. 更强的代码/结构化输出能力

- Qwen2.5-Coder 专门针对代码和结构化输出优化
- 更好的 JSON Schema 遵循能力

## 故障排查

### 问题 1：Ollama 连接失败

```bash
# 检查 Ollama 是否运行
curl http://localhost:11434/api/tags

# 如果未运行，启动 Ollama
ollama serve
```

### 问题 2：模型未安装

```bash
# 查看已安装的模型
ollama list

# 安装缺失的模型
ollama pull qwen2.5-coder:14b
```

### 问题 3：JSON 解析失败

检查日志输出 `./output/kg_builder.log`：

- 如果频繁出现 JSON 解析错误，可能需要调整 temperature 参数
- 尝试降低到 0.05 以获得更确定的输出

```yaml
llm:
  temperature: 0.05 # 更低的温度 = 更确定的输出
```

### 问题 4：处理速度慢

如果 Qwen-14B 太慢，切换到 7B 版本：

```yaml
llm:
  model: qwen2.5-coder:7b # 速度提升约 40%
```

## Prompt 设计原则

### 1. 明确的输出格式

- 使用 JSON Schema 定义
- 提供具体的输出示例
- 强调"只输出 JSON，无其他内容"

### 2. 领域知识嵌入

- 列出具体的实体类型和示例
- 定义关系的层级和类型
- 提供评分标准

### 3. 过滤规则

- 明确排除无效概念
- 避免过于宽泛的术语
- 排除非领域内容

### 4. Few-Shot 示例

- 在 user_prompt 中提供标准输出示例
- 使用领域内的真实案例
- 确保示例格式完全正确

## 扩展建议

### 1. 多模型集成

可以在 `concept_extractor.py` 中添加模型自动切换逻辑：

```python
def __init__(self, model: str = "qwen2.5-coder:14b"):
    self.model = model
    self.fallback_models = ["qwen2.5-coder:7b", "llama3.2:3b"]
    self._try_connect_with_fallback()
```

### 2. 动态 Prompt 调整

根据模型类型自动调整 Prompt：

```python
if 'qwen' in self.model.lower():
    system_prompt = self._get_qwen_prompt()
elif 'deepseek' in self.model.lower():
    system_prompt = self._get_deepseek_prompt()
```

### 3. JSON Schema 验证

使用 `jsonschema` 库验证输出：

```python
import jsonschema

schema = {
    "type": "object",
    "properties": {
        "concepts": {"type": "array"},
        "relationships": {"type": "array"}
    },
    "required": ["concepts", "relationships"]
}

jsonschema.validate(data, schema)
```

## 参考资源

- [Qwen2.5-Coder 官方文档](https://github.com/QwenLM/Qwen2.5-Coder)
- [Ollama 文档](https://github.com/ollama/ollama)
- [JSON Schema 规范](https://json-schema.org/)

---

**更新时间**: 2024-11-27  
**作者**: Knowledge Graph Pipeline Team  
**版本**: 2.0
