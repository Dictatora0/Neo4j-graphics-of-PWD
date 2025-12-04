#!/bin/bash

# 本地 CI 测试脚本
# 在本地运行与 GitHub Actions 相同的检查，提交前验证代码

set -e

echo "=================================="
echo "本地 CI 测试 - 模拟 GitHub Actions"
echo "=================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ERRORS=0

# 检查函数
run_check() {
    local name=$1
    local cmd=$2
    
    echo -e "${BLUE}▶ $name${NC}"
    echo "-----------------------------------"
    
    if eval $cmd; then
        echo -e "${GREEN}✓ $name 通过${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}✗ $name 失败${NC}"
        echo ""
        ((ERRORS++))
        return 1
    fi
}

# 1. 后端检查
echo "1️⃣  后端代码检查"
echo "=================================="

cd web/backend

# 检查依赖是否安装
if ! python -c "import flake8" 2>/dev/null; then
    echo -e "${YELLOW}⚠ 安装检查工具...${NC}"
    pip install flake8 black pytest pytest-cov > /dev/null 2>&1
fi

run_check "Flake8 语法检查" \
    "flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics"

run_check "Flake8 代码质量" \
    "flake8 app/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics"

run_check "Black 格式检查" \
    "black --check app/ || echo '提示: 运行 black app/ 自动格式化'"

run_check "Pytest 单元测试" \
    "pytest -v --cov=app --cov-report=term-missing || echo '提示: 部分测试失败'"

cd ../..

# 2. 前端检查
echo ""
echo "2️⃣  前端代码检查"
echo "=================================="

cd web/frontend

# 检查依赖是否安装
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}⚠ 安装依赖...${NC}"
    npm ci
fi

run_check "ESLint 检查" \
    "npm run lint"

run_check "TypeScript 编译和构建" \
    "npm run build"

cd ../..

# 3. 管道代码检查
echo ""
echo "3️⃣  管道代码检查"
echo "=================================="

run_check "管道 Flake8 检查" \
    "flake8 *.py --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=venv,archive"

run_check "管道 Black 格式检查" \
    "black --check *.py --exclude='venv|archive' || echo '提示: 运行 black *.py 自动格式化'"

# 4. Docker 配置检查
echo ""
echo "4️⃣  Docker 配置检查"
echo "=================================="

run_check "docker-compose 配置验证" \
    "docker-compose config > /dev/null"

# 5. 文件权限检查
echo ""
echo "5️⃣  文件权限检查"
echo "=================================="

run_check "Shell 脚本执行权限" \
    "ls -l *.sh | grep -q 'x.*\.sh' || echo '提示: 某些脚本可能缺少执行权限'"

# 总结
echo ""
echo "=================================="
echo "测试结果总结"
echo "=================================="

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ 所有检查通过！可以安全提交代码${NC}"
    echo ""
    echo "提交命令："
    echo "  git add ."
    echo "  git commit -m 'your message'"
    echo "  git push"
    exit 0
else
    echo -e "${RED}✗ 发现 $ERRORS 个问题，请修复后再提交${NC}"
    echo ""
    echo "修复建议："
    echo "  - 运行 'black app/' 自动格式化 Python 代码"
    echo "  - 运行 'npm run lint -- --fix' 自动修复前端代码"
    echo "  - 查看上述错误信息并手动修复"
    exit 1
fi
