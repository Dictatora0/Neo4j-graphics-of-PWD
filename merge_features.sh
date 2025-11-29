#!/bin/bash
# 多功能分支自动合并脚本
# 使用方法: ./merge_features.sh

set -e  # 遇到错误立即退出

echo "=================================================="
echo "🚀 知识图谱项目 v2.0 功能分支合并"
echo "=================================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 功能分支列表（按依赖顺序）
BRANCHES=(
    "feature/smart-parser:Layout-Aware 文档解析优化 (成员 C)"
    "feature/llm-upgrade:LLM 推理升级 (成员 A)"
    "feature/bge-embedding:Embedding 升级 (成员 E)"
    "feature/multimodal:多模态图片提取 (成员 B)"
    "feature/agent-logic:Agentic Workflow (成员 D)"
)

# 记录成功和失败的分支
SUCCESS_BRANCHES=()
FAILED_BRANCHES=()

# 备份当前状态
backup_current_state() {
    echo -e "${BLUE}📦 创建备份点...${NC}"
    BACKUP_TAG="backup-before-v2-merge-$(date +%Y%m%d-%H%M%S)"
    git tag $BACKUP_TAG
    echo -e "${GREEN}✓ 备份标签已创建: $BACKUP_TAG${NC}"
    echo "  如需回滚，运行: git reset --hard $BACKUP_TAG"
    echo ""
}

# 检查分支是否存在
check_branch_exists() {
    local branch=$1
    if git show-ref --verify --quiet refs/remotes/origin/$branch; then
        return 0
    else
        return 1
    fi
}

# 运行测试
run_tests() {
    local branch_name=$1
    echo -e "${BLUE}🧪 运行测试...${NC}"
    
    # 简单的语法检查
    if python3 -c "import sys; sys.path.insert(0, 'scripts/utils'); import config_loader" 2>/dev/null; then
        echo -e "${GREEN}✓ Python 导入测试通过${NC}"
    else
        echo -e "${YELLOW}⚠ Python 导入测试失败（可能需要安装依赖）${NC}"
        return 1
    fi
    
    # 检查关键文件是否存在
    if [ -f "enhanced_pipeline.py" ] && [ -f "concept_extractor.py" ]; then
        echo -e "${GREEN}✓ 关键文件检查通过${NC}"
    else
        echo -e "${RED}✗ 关键文件缺失${NC}"
        return 1
    fi
    
    return 0
}

# 合并单个分支
merge_branch() {
    local branch_desc=$1
    local branch=$(echo $branch_desc | cut -d':' -f1)
    local desc=$(echo $branch_desc | cut -d':' -f2)
    
    echo ""
    echo "=================================================="
    echo -e "${BLUE}📦 准备合并: $branch${NC}"
    echo -e "   描述: $desc"
    echo "=================================================="
    
    # 检查分支是否存在
    if ! check_branch_exists $branch; then
        echo -e "${YELLOW}⚠️  分支 $branch 不存在于远程仓库，跳过${NC}"
        FAILED_BRANCHES+=("$branch (不存在)")
        return 0
    fi
    
    # 获取最新的远程分支
    echo -e "${BLUE}📥 获取远程分支 $branch...${NC}"
    git fetch origin $branch
    
    # 尝试合并
    echo -e "${BLUE}🔀 合并 $branch 到 main...${NC}"
    if git merge origin/$branch --no-ff -m "Merge: $desc" 2>&1; then
        echo -e "${GREEN}✓ $branch 合并成功${NC}"
        
        # 运行测试
        if run_tests $branch; then
            echo -e "${GREEN}✓ 测试通过${NC}"
            SUCCESS_BRANCHES+=("$branch")
            
            # 提交合并后的文档更新
            if [ -d "docs" ]; then
                git add docs/ 2>/dev/null || true
                git commit --amend --no-edit 2>/dev/null || true
            fi
        else
            echo -e "${YELLOW}⚠️  测试未完全通过，但合并已完成${NC}"
            SUCCESS_BRANCHES+=("$branch (测试警告)")
        fi
    else
        echo -e "${RED}❌ 合并失败，检测到冲突${NC}"
        echo ""
        echo "🔧 冲突文件列表:"
        git status --short | grep "^UU"
        echo ""
        echo "请手动解决冲突后运行:"
        echo "  1. 编辑冲突文件"
        echo "  2. git add <冲突文件>"
        echo "  3. git commit"
        echo "  4. ./merge_features.sh  # 继续合并剩余分支"
        echo ""
        FAILED_BRANCHES+=("$branch (冲突)")
        return 1
    fi
}

# 主流程
main() {
    echo -e "${BLUE}1️⃣  准备工作${NC}"
    echo "   当前分支: $(git branch --show-current)"
    echo "   Git 用户: $(git config user.name) <$(git config user.email)>"
    echo ""
    
    # 确保在 main 分支
    if [ "$(git branch --show-current)" != "main" ]; then
        echo -e "${BLUE}切换到 main 分支...${NC}"
        git checkout main
    fi
    
    # 拉取最新的 main
    echo -e "${BLUE}📥 拉取最新的 main 分支...${NC}"
    git pull origin main 2>/dev/null || echo -e "${YELLOW}⚠️  无法拉取（可能网络问题），使用本地版本${NC}"
    echo ""
    
    # 创建备份
    backup_current_state
    
    # 逐个合并分支
    echo -e "${BLUE}2️⃣  开始合并功能分支${NC}"
    echo ""
    
    for branch_desc in "${BRANCHES[@]}"; do
        if ! merge_branch "$branch_desc"; then
            echo ""
            echo -e "${RED}⛔ 合并流程中断${NC}"
            echo -e "   已成功合并: ${#SUCCESS_BRANCHES[@]} 个分支"
            echo -e "   失败/跳过: ${#FAILED_BRANCHES[@]} 个分支"
            exit 1
        fi
    done
    
    # 总结
    echo ""
    echo "=================================================="
    echo -e "${GREEN}🎉 合并流程完成！${NC}"
    echo "=================================================="
    echo ""
    echo -e "${GREEN}✓ 成功合并的分支:${NC}"
    for branch in "${SUCCESS_BRANCHES[@]}"; do
        echo "   - $branch"
    done
    
    if [ ${#FAILED_BRANCHES[@]} -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}⚠️  跳过的分支:${NC}"
        for branch in "${FAILED_BRANCHES[@]}"; do
            echo "   - $branch"
        done
    fi
    
    echo ""
    echo -e "${BLUE}3️⃣  后续步骤${NC}"
    echo "   1. 验证功能: python enhanced_pipeline.py --max-chunks 5"
    echo "   2. 推送到远程: git push origin main"
    echo "   3. 创建发布标签: git tag v2.0.0 && git push origin v2.0.0"
    echo ""
    
    # 询问是否推送
    read -p "是否现在推送到远程仓库? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}📤 推送到远程...${NC}"
        if git push origin main; then
            echo -e "${GREEN}✓ 推送成功${NC}"
            
            # 创建版本标签
            read -p "是否创建 v2.0.0 标签? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                git tag v2.0.0 -m "Release v2.0.0 - 全功能升级"
                git push origin v2.0.0
                echo -e "${GREEN}✓ 标签 v2.0.0 已创建并推送${NC}"
            fi
        else
            echo -e "${RED}✗ 推送失败${NC}"
        fi
    fi
    
    echo ""
    echo -e "${GREEN}✅ 全部完成！${NC}"
}

# 运行主流程
main

exit 0
