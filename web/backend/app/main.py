"""
松材线虫病知识图谱 Web API
FastAPI 应用主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import neo4j_driver, close_neo4j_connection
from app.routers import graph, nodes, stats, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("🚀 启动 PWD Knowledge Graph API...")
    print(f"📊 Neo4j URI: {settings.NEO4J_URI}")
    
    # 测试数据库连接
    try:
        neo4j_driver.verify_connectivity()
        print("✅ Neo4j 连接成功")
    except Exception as e:
        print(f"❌ Neo4j 连接失败: {e}")
    
    yield
    
    # 关闭时执行
    print("🛑 关闭 API 服务...")
    close_neo4j_connection()


# 创建 FastAPI 应用
app = FastAPI(
    title="PWD Knowledge Graph API",
    description="松材线虫病知识图谱 RESTful API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(graph.router, prefix="/api/graph", tags=["图谱"])
app.include_router(nodes.router, prefix="/api/nodes", tags=["节点"])
app.include_router(stats.router, prefix="/api/stats", tags=["统计"])
app.include_router(search.router, prefix="/api/search", tags=["搜索"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "PWD Knowledge Graph API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        neo4j_driver.verify_connectivity()
        return {"status": "healthy", "neo4j": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "neo4j": "disconnected", "error": str(e)}
