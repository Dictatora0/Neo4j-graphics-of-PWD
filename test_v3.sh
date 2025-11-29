#!/bin/bash
# v3.0.0 功能测试脚本

echo "============================================================"
echo "🧪 v3.0.0 全功能集成测试"
echo "============================================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SUCCESS_COUNT=0
TOTAL_COUNT=0

# 测试函数
test_item() {
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓${NC} $1"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "${RED}  ✗${NC} $1"
    fi
}

# 测试 1: Git 版本
echo -e "${BLUE}[测试 1/6] Git 版本信息${NC}"
git describe --tags 2>/dev/null
test_item "Git 标签"

CURRENT_TAG=$(git describe --tags --abbrev=0 2>/dev/null)
if [ "$CURRENT_TAG" = "v3.0.0" ]; then
    echo -e "${GREEN}  ✓${NC} 当前版本: v3.0.0"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo -e "${YELLOW}  ⚠${NC} 当前版本: $CURRENT_TAG (预期 v3.0.0)"
fi
TOTAL_COUNT=$((TOTAL_COUNT + 1))
echo ""

# 测试 2: 关键文件
echo -e "${BLUE}[测试 2/6] 关键文件完整性${NC}"
FILES=(
    "concept_extractor.py:LLM抽取"
    "concept_deduplicator.py:BGE-M3去重"
    "image_captioner.py:图片描述"
    "graph_summarizer.py:GraphRAG"
    "bio_semantic_review.py:LLM审查"
    "config/config.yaml:配置"
    "CHANGELOG.md:更新日志"
    "enhanced_pipeline.py:Pipeline"
)

for item in "${FILES[@]}"; do
    IFS=':' read -r file desc <<< "$item"
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    if [ -f "$file" ]; then
        echo -e "${GREEN}  ✓${NC} $file ($desc)"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "${RED}  ✗${NC} $file 缺失"
    fi
done
echo ""

# 测试 3: 配置文件内容
echo -e "${BLUE}[测试 3/6] 配置文件检查${NC}"
if grep -q "qwen2.5-coder:14b" config/config.yaml; then
    echo -e "${GREEN}  ✓${NC} Qwen 模型配置"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo -e "${RED}  ✗${NC} Qwen 模型配置缺失"
fi
TOTAL_COUNT=$((TOTAL_COUNT + 1))

if grep -q "enable_image_captions" config/config.yaml; then
    echo -e "${GREEN}  ✓${NC} 图片描述配置"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo -e "${RED}  ✗${NC} 图片描述配置缺失"
fi
TOTAL_COUNT=$((TOTAL_COUNT + 1))

if grep -q "use_bge_m3" config/config.yaml; then
    echo -e "${GREEN}  ✓${NC} BGE-M3 配置"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo -e "${RED}  ✗${NC} BGE-M3 配置缺失"
fi
TOTAL_COUNT=$((TOTAL_COUNT + 1))

if grep -q "enable_llm_review" config/config.yaml; then
    echo -e "${GREEN}  ✓${NC} LLM 审查配置"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo -e "${RED}  ✗${NC} LLM 审查配置缺失"
fi
TOTAL_COUNT=$((TOTAL_COUNT + 1))

if grep -q "enable_graph_rag" config/config.yaml; then
    echo -e "${GREEN}  ✓${NC} GraphRAG 配置"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo -e "${RED}  ✗${NC} GraphRAG 配置缺失"
fi
TOTAL_COUNT=$((TOTAL_COUNT + 1))
echo ""

# 测试 4: Python 语法
echo -e "${BLUE}[测试 4/6] Python 语法检查${NC}"
PYTHON_FILES=(
    "concept_extractor.py"
    "concept_deduplicator.py"
    "image_captioner.py"
    "graph_summarizer.py"
    "bio_semantic_review.py"
)

for file in "${PYTHON_FILES[@]}"; do
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    if python3 -m py_compile "$file" 2>/dev/null; then
        echo -e "${GREEN}  ✓${NC} $file 语法正确"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "${RED}  ✗${NC} $file 语法错误"
    fi
done
echo ""

# 测试 5: Ollama 服务
echo -e "${BLUE}[测试 5/6] Ollama 服务${NC}"
TOTAL_COUNT=$((TOTAL_COUNT + 1))
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}  ✓${NC} Ollama 服务运行中"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    
    # 检查 Qwen 模型
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    if curl -s http://localhost:11434/api/tags | grep -q "qwen"; then
        echo -e "${GREEN}  ✓${NC} Qwen 模型已安装"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "${YELLOW}  ⚠${NC} Qwen 模型未安装（可选）"
    fi
else
    echo -e "${YELLOW}  ⚠${NC} Ollama 未运行（测试时需要）"
fi
echo ""

# 测试 6: 文档完整性
echo -e "${BLUE}[测试 6/6] 文档完整性${NC}"
DOCS=(
    "CHANGELOG.md:更新日志"
    "QUICKSTART_QWEN.md:快速开始"
    "docs/MODEL_UPGRADE.md:模型升级"
    "docs/MERGE_GUIDE.md:合并指南"
)

for item in "${DOCS[@]}"; do
    IFS=':' read -r file desc <<< "$item"
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    if [ -f "$file" ]; then
        echo -e "${GREEN}  ✓${NC} $file ($desc)"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "${YELLOW}  ⚠${NC} $file 缺失（非必需）"
    fi
done
echo ""

# 总结
echo "============================================================"
PASS_RATE=$((SUCCESS_COUNT * 100 / TOTAL_COUNT))
if [ $PASS_RATE -ge 80 ]; then
    echo -e "${GREEN}✅ 测试通过: $SUCCESS_COUNT/$TOTAL_COUNT ($PASS_RATE%)${NC}"
elif [ $PASS_RATE -ge 60 ]; then
    echo -e "${YELLOW}⚠️  部分通过: $SUCCESS_COUNT/$TOTAL_COUNT ($PASS_RATE%)${NC}"
else
    echo -e "${RED}❌ 测试失败: $SUCCESS_COUNT/$TOTAL_COUNT ($PASS_RATE%)${NC}"
fi
echo "============================================================"
echo ""

# 建议
echo -e "${BLUE}💡 后续建议:${NC}"
if [ $PASS_RATE -ge 80 ]; then
    echo "  1. 安装依赖: pip install -r requirements.txt"
    echo "  2. 下载模型: ollama pull qwen2.5-coder:14b"
    echo "  3. 运行测试: python3 enhanced_pipeline.py --max-chunks 3"
else
    echo "  1. 检查缺失的文件"
    echo "  2. 重新拉取代码: git pull origin main"
    echo "  3. 重新运行测试: ./test_v3.sh"
fi
echo ""

# 版本信息
echo -e "${BLUE}📦 版本信息:${NC}"
echo "  当前分支: $(git branch --show-current)"
echo "  最新提交: $(git log -1 --pretty=format:'%h %s')"
echo "  发布标签: $(git tag --list 'v*' | tail -5 | tr '\n' ' ')"
echo ""

exit 0
