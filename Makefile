# Pine Wilt Disease Knowledge Graph System - Makefile
# 统一管理整个项目的生命周期

.PHONY: help build up down restart logs status clean clean-all test lint format install-dev

# 默认目标：显示帮助信息
help:
	@echo "=================================================="
	@echo "PWD 知识图谱系统 - 项目管理命令"
	@echo "=================================================="
	@echo ""
	@echo "Docker 容器管理:"
	@echo "  make build          - 构建所有 Docker 镜像"
	@echo "  make up             - 启动所有服务（生产模式）"
	@echo "  make up-dev         - 启动所有服务（开发模式，包含前端热重载）"
	@echo "  make down           - 停止所有服务"
	@echo "  make restart        - 重启所有服务"
	@echo "  make logs           - 查看所有服务日志"
	@echo "  make logs-backend   - 查看后端日志"
	@echo "  make logs-frontend  - 查看前端日志"
	@echo "  make logs-neo4j     - 查看 Neo4j 日志"
	@echo "  make status         - 查看服务状态"
	@echo ""
	@echo "服务控制:"
	@echo "  make start-neo4j    - 单独启动 Neo4j"
	@echo "  make start-backend  - 单独启动后端"
	@echo "  make start-frontend - 单独启动前端"
	@echo "  make stop-neo4j     - 单独停止 Neo4j"
	@echo "  make stop-backend   - 单独停止后端"
	@echo "  make stop-frontend  - 单独停止前端"
	@echo ""
	@echo "数据处理管道:"
	@echo "  make pipeline       - 运行知识图谱构建管道"
	@echo "  make import-neo4j   - 导入数据到 Neo4j"
	@echo "  make clear-neo4j    - 清空 Neo4j 数据库"
	@echo ""
	@echo "开发工具:"
	@echo "  make test           - 运行所有测试"
	@echo "  make test-backend   - 运行后端测试"
	@echo "  make test-frontend  - 运行前端测试"
	@echo "  make lint           - 运行代码检查"
	@echo "  make format         - 格式化代码"
	@echo "  make install-dev    - 安装开发依赖"
	@echo ""
	@echo "清理命令:"
	@echo "  make clean          - 清理临时文件和缓存"
	@echo "  make clean-all      - 清理所有内容（包括 Docker 卷和输出）"
	@echo "  make prune          - 清理未使用的 Docker 资源"
	@echo ""

# ============================================================
# Docker 容器管理
# ============================================================

# 构建所有 Docker 镜像
build:
	@echo "🔨 构建 Docker 镜像..."
	docker-compose build --parallel

# 启动所有服务（生产模式）
up:
	@echo "🚀 启动所有服务（生产模式）..."
	docker-compose up -d
	@echo "✅ 服务已启动！"
	@echo "   - 前端: http://localhost"
	@echo "   - 后端 API: http://localhost:8000"
	@echo "   - Neo4j Browser: http://localhost:7474"
	@make status

# 启动所有服务（开发模式，包含前端热重载）
up-dev:
	@echo "🚀 启动所有服务（开发模式）..."
	docker-compose --profile dev up -d
	@echo "✅ 服务已启动！"
	@echo "   - 前端（开发）: http://localhost:5173"
	@echo "   - 后端 API: http://localhost:8000"
	@echo "   - Neo4j Browser: http://localhost:7474"
	@make status

# 停止所有服务
down:
	@echo "🛑 停止所有服务..."
	docker-compose --profile dev down
	@echo "✅ 所有服务已停止"

# 重启所有服务
restart:
	@echo "🔄 重启所有服务..."
	@make down
	@make up

# 查看所有服务日志
logs:
	docker-compose logs -f --tail=100

# 查看后端日志
logs-backend:
	docker-compose logs -f --tail=100 backend

# 查看前端日志
logs-frontend:
	docker-compose logs -f --tail=100 frontend

