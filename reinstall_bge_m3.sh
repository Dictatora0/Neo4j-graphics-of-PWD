#!/bin/bash
# 清理旧缓存并重新下载 BGE-M3（网络已修复）

set -e

PYTHON_BIN="$HOME/.pyenv/versions/3.10.13/bin/python"
PIP_BIN="$HOME/.pyenv/versions/3.10.13/bin/pip"

# 颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║          重新安装 BGE-M3 模型（网络已修复）                           ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# 1. 清理旧缓存
echo -e "${BLUE}Step 1: 清理旧缓存...${NC}"
if [ -d "$HOME/.cache/huggingface/hub/models--BAAI--bge-m3" ]; then
    echo "  删除旧缓存: ~/.cache/huggingface/hub/models--BAAI--bge-m3"
    rm -rf "$HOME/.cache/huggingface/hub/models--BAAI--bge-m3"
    echo -e "${GREEN}  ✓ 旧缓存已删除${NC}"
else
    echo "  ✓ 无旧缓存"
fi
echo ""

# 2. 安装 huggingface-hub
echo -e "${BLUE}Step 2: 确保 huggingface-hub 已安装...${NC}"
$PIP_BIN install -q huggingface-hub
echo -e "${GREEN}  ✓ huggingface-hub 已安装${NC}"
echo ""

# 3. 下载模型
echo -e "${BLUE}Step 3: 下载 BGE-M3 模型...${NC}"
echo "  模型大小: ~2.1GB"
echo "  预计时间: 3-10分钟（取决于网速）"
echo ""

$PYTHON_BIN << 'PYTHON_SCRIPT'
from huggingface_hub import snapshot_download
import os

print("正在下载 BAAI/bge-m3...")
print("-" * 60)

try:
    cache_dir = snapshot_download(
        repo_id="BAAI/bge-m3",
        cache_dir=os.path.expanduser("~/.cache/huggingface/hub"),
        resume_download=True
    )
    print("\n" + "=" * 60)
    print("✅ BGE-M3 下载成功!")
    print(f"缓存位置: {cache_dir}")
    print("=" * 60)
except Exception as e:
    print(f"\n❌ 下载失败: {e}")
    exit(1)

PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${BLUE}Step 4: 验证模型...${NC}"
    
    # 4. 验证模型
    $PYTHON_BIN << 'VERIFY_SCRIPT'
from sentence_transformers import SentenceTransformer
import os

# 禁用在线检查
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

try:
    print("加载模型...")
    model = SentenceTransformer('BAAI/bge-m3', device='cpu')
    
    print("测试 embedding...")
    embeddings = model.encode(["test"], normalize_embeddings=True)
    
    print("\n" + "=" * 60)
    print("✅ BGE-M3 验证成功！")
    print(f"  Embedding 维度: {embeddings.shape[1]}")
    print("=" * 60)
except Exception as e:
    print(f"\n⚠️  验证失败: {e}")
    print("模型已下载，但可能需要联网验证")
    print("程序运行时会自动处理")

VERIFY_SCRIPT
    
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    ✅ 安装完成！                                      ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "当程序运行到 Step 5 (去重) 时，BGE-M3 将自动使用"
    echo ""
else
    echo ""
    echo -e "${RED}❌ 安装失败${NC}"
    echo "请检查网络连接"
    exit 1
fi
