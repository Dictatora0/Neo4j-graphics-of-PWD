# PWD Knowledge Graph API - 后端服务

基于 FastAPI 的知识图谱 RESTful API 服务

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=12345678
NEO4J_DATABASE=neo4j
```

### 3. 启动服务

```bash
# 开发模式（热重载）
uvicorn app.main:app --reload --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. 访问文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

## 📚 API 文档

### 图谱接口 (`/api/graph`)

- `GET /api/graph/` - 获取图谱数据
- `POST /api/graph/path` - 查找节点路径
- `GET /api/graph/subgraph/{node_name}` - 获取子图

### 节点接口 (`/api/nodes`)

- `GET /api/nodes/` - 获取节点列表
- `GET /api/nodes/{node_id}` - 获取节点详情
- `GET /api/nodes/{node_id}/neighbors` - 获取节点邻居

### 统计接口 (`/api/stats`)

- `GET /api/stats/` - 获取图谱统计
- `GET /api/stats/distribution/nodes` - 节点分布
- `GET /api/stats/distribution/edges` - 关系分布
- `GET /api/stats/top-nodes` - 核心节点排行

### 搜索接口 (`/api/search`)

- `GET /api/search/` - 搜索节点
- `GET /api/search/suggest` - 搜索建议

## 🏗️ 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI应用入口
│   ├── config.py        # 配置管理
│   ├── database.py      # Neo4j连接
│   ├── models.py        # Pydantic模型
│   ├── routers/         # API路由
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   ├── stats.py
│   │   └── search.py
│   └── services/        # 业务逻辑
│       ├── graph_service.py
│       ├── stats_service.py
│       └── search_service.py
├── requirements.txt
└── README.md
```

## 🧪 测试

```bash
# 运行测试
pytest

# 测试覆盖率
pytest --cov=app
```

## 📦 依赖

- FastAPI 0.109+
- Neo4j Python Driver 5.x
- Pydantic 2.x
- Uvicorn

## 🔧 开发

### 添加新接口

1. 在 `app/routers/` 创建路由文件
2. 在 `app/services/` 创建服务文件
3. 在 `app/main.py` 注册路由

### 数据模型

所有数据模型定义在 `app/models.py`，使用 Pydantic 进行数据验证。

## 📄 许可证

MIT License
