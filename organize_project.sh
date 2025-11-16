#!/bin/bash
# 项目文件整理脚本
# 将开发过程中的临时脚本和文档移到 archive/ 目录

set -e

echo "=========================================="
echo "开始整理项目文件"
echo "=========================================="

# 创建 archive 子目录
mkdir -p archive/scripts
mkdir -p archive/docs

echo ""
echo "1. 移动调试/临时分析脚本到 archive/scripts/"
echo "=========================================="

# 调试脚本
for file in check_ollama.py debug_json_parsing.py debug_llm.py debug_orphaned_hosts.py inspect_database.py interactive_kg_review.py visualize_graph.py show_core_graph.py; do
    if [ -f "$file" ]; then
        echo "  移动: $file"
        git mv "$file" archive/scripts/ 2>/dev/null || echo "    (跳过: 可能已不存在或未追踪)"
    fi
done

echo ""
echo "2. 移动早期/中间版本的清洗脚本到 archive/scripts/"
echo "=========================================="

# 早期清洗脚本
for file in apply_final_merges.py apply_semantic_fixes.py clean_and_optimize_kg.py comprehensive_fix.py comprehensive_query.py deep_semantic_analysis.py detect_issues.py final_cleanup.py final_data_cleanup.py final_polish.py final_relation_standardization.py final_semantic_polish.py final_verification.py fix_critical_issues.py fix_detected_issues.py fix_semantic_issues.py fix_semantic_logic.py import_graph_direct.py reimport_cleaned_graph.py reimport_final_graph.py review_remaining_candidates.py semantic_sanity_check.py standardize_all_relations.py ultimate_cleanup.py ultimate_fix.py verify_neo4j.py; do
    if [ -f "$file" ]; then
        echo "  移动: $file"
        git mv "$file" archive/scripts/ 2>/dev/null || echo "    (跳过: 可能已不存在或未追踪)"
    fi
done

echo ""
echo "3. 移动旧文档到 archive/docs/"
echo "=========================================="

# 旧文档
for file in CHANGES_SUMMARY.md IMPROVEMENTS.md IMPROVEMENTS_IMPLEMENTED.md SPEED_OPTIMIZATION.md REPAIR_SUMMARY.txt; do
    if [ -f "$file" ]; then
        echo "  移动: $file"
        git mv "$file" archive/docs/ 2>/dev/null || echo "    (跳过: 可能已不存在或未追踪)"
    fi
done

echo ""
echo "4. 移动 output 下的大型报告到 archive/docs/"
echo "=========================================="

# output 下的报告
for file in output/COMPREHENSIVE_CHECK_REPORT.md output/DATABASE_CLEANING_REPORT.md output/FINAL_CLEANING_REPORT.md output/FINAL_DATA_CHECK_REPORT.md output/IMPORT_SUMMARY.md output/ULTRA_FINAL_REPORT.md; do
    if [ -f "$file" ]; then
        echo "  移动: $file"
        git mv "$file" archive/docs/ 2>/dev/null || echo "    (跳过: 可能已不存在或未追踪)"
    fi
done

echo ""
echo "5. 移动 monitor_errors.sh 到 archive/scripts/"
echo "=========================================="

if [ -f "monitor_errors.sh" ]; then
    echo "  移动: monitor_errors.sh"
    git mv monitor_errors.sh archive/scripts/ 2>/dev/null || echo "    (跳过: 可能已不存在或未追踪)"
fi

echo ""
echo "=========================================="
echo "文件整理完成。"
echo "=========================================="
echo ""
echo "已创建的目录结构:"
echo "  archive/"
echo "  ├── scripts/  (调试和中间版本脚本)"
echo "  └── docs/     (旧文档和报告)"
echo ""
echo "核心文件保留在项目根目录:"
echo "  - main.py"
echo "  - bio_semantic_review.py"
echo "  - import_to_neo4j_final.py"
echo "  - export_neo4j_to_csv.py"
echo "  - verify_neo4j_data.py"
echo "  - fix_semantic_triples.py"
echo "  - refine_node_labels.py"
echo "  - fix_remaining_relations.py"
echo "  - README.md (已更新)"
echo ""
echo "下一步: git status 查看变更，然后 git commit"
