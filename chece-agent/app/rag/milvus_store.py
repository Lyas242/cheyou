"""
车策 Agent - Milvus 向量存储模块

使用 LlamaIndex 连接 Milvus 向量数据库
提供车评数据的存储和检索能力
"""

import logging
from typing import List, Optional, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


# ========================================
# Milvus 向量存储类
# ========================================

class MilvusVectorStore:
    """
    Milvus 向量存储
    
    使用 LlamaIndex 的 MilvusVectorStore 进行向量存储和检索
    支持车评数据的语义搜索
    
    主要功能：
    - 连接 Milvus 数据库
    - 创建/获取 Collection
    - 插入向量数据
    - 语义相似度检索
    """
    
    def __init__(
        self,
        collection_name: Optional[str] = None,
        embedding_dimension: Optional[int] = None
    ):
        """
        初始化 Milvus 向量存储
        
        Args:
            collection_name: Collection 名称，默认使用配置中的值
            embedding_dimension: 向量维度，默认使用配置中的值
        """
        self.collection_name = collection_name or settings.milvus_collection
        self.embedding_dimension = embedding_dimension or settings.embedding_dimension
        self._client = None
        self._vector_store = None
        self._index = None
        
    @property
    def client(self):
        """懒加载 Milvus 客户端"""
        if self._client is None:
            try:
                from pymilvus import MilvusClient
                
                self._client = MilvusClient(
                    uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
                    timeout=10
                )
                logger.info(f"Milvus 客户端连接成功: {settings.milvus_host}:{settings.milvus_port}")
                
            except Exception as e:
                logger.error(f"Milvus 连接失败: {str(e)}")
                raise
        return self._client
    
    def get_vector_store(self):
        """
        获取 LlamaIndex MilvusVectorStore 实例
        
        Returns:
            MilvusVectorStore: LlamaIndex 向量存储实例
        """
        if self._vector_store is None:
            try:
                from llama_index.vector_stores.milvus import MilvusVectorStore
                from llama_index.core import StorageContext
                
                self._vector_store = MilvusVectorStore(
                    uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
                    collection_name=self.collection_name,
                    dim=self.embedding_dimension,
                    overwrite=False
                )
                logger.info(f"MilvusVectorStore 初始化成功: {self.collection_name}")
                
            except Exception as e:
                logger.error(f"MilvusVectorStore 初始化失败: {str(e)}")
                raise
                
        return self._vector_store
    
    def create_collection(self, overwrite: bool = False):
        """
        创建 Collection
        
        Args:
            overwrite: 是否覆盖已存在的 Collection
        """
        try:
            if overwrite:
                self.client.drop_collection(self.collection_name)
                logger.info(f"已删除旧 Collection: {self.collection_name}")
            
            self.client.create_collection(
                collection_name=self.collection_name,
                dimension=self.embedding_dimension
            )
            logger.info(f"Collection 创建成功: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"Collection 创建失败: {str(e)}")
            raise
    
    def insert_documents(self, documents: List[Dict[str, Any]]):
        """
        插入文档
        
        Args:
            documents: 文档列表，每个文档包含 id, text, vector 和 metadata
        """
        try:
            data = []
            for i, doc in enumerate(documents):
                row = {
                    "id": doc.get("id", i),
                    "vector": doc.get("vector"),
                    "text": doc.get("text", ""),
                }
                if doc.get("metadata"):
                    row["metadata"] = doc.get("metadata")
                data.append(row)
            
            self.client.insert(
                collection_name=self.collection_name,
                data=data
            )
            logger.info(f"插入 {len(documents)} 个文档到 {self.collection_name}")
            
        except Exception as e:
            logger.error(f"文档插入失败: {str(e)}")
            raise
    
    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_expr: Optional[str] = None
    ) -> List[Dict]:
        """
        向量相似度搜索
        
        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            filter_expr: 过滤表达式
            
        Returns:
            搜索结果列表
        """
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                data=[query_vector],
                limit=top_k,
                filter=filter_expr,
                output_fields=["text", "metadata"]
            )
            
            return results[0] if results else []
            
        except Exception as e:
            logger.error(f"向量搜索失败: {str(e)}")
            return []


# ========================================
# 知识缓存管理器
# ========================================