# 查看 Neo4j 日志
logs-neo4j:
	docker-compose logs -f --tail=100 neo4j

# 查看服务状态
status:
	@echo "📊 服务状态:"
	@docker-compose ps

# ============================================================
# 单独服务控制
# ============================================================

start-neo4j:
	docker-compose up -d neo4j

start-backend:
	docker-compose up -d backend

start-frontend:
	docker-compose up -d frontend

stop-neo4j:
	docker-compose stop neo4j

stop-backend:
	docker-compose stop backend

stop-frontend:
	docker-compose stop frontend

# ============================================================
# 数据处理管道
# ============================================================

# 运行知识图谱构建管道
pipeline:
	@echo "⚙️  运行知识图谱构建管道..."
	python main.py

# 导入数据到 Neo4j
import-neo4j:
	@echo "📥 导入数据到 Neo4j..."
	python import_to_neo4j_final.py

# 清空 Neo4j 数据库
clear-neo4j:
	@echo "🗑️  清空 Neo4j 数据库..."
	python clear_neo4j.py

# ============================================================
# 开发工具
# ============================================================

# 运行所有测试
test: test-backend test-frontend

# 运行后端测试
test-backend:
	@echo "🧪 运行后端测试..."
	cd web/backend && pytest -v

# 运行前端测试
test-frontend:
	@echo "🧪 运行前端测试..."
	cd web/frontend && npm test

# 运行代码检查
lint:
	@echo "🔍 运行代码检查..."
	@echo "检查后端代码..."
	cd web/backend && flake8 app/
	@echo "检查前端代码..."
	cd web/frontend && npm run lint

# 格式化代码
format:
	@echo "✨ 格式化代码..."
	@echo "格式化后端代码..."
	black web/backend/app/ *.py
	@echo "格式化前端代码..."
	cd web/frontend && npm run format || true

# 安装开发依赖
install-dev:
	@echo "📦 安装开发依赖..."
	pip install black flake8 pytest pytest-cov
	cd web/frontend && npm install

# ============================================================
# 清理命令
# ============================================================

# 清理临时文件和缓存
clean:
	@echo "🧹 清理临时文件..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ipynb_checkpoints" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	@echo "✅ 清理完成"

# 清理所有内容（包括 Docker 卷）
clean-all: clean
	@echo "🧹 清理所有内容（包括 Docker 卷和输出）..."
	docker-compose --profile dev down -v
	rm -rf output/
	@echo "✅ 所有内容已清理"

# 清理未使用的 Docker 资源
prune:
	@echo "🧹 清理未使用的 Docker 资源..."
	docker system prune -f
	docker volume prune -f
	@echo "✅ Docker 资源清理完成"

# ============================================================
# 快捷命令
# ============================================================

# 快速启动（构建 + 启动）
quick-start: build up

# 完全重启（停止 + 清理 + 构建 + 启动）
full-restart: down clean build up

# 查看实时日志（所有服务）
watch-logs:
	docker-compose logs -f

# 进入后端容器的 shell
shell-backend:
	docker-compose exec backend /bin/bash

# 进入 Neo4j 容器的 shell
shell-neo4j:
	docker-compose exec neo4j /bin/bash

# 备份 Neo4j 数据
backup-neo4j:
	@echo "💾 备份 Neo4j 数据..."
	@mkdir -p backups
	docker-compose exec neo4j neo4j-admin database dump neo4j --to-path=/backups/neo4j-$(shell date +%Y%m%d-%H%M%S).dump
	@echo "✅ 备份完成"

# 健康检查
health:
	@echo "🏥 检查服务健康状态..."
	@curl -s http://localhost:8000/api/health || echo "❌ 后端服务不可用"
	@curl -s http://localhost:7474 > /dev/null && echo "✅ Neo4j 服务正常" || echo "❌ Neo4j 服务不可用"
	@curl -s http://localhost > /dev/null && echo "✅ 前端服务正常" || echo "❌ 前端服务不可用"
