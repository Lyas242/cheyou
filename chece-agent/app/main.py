"""
车策 Agent - FastAPI 应用入口

负责初始化 FastAPI 应用、注册路由、配置中间件和生命周期管理
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import chat

# 配置日志格式
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    在应用启动时执行初始化逻辑，在关闭时执行清理逻辑
    使用 async context manager 模式管理资源
    """
    # ========================================
    # 应用启动 - 初始化阶段
    # ========================================
    logger.info(f"🚀 {settings.app_name} 正在启动...")
    logger.info(f"📍 运行环境: {settings.app_env}")
    logger.info(f"🔧 调试模式: {settings.debug}")
    logger.info(f"🤖 使用模型: {settings.dashscope_model} (阿里云百炼)")
    logger.info(f"🔗 API 地址: {settings.dashscope_base_url}")
    
    # TODO: 在此初始化外部连接
    # - Redis 连接池
    # - Milvus 客户端
    # - LLM 模型实例
    
    yield  # 应用运行期间
    
    # ========================================
    # 应用关闭 - 清理阶段
    # ========================================
    logger.info(f"👋 {settings.app_name} 正在关闭...")


# ========================================
# 创建 FastAPI 应用实例
# ========================================
app = FastAPI(
    title=settings.app_name,
    description="""
    ## 车策 - 智能选车助手 Agent 服务
    
    基于 LangGraph 和 RAG 技术的新能源汽车选购决策助手。
    
    ### 核心功能
    - 🚗 智能车型推荐
    - 📊 七维深度决策分析
    - 🔍 实时车价与资讯搜索
    - 💬 多轮对话状态管理
    
    ### 技术栈
    - **Agent 框架**: LangGraph (ReAct 循环)
    - **RAG 框架**: LlamaIndex + Milvus
    - **LLM**: Gemini 2.0 Flash
    - **实时搜索**: Tavily API
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# ========================================
# 配置 CORS 中间件
# ========================================
# 允许前端跨域访问，生产环境应限制具体域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境: ["https://your-domain.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================================
# 注册 API 路由
# ========================================
app.include_router(
    chat.router,
    prefix="/api/agent",
    tags=["Agent Chat"]
)


# ========================================
# 健康检查接口
# ========================================
@app.get("/", tags=["Health"])
async def root():
    """
    根路径健康检查
    
    用于验证服务是否正常运行，负载均衡器探测
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "2.0.0",
        "model": settings.dashscope_model
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    详细健康检查接口
    
    可扩展检查各依赖服务的状态：
    - Redis 连接状态
    - Milvus 连接状态
    - LLM API 可用性
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.app_env,
        "model": settings.dashscope_model,
        "dependencies": {
            "redis": "not_checked",
            "milvus": "not_checked",
            "llm": "configured"
        }
    }