class KnowledgeCache:
    """
    知识缓存管理器
    
    将工具查询结果保存到 Milvus，实现：
    1. 查询前检查缓存 - 避免重复调用外部 API
    2. 查询后保存结果 - 积累知识库
    """
    
    CACHE_COLLECTION = "agent_knowledge_cache"
    
    def __init__(self):
        self._vector_store = None
        self._embed_model = None
        self._doc_id_counter = 0
    
    @property
    def vector_store(self):
        if self._vector_store is None:
            self._vector_store = MilvusVectorStore(
                collection_name=self.CACHE_COLLECTION
            )
        return self._vector_store
    
    @property
    def embed_model(self):
        if self._embed_model is None:
            try:
                from llama_index.embeddings.dashscope import DashScopeEmbedding
                self._embed_model = DashScopeEmbedding(
                    model_name="text-embedding-v3",
                    api_key=settings.dashscope_api_key,
                    embed_batch_size=10,
                    embed_dim=settings.embedding_dimension
                )
                logger.info(f"KnowledgeCache Embedding 模型加载成功，维度: {settings.embedding_dimension}")
            except Exception as e:
                logger.error(f"Embedding 模型加载失败: {str(e)}")
                raise
        return self._embed_model
    
    def _ensure_collection(self):
        """确保 Collection 存在且维度匹配"""
        try:
            logger.info("获取 Milvus 客户端...")
            collections = self.vector_store.client.list_collections()
            logger.info(f"现有 Collections: {collections}")
            
            if self.CACHE_COLLECTION in collections:
                logger.info(f"检查 Collection 维度: {self.CACHE_COLLECTION}")
                desc = self.vector_store.client.describe_collection(self.CACHE_COLLECTION)
                logger.info(f"Collection 描述: {desc.get('fields', [])}")
                for field in desc.get("fields", []):
                    if field.get("name") == "vector":
                        current_dim = field.get("params", {}).get("dim")
                        logger.info(f"当前向量维度: {current_dim}, 配置维度: {settings.embedding_dimension}")
                        if current_dim and current_dim != settings.embedding_dimension:
                            logger.info(f"Collection 维度不匹配 ({current_dim} vs {settings.embedding_dimension})，正在重建...")
                            self.vector_store.client.drop_collection(self.CACHE_COLLECTION)
                            logger.info(f"已删除 Collection: {self.CACHE_COLLECTION}")
                            break
            
            collections = self.vector_store.client.list_collections()
            if self.CACHE_COLLECTION not in collections:
                logger.info(f"创建 Collection: {self.CACHE_COLLECTION}")
                self.vector_store.create_collection(overwrite=False)
                logger.info(f"创建知识缓存 Collection: {self.CACHE_COLLECTION}")
        except Exception as e:
            logger.warning(f"检查 Collection 失败: {str(e)}")
    
    def check_cache(
        self,
        query: str,
        similarity_threshold: float = 0.85
    ) -> Optional[str]:
        """
        检查缓存中是否有相似查询的结果
        
        Args:
            query: 查询文本
            similarity_threshold: 相似度阈值（0-1）
            
        Returns:
            缓存的结果文本，如果没有则返回 None
        """
        try:
            logger.info(f"开始检查缓存: {query[:50]}...")
            self._ensure_collection()
            logger.info("Collection 检查完成，开始生成向量...")
            
            query_vector = self.embed_model.get_query_embedding(query)
            logger.info(f"向量生成完成，维度: {len(query_vector)}")
            
            results = self.vector_store.search(
                query_vector=query_vector,
                top_k=1
            )
            logger.info("向量搜索完成")
            
            if results:
                distance = results[0].get("distance", 1)
                similarity = 1 - distance
                
                if similarity >= similarity_threshold:
                    entity = results[0].get("entity", {})
                    cached_result = entity.get("text", "")
                    logger.info(f"命中知识缓存! 相似度: {similarity:.2%}")
                    return cached_result
            
            logger.info("未命中知识缓存，将调用工具获取")
            return None
            
        except Exception as e:
            logger.warning(f"检查缓存失败: {str(e)}")
            return None
    
    def save_to_cache(
        self,
        query: str,
        result: str,
        tool_name: str,
        metadata: Optional[Dict] = None
    ):
        """
        将查询结果保存到缓存
        
        Args:
            query: 原始查询
            result: 工具返回的结果
            tool_name: 工具名称
            metadata: 额外的元数据
        """
        if not result or len(result) < 50:
            return
        
        try:
            self._ensure_collection()
            
            import time
            doc_id = int(time.time() * 1000)
            
            text_to_embed = f"查询: {query}\n\n结果: {result}"
            logger.info(f"生成缓存向量，文本长度: {len(text_to_embed)}")
            vector = self.embed_model.get_text_embedding(text_to_embed)
            
            if not vector:
                logger.warning(f"向量生成失败，跳过缓存保存")
                return
            
            logger.info(f"向量生成成功，维度: {len(vector)}")
            
            document = {
                "id": doc_id,
                "text": text_to_embed,
                "vector": vector,
                "metadata": {
                    "query": query,
                    "tool_name": tool_name,
                    "timestamp": doc_id,
                    **(metadata or {})
                }
            }
            
            self.vector_store.insert_documents([document])
            logger.info(f"已保存到知识缓存: {query[:50]}...")
            
        except Exception as e:
            logger.warning(f"保存到缓存失败: {str(e)}")


