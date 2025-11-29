#!/bin/bash
# 快速下载 BGE-M3 (使用 wget + 国内镜像)

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

CACHE_DIR="$HOME/.cache/huggingface/hub/models--BAAI--bge-m3"
SNAPSHOT_DIR="$CACHE_DIR/snapshots/main"
MIRROR="https://hf-mirror.com/BAAI/bge-m3/resolve/main"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║          快速下载 BGE-M3 (使用国内镜像)                               ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# 创建目录
mkdir -p "$SNAPSHOT_DIR"
cd "$SNAPSHOT_DIR"

echo -e "${BLUE}下载核心文件到: $SNAPSHOT_DIR${NC}"
echo ""

# 核心文件列表（按大小排序，大文件最后）
files=(
    "config.json:687"
    "tokenizer_config.json:444"
    "special_tokens_map.json:964"
    "sentence_bert_config.json:54"
    "modules.json:349"
    "config_sentence_transformers.json:123"
    "tokenizer.json:17.1M"
    "pytorch_model.bin:2.27G"
)

total_files=${#files[@]}
current=0

for file_info in "${files[@]}"; do
    file="${file_info%%:*}"
    size="${file_info##*:}"
    current=$((current + 1))
    
    echo -e "${BLUE}[$current/$total_files]${NC} 下载: $file ($size)"
    
    # 跳过已存在的文件
    if [ -f "$file" ] && [ -s "$file" ]; then
        echo "  ✓ 已存在，跳过"
        continue
    fi
    
    # 下载文件
    if wget -q --show-progress -O "$file" "$MIRROR/$file"; then
        echo -e "  ${GREEN}✓ 下载完成${NC}"
    else
        echo -e "  ${YELLOW}⚠️  下载失败，继续...${NC}"
    fi
    echo ""
done

# 删除空的 safetensors（如果存在）
if [ -f "model.safetensors" ] && [ ! -s "model.safetensors" ]; then
    rm -f "model.safetensors"
fi

# 创建引用结构
mkdir -p "$CACHE_DIR/refs"
echo "main" > "$CACHE_DIR/refs/main"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    ✅ 下载完成！                                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 验证关键文件
echo "验证文件..."
if [ -f "pytorch_model.bin" ] && [ -s "pytorch_model.bin" ]; then
    size=$(ls -lh pytorch_model.bin | awk '{print $5}')
    echo "  ✓ pytorch_model.bin: $size"
else
    echo "  ❌ pytorch_model.bin 不存在或为空"
    exit 1
fi

if [ -f "config.json" ] && [ -f "tokenizer.json" ]; then
    echo "  ✓ 配置文件齐全"
else
    echo "  ❌ 配置文件缺失"
    exit 1
fi

echo ""
echo "模型路径: $SNAPSHOT_DIR"
echo ""
echo -e "${BLUE}提示: 当主程序运行到 Step 5 时，BGE-M3 将自动使用${NC}"
echo ""
