#!/bin/bash

# 知识图谱系统改进功能静态验证脚本
# 不需要安装依赖，仅检查代码实现

echo "=========================================="
echo "  知识图谱系统改进功能静态验证"
echo "  验证时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo

PASSED=0
FAILED=0

# 测试函数
test_feature() {
    local feature_name="$1"
    local test_command="$2"
    
    echo "[$((PASSED + FAILED + 1))] 测试: $feature_name"
    
    if eval "$test_command"; then
        echo "   通过"
        ((PASSED++))
    else
        echo "   失败"
        ((FAILED++))
    fi
    echo
}

echo "=========================================="
echo "  第二阶段改进验证"
echo "=========================================="
echo

# 1. 实体消歧与链接
test_feature "CanonicalResolver 类定义" \
    "grep -q 'class CanonicalResolver:' concept_deduplicator.py"

test_feature "内置生物分类学映射" \
    "grep -q 'BIOLOGICAL_CANONICAL_NAMES' concept_deduplicator.py"

test_feature "resolve 方法实现" \
    "grep -q 'def resolve(self, entity: str' concept_deduplicator.py"

test_feature "NCBI Taxonomy 查询" \
    "grep -q 'def _query_ncbi_taxonomy' concept_deduplicator.py"

test_feature "Wikidata 查询" \
    "grep -q 'def _query_wikidata' concept_deduplicator.py"

test_feature "CanonicalResolver 集成到去重" \
    "grep -q 'self.canonical_resolver' concept_deduplicator.py"

# 2. 多模态深度融合
test_feature "MultimodalGraphBuilder 文件存在" \
    "test -f multimodal_graph_builder.py"

test_feature "MultimodalGraphBuilder 类定义" \
    "grep -q 'class MultimodalGraphBuilder:' multimodal_graph_builder.py"

test_feature "load_image_captions 方法" \
    "grep -q 'def load_image_captions' multimodal_graph_builder.py"

test_feature "build_image_concept_relationships 方法" \
    "grep -q 'def build_image_concept_relationships' multimodal_graph_builder.py"

test_feature "MultimodalRetriever 类定义" \
    "grep -q 'class MultimodalRetriever:' multimodal_graph_builder.py"

test_feature "retrieve_images_for_concepts 方法" \
    "grep -q 'def retrieve_images_for_concepts' multimodal_graph_builder.py"

# 3. 人机回环纠错
test_feature "HumanFeedbackManager 文件存在" \
    "test -f human_feedback_manager.py"

test_feature "FeedbackType 枚举定义" \
    "grep -q 'class FeedbackType:' human_feedback_manager.py"

test_feature "HumanFeedbackManager 类定义" \
    "grep -q 'class HumanFeedbackManager:' human_feedback_manager.py"

test_feature "record_relation_direction_error 方法" \
    "grep -q 'def record_relation_direction_error' human_feedback_manager.py"

test_feature "generate_feedback_report 方法" \
    "grep -q 'def generate_feedback_report' human_feedback_manager.py"

test_feature "export_training_data 方法" \
    "grep -q 'def export_training_data' human_feedback_manager.py"

# 4. Web API
test_feature "Feedback API 路由文件" \
    "test -f web/backend/app/routers/feedback.py"

test_feature "Multimodal API 路由文件" \
    "test -f web/backend/app/routers/multimodal.py"

echo "=========================================="
echo "  第一阶段改进验证"
echo "=========================================="
echo

# 5. 滑动窗口上下文机制
test_feature "context_window 参数支持" \
    "grep -q 'use_context_window' concept_extractor.py"

test_feature "context_window_size 参数支持" \
    "grep -q 'context_window_size' concept_extractor.py"

test_feature "context_entities 上下文列表" \
    "grep -q 'context_entities' concept_extractor.py"

test_feature "上下文提示生成" \
    "grep -q '前文提到的核心实体' concept_extractor.py"

# 6. 层级本体 Label
test_feature "type_hierarchy 定义" \
    "grep -q 'type_hierarchy' import_to_neo4j_final.py"

test_feature "多 Label 节点创建" \
    "grep -q 'labels_str' import_to_neo4j_final.py"

test_feature "primary_label 属性" \
    "grep -q 'primary_label' import_to_neo4j_final.py"

test_feature "all_labels 属性" \
    "grep -q 'all_labels' import_to_neo4j_final.py"

# 7. Local Search 功能
test_feature "LocalSearchEngine 类定义" \
    "grep -q 'class LocalSearchEngine:' graph_rag.py"

test_feature "build_node_index 方法" \
    "grep -q 'def build_node_index' graph_rag.py"

test_feature "search_relevant_nodes 方法" \
    "grep -q 'def search_relevant_nodes' graph_rag.py"

test_feature "expand_subgraph 方法" \
    "grep -q 'def expand_subgraph' graph_rag.py"

test_feature "answer_query 方法" \
    "grep -q 'def answer_query' graph_rag.py"

test_feature "GraphRAG local_search 集成" \
    "grep -q 'def local_search' graph_rag.py"

echo "=========================================="
echo "  配置文件验证"
echo "=========================================="
echo

# 8. 配置文件
test_feature "improvements 配置节存在" \
    "grep -q 'improvements:' config/config.yaml"

test_feature "context_window 配置" \
    "grep -q 'context_window:' config/config.yaml"

test_feature "hierarchical_ontology 配置" \
    "grep -q 'hierarchical_ontology:' config/config.yaml"

test_feature "local_search 配置" \
    "grep -q 'local_search:' config/config.yaml"

test_feature "improvements_phase2 配置节存在" \
    "grep -q 'improvements_phase2:' config/config.yaml"

test_feature "entity_linking 配置" \
    "grep -q 'entity_linking:' config/config.yaml"

test_feature "use_external_kb 配置" \
    "grep -q 'use_external_kb:' config/config.yaml"

test_feature "multimodal 配置" \
    "grep -q 'multimodal:' config/config.yaml"

test_feature "human_feedback 配置" \
    "grep -q 'human_feedback:' config/config.yaml"

echo "=========================================="
echo "  文档验证"
echo "=========================================="
echo

# 9. 文档
test_feature "README 包含最新改进说明" \
    "grep -q '最新改进' README.md"

test_feature "README 包含滑动窗口说明" \
    "grep -q '滑动窗口上下文机制' README.md"

test_feature "README 包含实体消歧说明" \
    "grep -q '实体消歧与链接' README.md"

test_feature "README 包含多模态说明" \
    "grep -q '多模态深度融合' README.md"

test_feature "README 包含人机回环说明" \
    "grep -q '人机回环纠错' README.md"

test_feature "Local Search 示例文件存在" \
    "test -f examples/local_search_demo.py"

echo "=========================================="
echo "  验证结果汇总"
echo "=========================================="
echo
echo "  通过: $PASSED"
echo "  失败: $FAILED"
echo "  总计: $((PASSED + FAILED))"
echo
echo "=========================================="

if [ $FAILED -eq 0 ]; then
    echo "  所有验证通过"
    echo "=========================================="
    exit 0
else
    echo "  有 $FAILED 项验证失败"
    echo "=========================================="
    exit 1
fi
