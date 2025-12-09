#!/bin/bash
# 验证改进功能的代码改动

echo "================================================================================"
echo "知识图谱改进功能验证"
echo "================================================================================"

cd "$(dirname "$0")/.."

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数
PASSED=0
FAILED=0

echo ""
echo "================================================================================"
echo "测试 1: 滑动窗口上下文机制"
echo "================================================================================"

# 检查 concept_extractor.py 中的改动
if grep -q "use_context_window" concept_extractor.py && \
   grep -q "context_window_size" concept_extractor.py && \
   grep -q "context_entities" concept_extractor.py; then
    echo -e "${GREEN}滑动窗口参数已添加${NC}"
    ((PASSED++))
else
    echo -e "${RED}滑动窗口参数未找到${NC}"
    ((FAILED++))
fi

if grep -q "前文提到的核心实体" concept_extractor.py; then
    echo -e "${GREEN}上下文提示已集成${NC}"
    ((PASSED++))
else
    echo -e "${RED}上下文提示未找到${NC}"
    ((FAILED++))
fi

if grep -q "context_hint" concept_extractor.py; then
    echo -e "${GREEN}context_hint 参数已添加${NC}"
    ((PASSED++))
else
    echo -e "${RED}context_hint 参数未找到${NC}"
    ((FAILED++))
fi

echo ""
echo "================================================================================"
echo "测试 2: 层级本体 Label"
echo "================================================================================"

# 检查 import_to_neo4j_final.py 中的改动
if grep -q "type_hierarchy" import_to_neo4j_final.py; then
    echo -e "${GREEN}层级本体定义已添加${NC}"
    ((PASSED++))
else
    echo -e "${RED}层级本体定义未找到${NC}"
    ((FAILED++))
fi

if grep -q "Organism" import_to_neo4j_final.py && \
   grep -q "Plant" import_to_neo4j_final.py && \
   grep -q "Animal" import_to_neo4j_final.py; then
    echo -e "${GREEN}本体类型已定义${NC}"
    ((PASSED++))
else
    echo -e "${RED}本体类型未完整定义${NC}"
    ((FAILED++))
fi

if grep -q "primary_label" import_to_neo4j_final.py && \
   grep -q "all_labels" import_to_neo4j_final.py; then
    echo -e "${GREEN}Label 属性已添加${NC}"
    ((PASSED++))
else
    echo -e "${RED}Label 属性未找到${NC}"
    ((FAILED++))
fi

if grep -q "查询所有生物" import_to_neo4j_final.py; then
    echo -e "${GREEN}层级查询示例已添加${NC}"
    ((PASSED++))
else
    echo -e "${RED}层级查询示例未找到${NC}"
    ((FAILED++))
fi

echo ""
echo "================================================================================"
echo "测试 3: Local Search 功能"
echo "================================================================================"

# 检查 graph_rag.py 中的改动
if grep -q "class LocalSearchEngine" graph_rag.py; then
    echo -e "${GREEN}LocalSearchEngine 类已定义${NC}"
    ((PASSED++))
else
    echo -e "${RED}LocalSearchEngine 类未找到${NC}"
    ((FAILED++))
fi

if grep -q "build_node_index" graph_rag.py && \
   grep -q "search_relevant_nodes" graph_rag.py && \
   grep -q "expand_subgraph" graph_rag.py; then
    echo -e "${GREEN}Local Search 核心方法已实现${NC}"
    ((PASSED++))
else
    echo -e "${RED}Local Search 核心方法未完整${NC}"
    ((FAILED++))
fi

if grep -q "def local_search" graph_rag.py; then
    echo -e "${GREEN}GraphRAG.local_search 方法已添加${NC}"
    ((PASSED++))
else
    echo -e "${RED}GraphRAG.local_search 方法未找到${NC}"
    ((FAILED++))
fi

if grep -q "BGEM3FlagModel" graph_rag.py; then
    echo -e "${GREEN}BGE-M3 Embedding 已集成${NC}"
    ((PASSED++))
else
    echo -e "${RED}BGE-M3 Embedding 未集成${NC}"
    ((FAILED++))
fi

echo ""
echo "================================================================================"
echo "测试 4: 配置文件更新"
echo "================================================================================"

# 检查配置文件
if grep -q "improvements:" config/config.yaml; then
    echo -e "${GREEN}改进配置段已添加${NC}"
    ((PASSED++))
else
    echo -e "${RED}改进配置段未找到${NC}"
    ((FAILED++))
fi

if grep -q "context_window:" config/config.yaml && \
   grep -q "hierarchical_ontology:" config/config.yaml && \
   grep -q "local_search:" config/config.yaml; then
    echo -e "${GREEN}三个改进的配置项已添加${NC}"
    ((PASSED++))
else
    echo -e "${RED}配置项不完整${NC}"
    ((FAILED++))
fi

echo ""
echo "================================================================================"
echo "测试 5: 文档更新"
echo "================================================================================"

# 检查文档
if [ -f "docs/IMPROVEMENTS_2024.md" ]; then
    echo -e "${GREEN}改进说明文档已创建${NC}"
    ((PASSED++))
else
    echo -e "${RED}改进说明文档未找到${NC}"
    ((FAILED++))
fi

if [ -f "examples/local_search_demo.py" ]; then
    echo -e "${GREEN}Local Search 示例已创建${NC}"
    ((PASSED++))
else
    echo -e "${RED}Local Search 示例未找到${NC}"
    ((FAILED++))
fi

if grep -q "最新改进" README.md; then
    echo -e "${GREEN}README 已更新${NC}"
    ((PASSED++))
else
    echo -e "${RED}README 未更新${NC}"
    ((FAILED++))
fi

echo ""
echo "================================================================================"
echo "测试结果汇总"
echo "================================================================================"
echo -e "通过: ${GREEN}${PASSED}${NC} 项"
echo -e "失败: ${RED}${FAILED}${NC} 项"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}所有改进功能验证通过${NC}"
    echo ""
    echo "下一步操作："
    echo "  1. 安装依赖: pip install -r requirements.txt"
    echo "  2. 运行完整流程: ./start.sh"
    echo "  3. 导入 Neo4j: python import_to_neo4j_final.py"
    echo "  4. 测试 Local Search: python examples/local_search_demo.py"
    echo ""
    echo "详细文档："
    echo "  - 改进说明: docs/IMPROVEMENTS_2024.md"
    echo "  - 使用示例: examples/local_search_demo.py"
    exit 0
else
    echo -e "${RED}部分功能验证失败${NC}"
    exit 1
fi
