"""
车策 Agent - 核心配置模块

使用 Pydantic Settings 管理环境变量和应用配置
支持从 .env 文件加载配置，提供类型安全的配置访问
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    应用配置类
    
    所有配置项都从环境变量加载，支持 .env 文件
    使用 Pydantic 进行类型验证和转换
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ========================================
    # 应用基础配置
    # ========================================
    app_name: str = Field(
        default="chece-agent",
        description="应用名称"
    )
    app_env: str = Field(
        default="development",
        description="运行环境: development, staging, production"
    )
    debug: bool = Field(
        default=False,
        description="调试模式开关"
    )
    log_level: str = Field(
        default="INFO",
        description="日志级别: DEBUG, INFO, WARNING, ERROR"
    )
    
    # ========================================
    # LLM 配置 - 阿里云百炼 (DashScope)
    # ========================================
    dashscope_api_key: str = Field(
        default="",
        description="阿里云百炼 API Key，从 https://bailian.console.aliyun.com 获取"
    )
    dashscope_model: str = Field(
        default="qwen-plus",
        description="百炼模型名称: qwen-turbo, qwen-plus, qwen-max"
    )
    dashscope_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="百炼 API 地址"
    )
    
    # ========================================
    # Tavily 搜索 API 配置
    # ========================================
    tavily_api_key: str = Field(
        default="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",
        description="Tavily API Key，用于实时网络搜索"
    )
    
    # ========================================
    # Redis 配置 (LangGraph 状态持久化)
    # ========================================
    redis_url: str = Field(
        default="redis://localhost:6379/3",
        description="Redis 连接 URL"
    )
    redis_password: Optional[str] = Field(
        default=None,
        description="Redis 密码（如有）"
    )
    
    # ========================================
    # Milvus 向量数据库配置
    # ========================================
    milvus_host: str = Field(
        default="localhost",
        description="Milvus 服务器地址"
    )
    milvus_port: int = Field(
        default=19530,
        description="Milvus 服务器端口"
    )
    milvus_collection: str = Field(
        default="car_reviews",
        description="存储车评数据的 Collection 名称"
    )
    
    # ========================================
    # Embedding 模型配置
    # ========================================
    embedding_model: str = Field(
        default="text-embedding-v3",
        description="Embedding 模型名称"
    )
    embedding_dimension: int = Field(
        default=1024,
        description="Embedding 向量维度 (DashScope text-embedding-v3 支持 1024/768/512)"
    )
    
    # ========================================
    # Agent 行为配置
    # ========================================
    max_iterations: int = Field(
        default=5,
        description="Agent 最大迭代次数，防止无限循环"
    )
    temperature: float = Field(
        default=0.5,
        description="LLM 温度参数，控制输出随机性"
    )
    max_tokens: int = Field(
        default=2048,
        description="LLM 最大输出 token 数"
    )
    
    # ========================================
    # 快速响应模式配置
    # ========================================
    fast_mode: bool = Field(
        default=True,
        description="快速响应模式，减少工具调用"
    )
    skip_tools_for_simple_questions: bool = Field(
        default=True,
        description="简单问题跳过工具调用"
    )
    
    @property
    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return self.app_env == "development"
    
    @property
    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return self.app_env == "production"


# 创建全局配置实例
# 在应用启动时自动加载环境变量
settings = Settings()
