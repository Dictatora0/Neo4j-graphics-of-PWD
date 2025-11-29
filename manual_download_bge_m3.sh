#!/bin/bash
# BGE-M3 手动下载配置脚本
# 支持多种下载方式，解决网络和SSL问题

set -e

PYTHON_BIN="$HOME/.pyenv/versions/3.10.13/bin/python"
PIP_BIN="$HOME/.pyenv/versions/3.10.13/bin/pip"

# 如果 Python 3.10.13 不存在，使用系统 Python
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
    PIP_BIN="pip3"
fi

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║              BGE-M3 模型手动下载配置工具                              ║"
echo "║              支持多种下载方式                                          ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# 设置 HuggingFace 镜像
export HF_ENDPOINT=https://hf-mirror.com
echo -e "${CYAN}✓ 已设置 HuggingFace 镜像: $HF_ENDPOINT${NC}"
echo ""

# 显示选项菜单
echo -e "${BLUE}请选择下载方式:${NC}"
echo ""
echo "  1. 使用 ModelScope 国内源下载（推荐，最快）"
echo "  2. 使用 HuggingFace 镜像下载"
echo "  3. 使用 huggingface-cli 下载"
echo "  4. 手动 wget 下载（适合网络不稳定）"
echo "  5. 禁用 BGE-M3（临时方案）"
echo "  6. 查看当前模型状态"
echo ""
read -p "请输入选项 (1-6): " choice
echo ""

