#!/bin/bash
################################################################################
# 推送项目到GitHub
# 用途: 快速将项目推送到GitHub，配合Colab使用
################################################################################

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  推送项目到GitHub${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# 检查是否已初始化Git
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}⚠️  未检测到Git仓库，正在初始化...${NC}"
    git init
    echo -e "${GREEN}✓ Git仓库已初始化${NC}"
fi

# 检查是否有远程仓库
if ! git remote | grep -q "origin"; then
    echo -e "\n${YELLOW}请输入您的GitHub仓库地址:${NC}"
    echo -e "${BLUE}例如: https://github.com/YOUR_USERNAME/PWD-Knowledge-Graph.git${NC}"
    read -p "仓库地址: " REPO_URL
    
    git remote add origin "$REPO_URL"
    echo -e "${GREEN}✓ 已添加远程仓库${NC}"
else
    REPO_URL=$(git remote get-url origin)
    echo -e "${GREEN}✓ 远程仓库: $REPO_URL${NC}"
fi

# 显示将要提交的文件
echo -e "\n${BLUE}📁 将要提交的文件:${NC}"
git status --short

# 添加所有文件
echo -e "\n${BLUE}📦 添加文件...${NC}"
git add .

# 提交
echo -e "\n${BLUE}💾 提交更改...${NC}"
COMMIT_MSG="Update: 优化知识图谱构建，支持Colab高质量运行"
git commit -m "$COMMIT_MSG" || echo "没有新的更改需要提交"

# 推送
echo -e "\n${BLUE}🚀 推送到GitHub...${NC}"
git branch -M main
git push -u origin main

echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ 推送完成！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "\n${BLUE}📋 下一步操作:${NC}"
echo -e "1. 上传文献到Google Drive的 ${YELLOW}PWD_文献${NC} 文件夹"
echo -e "2. 上传 ${YELLOW}PWD_KG_Colab_GitHub.ipynb${NC} 到Google Drive"
echo -e "3. 在Colab中打开Notebook"
echo -e "4. 修改 ${YELLOW}GITHUB_REPO${NC} 为: ${GREEN}$REPO_URL${NC}"
echo -e "5. 运行所有单元格\n"

echo -e "${BLUE}📖 详细说明请查看: ${YELLOW}GitHub同步指南.md${NC}\n"
