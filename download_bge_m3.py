#!/usr/bin/env python3
"""
手动下载 BGE-M3 模型（绕过 SSL 问题）
使用 modelscope 国内源
"""

import os

print("\n" + "="*70)
print(" 📦 手动下载 BGE-M3 模型")
print("="*70 + "\n")

print("方案 1: 使用 ModelScope（国内源，推荐）")
print("-"*70)
print("""
# 1. 安装 modelscope
pip install modelscope

# 2. 下载模型
python -c "
from modelscope import snapshot_download
model_dir = snapshot_download('AI-ModelScope/bge-m3', cache_dir='~/.cache/modelscope')
print(f'模型下载到: {model_dir}')
"

# 3. 然后需要转换到 HuggingFace 格式（暂时复杂）
""")

print("\n方案 2: 使用 wget 直接下载（简单但大）")
print("-"*70)
print("""
# 创建目录
mkdir -p ~/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/main

# 下载主要文件（约 1.1GB，需要翻墙或找国内镜像）
cd ~/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/main

# 下载列表（示例）
wget https://hf-mirror.com/BAAI/bge-m3/resolve/main/pytorch_model.bin
wget https://hf-mirror.com/BAAI/bge-m3/resolve/main/config.json
wget https://hf-mirror.com/BAAI/bge-m3/resolve/main/tokenizer.json
# ... 等等
""")

print("\n方案 3: 临时禁用去重，运行完成后单独处理")
print("-"*70)
print("""
# 修改配置
# config/config.yaml
deduplication:
  use_bge_m3: false  # 禁用

# 运行管道（会跳过去重）
./start.sh

# 完成后，单独运行去重脚本
python scripts/utils/auto_disambiguate.py
""")

print("\n" + "="*70)
print(" 💡 当前建议")
print("="*70)
print("""
由于网络问题（SSL 错误），建议：

1. 【最快】让程序继续运行（不去重）
   - 当前正在进行中
   - 2-3 小时后得到结果
   - 后期手动去重

2. 【最简单】临时禁用 BGE-M3
   - 已经在运行了，程序自动跳过了去重
   - 等它完成即可

3. 【最完美】解决网络问题后重新下载
   - 需要配置代理或等待网络恢复
   - 可能需要较长时间
""")

print("="*70 + "\n")