case $choice in
    1)
        # 方案 1: ModelScope 国内源
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}方案 1: 使用 ModelScope 国内源${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        
        # 安装 modelscope
        echo -e "${YELLOW}1. 检查并安装 modelscope...${NC}"
        if ! $PYTHON_BIN -c "import modelscope" 2>/dev/null; then
            $PIP_BIN install -q modelscope
            echo -e "${GREEN}✓ modelscope 已安装${NC}"
        else
            echo -e "${GREEN}✓ modelscope 已存在${NC}"
        fi
        
        # 下载模型
        echo ""
        echo -e "${YELLOW}2. 下载 BGE-M3 模型（约 1.1GB）...${NC}"
        echo "   预计时间: 3-10 分钟"
        echo ""
        
        $PYTHON_BIN << 'EOF'
import os
import shutil
from modelscope import snapshot_download

try:
    print("正在从 ModelScope 下载 BAAI/bge-m3...")
    
    # 下载模型
    model_dir = snapshot_download(
        'AI-ModelScope/bge-m3',
        cache_dir=os.path.expanduser('~/.cache/modelscope')
    )
    print(f"\n✓ 下载完成: {model_dir}\n")
    
    # 创建 HuggingFace 兼容的目录结构
    hf_base = os.path.expanduser('~/.cache/huggingface/hub/models--BAAI--bge-m3')
    hf_snapshots = os.path.join(hf_base, 'snapshots')
    hf_refs = os.path.join(hf_base, 'refs')
    
    os.makedirs(hf_snapshots, exist_ok=True)
    os.makedirs(hf_refs, exist_ok=True)
    
    snapshot_path = os.path.join(hf_snapshots, 'main')
    
    # 删除已存在的链接或目录
    if os.path.exists(snapshot_path):
        if os.path.islink(snapshot_path):
            os.unlink(snapshot_path)
        else:
            shutil.rmtree(snapshot_path)
    
    # 创建符号链接
    os.symlink(model_dir, snapshot_path)
    print(f"✓ 创建符号链接: {snapshot_path} -> {model_dir}")
    
    # 创建 refs 文件
    with open(os.path.join(hf_refs, 'main'), 'w') as f:
        f.write('main\n')
    
    print("\n" + "="*70)
    print("✅ BGE-M3 模型安装成功！")
    print("="*70)
    print(f"\n模型路径: {model_dir}")
    print(f"HuggingFace 缓存: {hf_base}\n")
    
except Exception as e:
    print(f"\n❌ 下载失败: {e}\n")
    exit(1)
EOF
        
        if [ $? -eq 0 ]; then
            echo ""
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${GREEN}✅ 安装完成！现在可以运行: ./start.sh${NC}"
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        fi
        ;;
        
    2)
        # 方案 2: HuggingFace 镜像
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}方案 2: 使用 HuggingFace 镜像${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        
        echo -e "${YELLOW}通过 Python transformers 自动下载...${NC}"
        echo ""
        
        $PYTHON_BIN << 'EOF'
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

try:
    from transformers import AutoModel, AutoTokenizer
    
    print("正在下载 BGE-M3 模型...")
    print(f"使用镜像: {os.environ['HF_ENDPOINT']}\n")
    
    # 下载模型和分词器
    model_name = "BAAI/bge-m3"
    cache_dir = os.path.expanduser("~/.cache/huggingface")
    
    print("1. 下载分词器...")
    tokenizer = AutoTokenizer.from_pretrained(
        model_name, 
        cache_dir=cache_dir,
        trust_remote_code=True
    )
    print("✓ 分词器下载完成\n")
    
    print("2. 下载模型...")
    model = AutoModel.from_pretrained(
        model_name, 
        cache_dir=cache_dir,
        trust_remote_code=True
    )
    print("✓ 模型下载完成\n")
    
    print("="*70)
    print("✅ BGE-M3 模型安装成功！")
    print("="*70)
    
except Exception as e:
    print(f"\n❌ 下载失败: {e}\n")
    print("建议:")
    print("  1. 检查网络连接")
    print("  2. 尝试方案 1 (ModelScope)")
    print("  3. 或运行: pip install -U transformers sentence-transformers\n")
    exit(1)
EOF
        
        if [ $? -eq 0 ]; then
            echo ""
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${GREEN}✅ 安装完成！现在可以运行: ./start.sh${NC}"
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        fi
        ;;
        
    3)
        # 方案 3: huggingface-cli
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}方案 3: 使用 huggingface-cli${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        
        # 安装 huggingface_hub
        echo -e "${YELLOW}1. 安装 huggingface-cli...${NC}"
        $PIP_BIN install -q huggingface_hub[cli]
        echo -e "${GREEN}✓ 已安装${NC}"
        echo ""
        
        # 下载模型
        echo -e "${YELLOW}2. 下载模型...${NC}"
        echo ""
        
        export HF_ENDPOINT=https://hf-mirror.com
        $PYTHON_BIN -m huggingface_hub download BAAI/bge-m3 --local-dir ~/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/main
        
        if [ $? -eq 0 ]; then
            echo ""
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${GREEN}✅ 下载完成！${NC}"
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        fi
        ;;
        
    4)
        # 方案 4: wget 手动下载
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}方案 4: wget 手动下载文件${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        
        MODEL_DIR="$HOME/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/main"
        mkdir -p "$MODEL_DIR"
        cd "$MODEL_DIR"
        
        echo -e "${YELLOW}下载模型文件到: $MODEL_DIR${NC}"
        echo ""
        
        BASE_URL="https://hf-mirror.com/BAAI/bge-m3/resolve/main"
        
        FILES=(
            "config.json"
            "tokenizer_config.json"
            "tokenizer.json"
            "special_tokens_map.json"
            "sentence_bert_config.json"
            "modules.json"
            "config_sentence_transformers.json"
            "model.safetensors"
            "pytorch_model.bin"
        )
        
        for file in "${FILES[@]}"; do
            echo -e "${CYAN}下载: $file${NC}"
            wget -q --show-progress "$BASE_URL/$file" -O "$file" || echo -e "${YELLOW}⚠️  $file 下载失败（可能不存在）${NC}"
        done
        
        echo ""
        echo -e "${GREEN}✓ 下载完成！${NC}"
        echo -e "模型路径: $MODEL_DIR"
        ;;
        
    5)
        # 方案 5: 禁用 BGE-M3
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${YELLOW}方案 5: 禁用 BGE-M3（临时方案）${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        
        CONFIG_FILE="./config/config.yaml"
        
        if [ -f "$CONFIG_FILE" ]; then
            # 备份配置
            cp "$CONFIG_FILE" "$CONFIG_FILE.backup"
            echo -e "${GREEN}✓ 已备份配置文件: $CONFIG_FILE.backup${NC}"
            
            # 修改配置
            sed -i '' 's/use_bge_m3: true/use_bge_m3: false/' "$CONFIG_FILE"
            
            echo -e "${GREEN}✓ 已禁用 BGE-M3${NC}"
            echo ""
            echo "配置已更新:"
            echo "  use_bge_m3: true  =>  use_bge_m3: false"
            echo ""
            echo "现在运行 ./start.sh 将使用默认的轻量级模型"
            echo ""
            echo "恢复 BGE-M3:"
            echo "  cp $CONFIG_FILE.backup $CONFIG_FILE"
        else
            echo -e "${RED}❌ 配置文件不存在: $CONFIG_FILE${NC}"
        fi
        ;;
        
    6)
        # 方案 6: 查看状态
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${CYAN}BGE-M3 模型状态检查${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        
        $PYTHON_BIN << 'EOF'
import os
import sys

def check_path(path, name):
    expanded_path = os.path.expanduser(path)
    exists = os.path.exists(expanded_path)
    
    status = "✓" if exists else "✗"
    color = "\033[0;32m" if exists else "\033[0;31m"
    reset = "\033[0m"
    
    print(f"{color}{status}{reset} {name}")
    print(f"  路径: {expanded_path}")
    
    if exists:
        if os.path.isfile(expanded_path):
            size = os.path.getsize(expanded_path)
            print(f"  大小: {size:,} bytes ({size/1024/1024:.2f} MB)")
        elif os.path.isdir(expanded_path):
            files = os.listdir(expanded_path)
            print(f"  文件数: {len(files)}")
            if files:
                print(f"  内容: {', '.join(files[:5])}")
    print()

print("1. HuggingFace 缓存:")
check_path("~/.cache/huggingface/hub/models--BAAI--bge-m3", "HF Cache")

print("2. ModelScope 缓存:")
check_path("~/.cache/modelscope/hub/AI-ModelScope/bge-m3", "ModelScope Cache")

print("3. 配置文件:")
if os.path.exists("./config/config.yaml"):
    with open("./config/config.yaml") as f:
        for line in f:
            if "use_bge_m3" in line:
                print(f"  {line.strip()}")
                break
else:
    print("  ✗ 配置文件不存在")

print("\n4. 依赖检查:")
try:
    import sentence_transformers
    print("  ✓ sentence-transformers 已安装")
except:
    print("  ✗ sentence-transformers 未安装")
    
try:
    import modelscope
    print("  ✓ modelscope 已安装")
except:
    print("  ✗ modelscope 未安装")
EOF
        ;;
        
    *)
        echo -e "${RED}无效选项${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}提示:${NC}"
echo -e "  • 运行程序: ${GREEN}./start.sh${NC}"
echo -e "  • 查看状态: ${GREEN}./manual_download_bge_m3.sh${NC} (选择选项 6)"
echo -e "  • 如遇问题: 查看日志 ${YELLOW}output/kg_builder.log${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
