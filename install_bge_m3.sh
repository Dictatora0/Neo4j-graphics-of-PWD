#!/bin/bash
# 手动下载 BGE-M3 模型

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
echo "║              手动下载 BGE-M3 模型                                     ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# 方案 1: 使用 ModelScope（国内源）
echo -e "${BLUE}方案 1: 使用 ModelScope 国内源（推荐）${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 检查 modelscope 是否安装
if ! $PYTHON_BIN -c "import modelscope" 2>/dev/null; then
    echo -e "${YELLOW}安装 modelscope...${NC}"
    $PIP_BIN install -q modelscope
    echo -e "${GREEN}✓ modelscope 已安装${NC}"
else
    echo -e "${GREEN}✓ modelscope 已安装${NC}"
fi

echo ""
echo -e "${BLUE}开始下载 BGE-M3 模型（约 1.1GB）...${NC}"
echo "这可能需要 3-10 分钟，请耐心等待"
echo ""

# 下载模型
$PYTHON_BIN << 'PYTHON_SCRIPT'
from modelscope import snapshot_download
import os
import shutil

print("正在从 ModelScope 下载 BAAI/bge-m3...")

try:
    # 下载到 modelscope 缓存
    model_dir = snapshot_download(
        'AI-ModelScope/bge-m3',
        cache_dir=os.path.expanduser('~/.cache/modelscope')
    )
    print(f"✓ 下载完成: {model_dir}")
    
    # 创建 HuggingFace 缓存目录
    hf_cache_dir = os.path.expanduser('~/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots')
    os.makedirs(hf_cache_dir, exist_ok=True)
    
    # 创建软链接
    snapshot_name = 'main'
    target_path = os.path.join(hf_cache_dir, snapshot_name)
    
    # 如果已存在，删除
    if os.path.exists(target_path):
        if os.path.islink(target_path):
            os.unlink(target_path)
        else:
            shutil.rmtree(target_path)
    
    # 创建软链接
    os.symlink(model_dir, target_path)
    print(f"✓ 创建软链接: {target_path} -> {model_dir}")
    
    # 创建 refs 文件
    refs_dir = os.path.expanduser('~/.cache/huggingface/hub/models--BAAI--bge-m3/refs')
    os.makedirs(refs_dir, exist_ok=True)
    
    with open(os.path.join(refs_dir, 'main'), 'w') as f:
        f.write(snapshot_name)
    
    print("\n" + "="*70)
    print("✅ BGE-M3 模型安装成功！")
    print("="*70)
    
except Exception as e:
    print(f"\n❌ 下载失败: {e}")
    print("\n尝试方案 2...")
    exit(1)

PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    ✅ 安装完成！                                      ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "现在可以运行:"
    echo "  ./start.sh"
    echo ""
    exit 0
fi

# 如果方案 1 失败，提示方案 2
echo ""
echo -e "${RED}方案 1 失败，请尝试以下方案 2:${NC}"
echo ""
echo -e "${BLUE}方案 2: 使用 Git LFS 克隆${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. 安装 git-lfs:"
echo "   brew install git-lfs"
echo ""
echo "2. 克隆模型:"
echo "   cd ~/.cache/huggingface/hub"
echo "   GIT_LFS_SKIP_SMUDGE=1 git clone https://hf-mirror.com/BAAI/bge-m3 models--BAAI--bge-m3"
echo "   cd models--BAAI--bge-m3"
echo "   git lfs pull"
echo ""
echo "3. 重新运行:"
echo "   ./start.sh"
echo ""
