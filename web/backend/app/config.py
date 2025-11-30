"""
应用配置
使用 Pydantic Settings 管理环境变量
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """应用配置"""
    
    # API 配置
    API_V1_PREFIX: str = "/api"
    PROJECT_NAME: str = "PWD Knowledge Graph API"
    
    # CORS 配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    # Neo4j 配置
    NEO4J_URI: str = "neo4j://127.0.0.1:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "12345678"
    NEO4J_DATABASE: str = "neo4j"
    
    # 查询配置
    DEFAULT_LIMIT: int = 100
    MAX_LIMIT: int = 1000
    DEFAULT_DEPTH: int = 1
    MAX_DEPTH: int = 3
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