# ========================================
# RAG 检索器
# ========================================

class CarReviewRetriever:
    """
    车评检索器
    
    封装车评数据的语义检索逻辑
    提供基于用户需求的智能检索
    """
    
    def __init__(self):
        """初始化检索器"""
        self._vector_store = None
        self._embed_model = None
        
    @property
    def vector_store(self):
        """懒加载向量存储"""
        if self._vector_store is None:
            self._vector_store = MilvusVectorStore()
        return self._vector_store
    
    @property
    def embed_model(self):
        """懒加载 Embedding 模型"""
        if self._embed_model is None:
            try:
                from llama_index.embeddings.dashscope import DashScopeEmbedding
                
                self._embed_model = DashScopeEmbedding(
                    model_name="text-embedding-v3",
                    api_key=settings.dashscope_api_key,
                    embed_batch_size=10,
                    embed_dim=settings.embedding_dimension
                )
                logger.info("Embedding 模型加载成功: text-embedding-v3 (阿里云百炼)")
                
            except Exception as e:
                logger.error(f"Embedding 模型加载失败: {str(e)}")
                raise
        return self._embed_model
    
    def _ensure_collection(self) -> bool:
        """
        确保 Collection 存在且维度匹配，不存在则自动创建
        
        Returns:
            bool: Collection 是否可用
        """
        if self._collection_checked:
            return True
            
        try:
            collections = self.vector_store.client.list_collections()
            collection_name = self.vector_store.collection_name
            logger.info(f"CarReviewRetriever - 现有 Collections: {collections}, 目标: {collection_name}")
            
            if collection_name in collections:
                desc = self.vector_store.client.describe_collection(collection_name)
                logger.info(f"Collection '{collection_name}' 字段: {desc.get('fields', [])}")
                for field in desc.get("fields", []):
                    if field.get("name") == "vector":
                        current_dim = field.get("params", {}).get("dim")
                        logger.info(f"当前向量维度: {current_dim}, 配置维度: {settings.embedding_dimension}")
                        if current_dim and current_dim != settings.embedding_dimension:
                            logger.info(f"Collection '{collection_name}' 维度不匹配 ({current_dim} vs {settings.embedding_dimension})，正在重建...")
                            self.vector_store.client.drop_collection(collection_name)
                            logger.info(f"已删除 Collection: {collection_name}")
                            break
            
            collections = self.vector_store.client.list_collections()
            if collection_name not in collections:
                logger.info(f"Collection '{collection_name}' 不存在，正在自动创建...")
                self.vector_store.create_collection(overwrite=False)
                logger.info(f"Collection '{collection_name}' 创建成功")
            
            self._collection_checked = True
            return True
            
        except Exception as e:
            logger.error(f"确保 Collection 失败: {str(e)}")
            return False
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        car_model: Optional[str] = None
    ) -> str:
        """
        检索相关车评
        
        根据用户查询检索相关的车评内容
        
        Args:
            query: 用户查询，如 "20万纯电轿车智驾口碑"
            top_k: 返回结果数量
            car_model: 可选的车型过滤
            
        Returns:
            格式化的检索结果文本
        """
        logger.info(f"RAG 检索: {query}")
        
        if not self._ensure_collection():
            return f"车评数据库连接失败，请检查 Milvus 服务是否正常。"
        
        try:
            # 生成查询向量
            query_vector = self.embed_model.get_query_embedding(query)
            
            # 构建过滤条件
            filter_expr = None
            if car_model:
                filter_expr = f'car_model == "{car_model}"'
            
            # 执行搜索
            results = self.vector_store.search(
                query_vector=query_vector,
                top_k=top_k,
                filter_expr=filter_expr
            )
            
            if not results:
                return f"未找到与 '{query}' 相关的车评内容。"
            
            # 格式化结果
            result_text = f"### 📚 相关车评 ({query})\n\n"
            
            for i, result in enumerate(results, 1):
                entity = result.get("entity", {})
                text = entity.get("text", "")
                distance = result.get("distance", 0)
                
                # 计算相似度百分比
                similarity = (1 - distance) * 100 if distance else 0
                
                result_text += f"**{i}. 相似度: {similarity:.1f}%**\n"
                result_text += f"{text[:500]}...\n\n"
            
            return result_text
            
        except Exception as e:
            logger.error(f"RAG 检索失败: {str(e)}")
            return f"检索失败: {str(e)}"
    
    def retrieve_by_scenario(
        self,
        scenario: str,
        budget: Optional[str] = None,
        top_k: int = 5
    ) -> str:
        """
        按场景检索车评
        
        根据用车场景检索相关的车评内容
        
        Args:
            scenario: 用车场景，如 "家用"、"通勤"
            budget: 预算范围
            top_k: 返回结果数量
            
        Returns:
            格式化的检索结果
        """
        query = f"{budget or ''} {scenario} 新能源汽车 口碑 体验"
        return self.retrieve(query.strip(), top_k)


