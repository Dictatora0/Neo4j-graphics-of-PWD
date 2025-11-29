# BGE-M3 模型下载配置指南

## 快速开始

运行交互式下载脚本：

```bash
./manual_download_bge_m3.sh
```

## 下载方式说明

### 方案 1: ModelScope 国内源（⭐ 推荐）

**优点：**

- ✅ 速度最快（国内 CDN）
- ✅ 不需要 VPN
- ✅ 稳定可靠

**适用场景：** 国内网络环境

```bash
./manual_download_bge_m3.sh
# 选择 1
```

### 方案 2: HuggingFace 镜像

**优点：**

- ✅ 官方模型格式
- ✅ 使用 hf-mirror.com 镜像
- ✅ 自动配置

**适用场景：** 需要官方格式或镜像可访问

```bash
./manual_download_bge_m3.sh
# 选择 2
```

### 方案 3: huggingface-cli

**优点：**

- ✅ 支持断点续传
- ✅ 命令行工具
- ✅ 适合大文件

**适用场景：** 网络不稳定需要断点续传

```bash
./manual_download_bge_m3.sh
# 选择 3
```

### 方案 4: wget 手动下载

**优点：**

- ✅ 完全手动控制
- ✅ 可单独下载文件
- ✅ 适合调试

**适用场景：** 其他方案失败或需要手动控制

```bash
./manual_download_bge_m3.sh
# 选择 4
```

### 方案 5: 禁用 BGE-M3（临时方案）

**说明：**

- 暂时不使用 BGE-M3
- 使用轻量级默认模型
- 可后续再下载 BGE-M3

**适用场景：** 急需运行程序，暂不需要高级去重

```bash
./manual_download_bge_m3.sh
# 选择 5
```

## 常见问题

### Q1: SSL 证书错误

**错误信息：**

```
SSLError: [SSL: CERTIFICATE_VERIFY_FAILED]
```

**解决方案：**

1. 使用方案 1 (ModelScope) - 最简单
2. 或设置环境变量：
   ```bash
   export SSL_CERT_FILE=/etc/ssl/cert.pem
   export REQUESTS_CA_BUNDLE=/etc/ssl/cert.pem
   ```

### Q2: 网络连接超时

**解决方案：**

1. 使用方案 1 (ModelScope 国内源)
2. 或使用方案 4 (wget 手动下载) 配合重试

### Q3: 下载中断

**解决方案：**

- 使用方案 3 (huggingface-cli) 支持断点续传
- 或重新运行脚本

### Q4: 磁盘空间不足

**模型大小：** 约 1.1 GB

**检查空间：**

```bash
df -h ~
```

**清理缓存：**

```bash
# 清理 pip 缓存
pip cache purge

# 清理旧的模型缓存（谨慎！）
rm -rf ~/.cache/huggingface/hub/models--BAAI--bge-m3.old
```

### Q5: 如何验证下载成功？

运行状态检查：

```bash
./manual_download_bge_m3.sh
# 选择 6 - 查看模型状态
```

或手动验证：

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('BAAI/bge-m3')
embeddings = model.encode(['测试文本'])
print(f"✓ BGE-M3 工作正常，向量维度: {embeddings.shape}")
```

## 模型位置

### HuggingFace 缓存

```
~/.cache/huggingface/hub/models--BAAI--bge-m3/
```

### ModelScope 缓存

```
~/.cache/modelscope/hub/AI-ModelScope/bge-m3/
```

## 配置文件

修改 `config/config.yaml` 启用/禁用 BGE-M3：

```yaml
deduplication:
  use_bge_m3: true # true=启用, false=禁用
  embedding_model: BAAI/bge-m3
```

## 性能对比

| 模型          | 大小  | 速度 | 准确度     |
| ------------- | ----- | ---- | ---------- |
| BGE-M3        | 1.1GB | 中等 | ⭐⭐⭐⭐⭐ |
| MiniLM (默认) | 90MB  | 快速 | ⭐⭐⭐     |

## 下一步

下载完成后：

```bash
# 1. 启动知识图谱构建
./start.sh

# 2. 监控进度
./monitor.sh

# 3. 查看日志
tail -f output/kg_builder.log
```

## 技术支持

遇到问题？

1. 查看日志：`output/kg_builder.log`
2. 运行状态检查：`./manual_download_bge_m3.sh` (选择 6)
3. 查看详细错误信息

## 附录：手动命令

### ModelScope 手动下载

```python
from modelscope import snapshot_download
model_dir = snapshot_download('AI-ModelScope/bge-m3')
print(f'模型路径: {model_dir}')
```

### HuggingFace 手动下载

```python
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
from transformers import AutoModel, AutoTokenizer

model = AutoModel.from_pretrained('BAAI/bge-m3', trust_remote_code=True)
tokenizer = AutoTokenizer.from_pretrained('BAAI/bge-m3', trust_remote_code=True)
```

### wget 批量下载

```bash
BASE_URL="https://hf-mirror.com/BAAI/bge-m3/resolve/main"
for file in config.json tokenizer.json model.safetensors; do
    wget "$BASE_URL/$file"
done
```

---

**更新时间：** 2024-11
**脚本版本：** v1.0
