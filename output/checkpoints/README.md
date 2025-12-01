# Checkpoint 目录

本目录用于存储管道运行时的增量 checkpoint，支持断点续传。

## 最近清理记录

**清理时间**: 2025-12-01 21:56

**清理原因**:

- Ollama 服务因内存不足频繁崩溃
- 所有 LLM 调用失败（Connection refused）
- Checkpoint 数据不完整（concepts=0, relationships=0）

**清理内容**:

- ✅ 删除 186 个 checkpoint CSV 文件
- ✅ 删除进度文件 (.progress.json)
- ✅ 删除增量数据 (concepts_incremental.csv, relationships_incremental.csv)

**下次运行**: 将从头开始处理所有 PDF

---

## 系统优化建议

### 已完成

- ✅ 禁用图片描述功能（节省内存）
- ✅ 添加请求延迟（0.5 秒，防止 Ollama 过载）
- ✅ 降低并发数（parallel_workers: 4）
- ✅ 减小上下文窗口（num_ctx: 3072）

### 待优化

- 📌 使用更小的 LLM 模型（llama3.2:1b 替代 qwen2.5-coder:7b）
- 📌 限制处理的 chunk 数量（max_chunks: 30 测试）
- 📌 增加系统交换内存
- 📌 关闭不必要的后台应用

---

## 下次运行前检查

```bash
# 1. 确认Ollama正常
pgrep ollama && echo "✅ Ollama运行中" || echo "❌ 需要启动Ollama"

# 2. 检查可用内存
vm_stat | grep "Pages free"

# 3. 确认配置
grep -A2 "enable_image_captions" config/config.yaml

# 4. 运行pipeline
./start.sh
```
