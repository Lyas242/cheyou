"""
车策 Agent - Tavily 搜索工具

封装 Tavily Search API，提供实时网络搜索能力
用于检索最新的汽车报价、新车资讯、促销活动等
"""

import logging
from typing import Optional, List
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


# ========================================
# 搜索结果模型
# ========================================

class SearchResult(BaseModel):
    """搜索结果项"""
    title: str = Field(description="结果标题")
    url: str = Field(description="结果链接")
    content: str = Field(description="结果摘要内容")
    score: Optional[float] = Field(default=None, description="相关性分数")


class SearchResponse(BaseModel):
    """搜索响应"""
    query: str = Field(description="搜索查询")
    results: List[SearchResult] = Field(default_factory=list, description="搜索结果列表")
    answer: Optional[str] = Field(default=None, description="AI 生成的答案")


# ========================================
# Tavily 搜索工具类
# ========================================

class TavilySearchTool:
    """
    Tavily 搜索工具
    
    封装 Tavily API，提供以下搜索能力：
    - 汽车新闻搜索
    - 价格促销搜索
    - 车型评测搜索
    
    Tavily 是专为 AI Agent 设计的搜索 API，
    返回结构化的搜索结果，支持实时信息检索
    """
    
    def __init__(self):
        """初始化 Tavily 客户端"""
        self.api_key = settings.tavily_api_key
        self._client = None
        self.timeout = 30
        
    @property
    def client(self):
        """懒加载 Tavily 客户端"""
        if self._client is None:
            try:
                from tavily import TavilyClient
                self._client = TavilyClient(api_key=self.api_key)
                logger.info("Tavily 客户端初始化成功")
            except ImportError:
                logger.error("tavily-python 未安装，请运行: pip install tavily-python")
                raise
            except Exception as e:
                logger.error(f"Tavily 客户端初始化失败: {str(e)}")
                raise
        return self._client
    
    def search(
        self,
        query: str,
        search_depth: str = "basic",
        max_results: int = 5,
        include_answer: bool = True
    ) -> SearchResponse:
        """
        执行搜索
        
        Args:
            query: 搜索查询
            search_depth: 搜索深度 "basic" 或 "advanced"
            max_results: 最大结果数
            include_answer: 是否包含 AI 生成的答案
            
        Returns:
            SearchResponse: 搜索响应
        """
        logger.info(f"执行 Tavily 搜索: {query}")
        
        try:
            response = self.client.search(
                query=query,
                search_depth=search_depth,
                max_results=max_results,
                include_answer=include_answer
            )
            
            results = [
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    score=item.get("score")
                )
                for item in response.get("results", [])
            ]
            
            return SearchResponse(
                query=query,
                results=results,
                answer=response.get("answer")
            )
            
        except Exception as e:
            logger.error(f"Tavily 搜索失败: {str(e)}")
            return SearchResponse(query=query, results=[])
    
    def search_car_news(self, keyword: str, max_results: int = 5) -> str:
        """
        搜索汽车新闻
        
        用于搜索新车发布、车型换代、行业动态等
        
        Args:
            keyword: 搜索关键词，如 "极氪001 换代"
            max_results: 最大结果数
            
        Returns:
            格式化的搜索结果文本
        """
        query = f"{keyword} 新能源汽车 新闻 2024 2025"
        response = self.search(query, max_results=max_results)
        
        if not response.results:
            return f"未找到关于 '{keyword}' 的相关新闻。"
        
        result_text = f"### 🔍 关于 '{keyword}' 的最新资讯\n\n"
        
        for i, result in enumerate(response.results, 1):
            result_text += f"**{i}. {result.title}**\n"
            result_text += f"{result.content}\n"
            result_text += f"来源: {result.url}\n\n"
        
        if response.answer:
            result_text += f"**摘要**: {response.answer}\n"
        
        return result_text
    
    def search_car_price(self, car_model: str, max_results: int = 5) -> str:
        """
        搜索汽车价格和促销信息
        
        用于搜索车型报价、优惠活动、落地价格等
        
        Args:
            car_model: 车型名称，如 "比亚迪海豹"
            max_results: 最大结果数
            
        Returns:
            格式化的价格信息文本
        """
        query = f"{car_model} 价格 优惠 促销 落地价 2024"
        response = self.search(query, max_results=max_results)
        
        if not response.results:
            return f"未找到 '{car_model}' 的价格信息。"
        
        result_text = f"### 💰 {car_model} 价格与优惠信息\n\n"
        
        for i, result in enumerate(response.results, 1):
            result_text += f"**{i}. {result.title}**\n"
            result_text += f"{result.content}\n\n"
        
        return result_text
    
    def search_car_reviews(self, car_model: str, max_results: int = 5) -> str:
        """
        搜索车型评测和口碑
        
        用于搜索专业评测、用户口碑、优缺点分析等
        
        Args:
            car_model: 车型名称
            max_results: 最大结果数
            
        Returns:
            格式化的评测信息文本
        """
        query = f"{car_model} 评测 口碑 优缺点 真实车主"
        response = self.search(query, max_results=max_results)
        
        if not response.results:
            return f"未找到 '{car_model}' 的评测信息。"
        
        result_text = f"### 📝 {car_model} 评测与口碑\n\n"
        
        for i, result in enumerate(response.results, 1):
            result_text += f"**{i}. {result.title}**\n"
            result_text += f"{result.content}\n\n"
        
        return result_text


