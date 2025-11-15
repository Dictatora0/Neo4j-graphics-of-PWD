# 快速开始指南

## 运行系统

### 1. 确认环境

```bash
# 检查 Ollama 是否运行
curl http://localhost:11434/api/tags

# 检查模型是否可用
ollama list | grep llama3.2
```

### 2. 运行完整流程

```bash
# 使用完整工作流脚本
./run_complete_workflow.sh

# 或者直接运行
python main.py
```

### 3. 处理时间

- **处理时间**: 约 37.5 分钟
- **处理块数**: 150 块 (共 321 块的 46.7%)
- **预期概念**: 250-300 个

---

## 配置参数

### 当前配置

| 参数              | 值  |
| ----------------- | --- |
| `max_chunks`      | 150 |
| `min_importance`  | 1   |
| `min_connections` | 0   |

### 提示词配置

| 方面     | 设置         |
| -------- | ------------ |
| 语言     | 中文领域特定 |
| 领域词汇 | 9 类专业术语 |
| 关系类型 | 9 种明确关系 |

### 功能特性

- 类别标准化：统一中英文类别到中文
- 通用词过滤：自动过滤 20+ 种通用概念
- 领域聚焦：针对松材线虫病的专业提取

---

## 预期结果

### 概念质量

提取结果：

- 松材线虫, 松褐天牛, 马尾松 等具体概念
- 200-300 个概念
- 统一中文类别

### 关系质量

关系分布：

- 80-90% 共现关系
- 10-20% 语义关系

---

## 查看结果

### 统计报告

```bash
cat output/statistics_report.txt
```

### 概念列表

```bash
# CSV 格式
head -50 output/triples/triples_*.csv

# JSON 格式
cat output/triples/triples_*.json | jq '.concepts[:10]'
```

### Neo4j 图谱

```bash
# 启动 Neo4j 并查看
./view_results.sh
```

---

## 配置调整选项

### 快速测试模式

```yaml
llm:
  max_chunks: 100
```

处理时间：25 分钟  
预期概念：200-250 个

### 完整处理模式

```yaml
llm:
  max_chunks: null
```

处理时间：80 分钟  
预期概念：400-600 个

### 高质量模式

```yaml
llm:
  model: mistral
  max_chunks: 200
```

处理时间：2-3 小时  
预期概念：400-500 个

---

## 监控运行

### 查看实时日志

```bash
tail -f output/kg_builder.log
```

### 关键指标

- 成功块数：应该接近 150
- 失败块数：应该 < 10
- 概念数：应该 > 200
- 关系数：应该 > 1000

---

## 问题排查

### Ollama 连接失败

```bash
# 启动 Ollama
ollama serve

# 拉取模型
ollama pull llama3.2:3b
```

### JSON 解析失败过多

- 查看日志中的错误信息
- 考虑增加 `timeout` 到 180
- 尝试切换模型到 `qwen`

### 概念数量偏少

- 检查 `max_chunks` 是否生效
- 降低 `min_importance` 到 0
- 查看被过滤的通用概念数量

---

## 后续步骤

### 运行后分析

1. 查看统计报告了解实际提取效果
2. 检查概念质量是否有足够的具体概念
3. 验证关系类型语义关系比例
4. 在 Neo4j 中可视化图谱结构

### 根据结果调整

- 概念太多：提高 `min_importance` 或 `min_connections`
- 概念太少：降低过滤阈值或增加 `max_chunks`
- 质量不佳：切换到更大模型或优化提示词

---

## 建议

- 首次运行建议使用当前配置
- 观察效果后再决定是否调整
- 保留日志文件以便分析问题
- 可以随时中断并从缓存恢复
