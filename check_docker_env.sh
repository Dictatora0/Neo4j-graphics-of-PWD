#!/bin/bash

# Docker 环境检查脚本
# 用于验证 Docker 和 docker-compose 是否正确安装和配置

set -e

echo "=================================="
echo "PWD 系统 Docker 环境检查"
echo "=================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查结果统计
PASS=0
FAIL=0

# 检查函数
check() {
    local name=$1
    local cmd=$2
    
    echo -n "检查 $name... "
    if eval $cmd > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 通过${NC}"
        ((PASS++))
        return 0
    else
        echo -e "${RED}✗ 失败${NC}"
        ((FAIL++))
        return 1
    fi
}

# 1. 检查 Docker
echo "1. 检查 Docker 安装"
echo "-------------------"
if check "Docker 命令" "command -v docker"; then
    docker --version
    
    if check "Docker 服务运行" "docker info"; then
        echo "  Docker 服务正常运行"
    else
        echo -e "  ${YELLOW}提示: 请启动 Docker Desktop 或 Docker 守护进程${NC}"
    fi
else
    echo -e "  ${RED}错误: Docker 未安装${NC}"
    echo "  请访问 https://www.docker.com/get-started 安装 Docker"
fi
echo ""

# 2. 检查 Docker Compose
echo "2. 检查 Docker Compose"
echo "---------------------"
if check "Docker Compose 命令" "command -v docker-compose || docker compose version"; then
    docker-compose --version 2>/dev/null || docker compose version
else
    echo -e "  ${RED}错误: Docker Compose 未安装${NC}"
    echo "  Docker Compose 通常随 Docker Desktop 一起安装"
fi
echo ""

# 3. 检查系统资源
echo "3. 检查系统资源"
echo "---------------"

# 检查内存
TOTAL_MEM=$(sysctl -n hw.memsize 2>/dev/null || free -b | awk '/^Mem:/{print $2}')
TOTAL_MEM_GB=$((TOTAL_MEM / 1024 / 1024 / 1024))
echo -n "系统总内存: ${TOTAL_MEM_GB}GB... "
if [ $TOTAL_MEM_GB -ge 4 ]; then
    echo -e "${GREEN}✓ 充足${NC}"
    ((PASS++))
else
    echo -e "${YELLOW}⚠ 建议至少 4GB${NC}"
fi

# 检查磁盘空间
DISK_AVAIL=$(df -h . | awk 'NR==2 {print $4}' | sed 's/G.*//')
echo -n "可用磁盘空间: ${DISK_AVAIL}GB... "
if [ ${DISK_AVAIL%.*} -ge 10 ]; then
    echo -e "${GREEN}✓ 充足${NC}"
    ((PASS++))
else
    echo -e "${YELLOW}⚠ 建议至少 10GB${NC}"
fi
echo ""

# 4. 检查端口占用
echo "4. 检查端口占用"
echo "---------------"
PORTS=(80 3000 5173 7474 7687 8000)
PORT_CONFLICTS=0

for port in "${PORTS[@]}"; do
    echo -n "端口 $port... "
    if lsof -i :$port > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠ 已被占用${NC}"
        lsof -i :$port | tail -n 1
        ((PORT_CONFLICTS++))
    else
        echo -e "${GREEN}✓ 可用${NC}"
        ((PASS++))
    fi
done

if [ $PORT_CONFLICTS -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}提示: 端口被占用时，可以：${NC}"
    echo "  1. 停止占用端口的进程"
    echo "  2. 修改 docker-compose.yml 中的端口映射"
fi
echo ""

# 5. 检查项目文件
echo "5. 检查项目文件"
echo "---------------"
FILES=(
    "docker-compose.yml"
    "Makefile"
    "web/backend/Dockerfile"
    "web/frontend/Dockerfile"
    ".github/workflows/ci.yml"
)

for file in "${FILES[@]}"; do
    check "$file" "test -f $file"
done
echo ""

# 6. 测试 Docker 基础功能
echo "6. 测试 Docker 基础功能"
echo "----------------------"
if check "拉取测试镜像" "docker pull hello-world"; then
    if check "运行测试容器" "docker run --rm hello-world"; then
        echo -e "  ${GREEN}Docker 功能正常${NC}"
    fi
    # 清理测试镜像
    docker rmi hello-world > /dev/null 2>&1 || true
fi
echo ""

# 总结
echo "=================================="
echo "检查结果总结"
echo "=================================="
echo -e "通过: ${GREEN}${PASS}${NC}"
echo -e "失败: ${RED}${FAIL}${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ 所有检查通过！您可以运行 'make quick-start' 启动系统${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ 部分检查未通过，请根据上述提示解决问题${NC}"
    echo ""
    echo "常见解决方案："
    echo "  - Docker 未运行: 启动 Docker Desktop"
    echo "  - 端口被占用: 停止占用端口的服务或修改配置"
    echo "  - 内存不足: 关闭其他应用或增加 Docker 内存限制"
    echo ""
    echo "详细文档: DOCKER_DEPLOYMENT.md"
    exit 1
fi