# ========================================
# LangChain Tool 定义
# ========================================

def get_tavily_tools() -> List:
    """
    获取 Tavily 工具列表
    
    返回 LangChain Tool 格式的工具列表，
    可直接绑定到 LLM 使用
    
    Returns:
        List[Tool]: LangChain 工具列表
    """
    from langchain_core.tools import tool
    
    search_tool = TavilySearchTool()
    
    @tool
    def tavily_search_car_news(keyword: str) -> str:
        """
        搜索汽车新闻和资讯
        
        用于获取最新的汽车行业动态、新车发布、车型换代消息等。
        当用户询问某款车的最新消息或是否即将换代时使用此工具。
        
        Args:
            keyword: 搜索关键词，如 "极氪001换代"、"比亚迪新车"
            
        Returns:
            相关新闻和资讯的格式化文本
        """
        return search_tool.search_car_news(keyword)
    
    @tool
    def tavily_search_car_price(car_model: str) -> str:
        """
        搜索汽车价格和促销信息
        
        用于获取车型的当前报价、优惠活动、落地价格等。
        当用户询问某款车的价格或优惠时使用此工具。
        
        Args:
            car_model: 车型名称，如 "比亚迪海豹"、"特斯拉Model 3"
            
        Returns:
            价格和促销信息的格式化文本
        """
        return search_tool.search_car_price(car_model)
    
    @tool
    def tavily_search_car_reviews(car_model: str) -> str:
        """
        搜索车型评测和口碑
        
        用于获取专业评测、用户口碑、优缺点分析等。
        当用户想了解某款车的真实表现时使用此工具。
        
        Args:
            car_model: 车型名称
            
        Returns:
            评测和口碑信息的格式化文本
        """
        return search_tool.search_car_reviews(car_model)
    
    return [tavily_search_car_news, tavily_search_car_price, tavily_search_car_reviews]


# ========================================
# 便捷函数
# ========================================

def search_car_info(query: str, search_type: str = "news") -> str:
    """
    便捷搜索函数
    
    Args:
        query: 搜索查询
        search_type: 搜索类型 "news", "price", "reviews"
        
    Returns:
        搜索结果文本
    """
    tool = TavilySearchTool()
    
    if search_type == "price":
        return tool.search_car_price(query)
    elif search_type == "reviews":
        return tool.search_car_reviews(query)
    else:
        return tool.search_car_news(query)