# ========================================
# LangChain Tool 定义
# ========================================

def get_rag_tools() -> List:
    """
    获取 RAG 工具列表
    
    返回 LangChain Tool 格式的工具列表
    
    Returns:
        List[Tool]: LangChain 工具列表
    """
    from langchain_core.tools import tool
    
    retriever = CarReviewRetriever()
    
    @tool
    def search_car_reviews_rag(query: str) -> str:
        """
        从车评数据库中检索相关内容
        
        使用向量语义搜索从已存储的车评数据中检索相关内容。
        当需要了解某款车的真实口碑、优缺点、使用体验时使用此工具。
        
        Args:
            query: 搜索查询，如 "20万纯电轿车智驾口碑"、"比亚迪海豹真实车主评价"
            
        Returns:
            相关车评内容
        """
        return retriever.retrieve(query)
    
    @tool
    def search_by_scenario(scenario: str, budget: Optional[str] = None) -> str:
        """
        按用车场景检索车评
        
        根据用车场景（如家用、通勤、长途）检索相关的车评内容。
        
        Args:
            scenario: 用车场景
            budget: 预算范围（可选）
            
        Returns:
            相关车评内容
        """
        return retriever.retrieve_by_scenario(scenario, budget)
    
    return [search_car_reviews_rag, search_by_scenario]


# ========================================
# Mock 数据（开发环境使用）
# ========================================

def init_mock_data():
    """
    初始化 Mock 数据
    
    在开发环境下插入模拟的车评数据
    """
    from llama_index.embeddings.dashscope import DashScopeEmbedding
    
    embed_model = DashScopeEmbedding(
        model_name="text-embedding-v3",
        api_key=settings.dashscope_api_key,
        embed_batch_size=10,
        embed_dim=settings.embedding_dimension
    )
    
    mock_texts = [
        "比亚迪海豹真实车主评价：作为一款20万级别的纯电轿车，海豹的驾驶质感非常出色。e平台3.0的技术确实成熟，续航扎实，800V快充很实用。唯一不足是后排头部空间稍显局促。",
        "极氪001车主真实体验：买了极氪001半年多了，整体非常满意。空间大、配置高、驾驶感受好。特别是空气悬架和电磁悬挂，过减速带非常舒适。智驾系统也在不断升级。",
        "特斯拉Model 3使用心得：提车三个月，最满意的是智驾系统和超充网络。AP在高速上非常省心，超充站覆盖广充电快。缺点是内饰过于简约，隔音一般。"
    ]
    
    mock_metadata = [
        {"car_model": "比亚迪海豹", "price_range": "16-24万", "type": "纯电轿车"},
        {"car_model": "极氪001", "price_range": "26-35万", "type": "纯电猎装"},
        {"car_model": "特斯拉Model 3", "price_range": "23-33万", "type": "纯电轿车"}
    ]
    
    vectors = embed_model.get_text_embedding_batch(mock_texts)
    
    mock_documents = []
    for i, (text, vector, metadata) in enumerate(zip(mock_texts, vectors, mock_metadata), 1):
        mock_documents.append({
            "id": i,
            "text": text,
            "vector": vector,
            "metadata": metadata
        })
    
    store = MilvusVectorStore()
    store.create_collection(overwrite=True)
    store.insert_documents(mock_documents)
    
    logger.info("Mock 数据初始化完成")
