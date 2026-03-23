"""
车策 Agent - 聊天 API 路由

处理与 Java 后端的通信，调用 LangGraph 工作流
提供 RESTful 接口供前端调用
支持 SSE 流式输出
"""

import logging
import json
from typing import List, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.graph import run_agent, run_agent_stream

logger = logging.getLogger(__name__)

router = APIRouter()


# ========================================
# 请求/响应模型定义
# ========================================

class ChatRequest(BaseModel):
    """
    聊天请求模型
    
    接收来自 Java 后端或前端的请求
    session_id 用于追踪多轮对话状态
    """
    session_id: str = Field(
        ...,
        alias="sessionId",
        description="会话唯一标识，用于追踪多轮对话状态，由前端生成或 Java 后端分配"
    )
    message: str = Field(
        ...,
        description="用户发送的消息内容，如购车需求、车型咨询等"
    )

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "sessionId": "user_123_session_456",
                "message": "我预算20万，想买一辆纯电SUV，主要家用，有推荐吗？"
            }
        }


class CarRecommendation(BaseModel):
    """
    车型推荐数据模型
    
    结构化返回推荐结果，供前端渲染推荐卡片
    """
    id: str = Field(
        description="车型唯一标识，用于关联详细信息"
    )
    name: str = Field(
        description="车型名称，如 '比亚迪海豹 2024款'"
    )
    price_range: str = Field(
        alias="priceRange",
        description="价格区间，如 '16.68-23.98万'"
    )
    image: Optional[str] = Field(
        default="",
        description="车型图片 URL，用于前端展示"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="核心标签，如 ['纯电', '轿跑', '800V快充']"
    )
    description: str = Field(
        description="推荐理由，简要说明为什么推荐这款车型"
    )
    match_score: Optional[int] = Field(
        default=None,
        alias="matchScore",
        description="匹配度评分 (0-100)"
    )

    class Config:
        populate_by_name = True


class ChatResponse(BaseModel):
    """
    聊天响应模型
    
    返回给调用方的完整响应，包含文本回复和结构化推荐
    """
    session_id: str = Field(
        alias="sessionId",
        description="会话 ID，与请求一致"
    )
    content: str = Field(
        description="Agent 的文本回复，Markdown 格式"
    )
    recommendations: List[CarRecommendation] = Field(
        default_factory=list,
        description="推荐的车型列表，供前端渲染卡片"
    )
    need_more_info: bool = Field(
        default=False,
        alias="needMoreInfo",
        description="是否需要更多信息才能给出推荐"
    )
    missing_fields: Optional[List[str]] = Field(
        default=None,
        alias="missingFields",
        description="缺失的信息字段列表"
    )

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "sessionId": "user_123_session_456",
                "content": "### 💡 核心诊断分析\n\n根据您的需求...",
                "recommendations": [
                    {
                        "id": "byd_seal_2024",
                        "name": "比亚迪海豹",
                        "priceRange": "16.68-23.98万",
                        "tags": ["纯电", "轿跑", "800V快充"],
                        "description": "e平台3.0技术成熟，续航扎实"
                    }
                ],
                "needMoreInfo": False,
                "missingFields": None
            }
        }


# ========================================
# API 路由定义
# ========================================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Agent 聊天接口（非流式）
    
    接收用户消息，调用 LangGraph 工作流处理，
    返回 Agent 的回复和推荐车型
    
    ## 处理流程
    1. 接收请求，提取 session_id 和 message
    2. 调用 LangGraph Agent 工作流
    3. 工作流内部：
       - 槽位提取：从对话中提取预算、车型偏好等
       - 逻辑熔断：检测不合理需求
       - 信息追问：温和询问缺失信息
       - 深度分析：七维决策框架分析
    4. 返回结构化响应
    
    ## 错误处理
    - 400: 请求参数无效
    - 500: Agent 内部处理错误
    """
    logger.info(f"收到聊天请求 - session_id: {request.session_id}")
    logger.debug(f"用户消息: {request.message}")
    
    try:
        result = await run_agent(
            session_id=request.session_id,
            user_message=request.message
        )
        
        logger.info(f"Agent 处理完成 - session_id: {request.session_id}")
        
        response = ChatResponse(
            content=result.get("content", ""),
            recommendations=[
                CarRecommendation(**car) 
                for car in result.get("recommendations", [])
            ]
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Agent 处理失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agent 处理失败: {str(e)}"
        )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Agent 聊天接口（流式输出）
    
    使用 Server-Sent Events (SSE) 实现实时流式输出
    前端可以实时显示 Agent 的回复内容（打字机效果）
    
    ## SSE 事件格式
    每个事件都是标准 SSE 格式：`data: {json}\n\n`
    
    ### 事件类型
    1. content 事件 - 内容片段（打字机效果）
       ```json
       {"type": "content", "text": "回复内容片段"}
       ```
    
    2. tool_call 事件 - 工具调用开始
       ```json
       {"type": "tool_call", "name": "tavily_search_car_price", "args": {...}}
       ```
    
    3. tool_result 事件 - 工具调用结束
       ```json
       {"type": "tool_result", "name": "tavily_search_car_price", "result": "..."}
       ```
    
    4. done 事件 - 流式输出完成
       ```json
       {"type": "done", "session_id": "xxx", "content": "完整内容", "recommendations": [...]}
       ```
    
    5. error 事件 - 错误
       ```json
       {"type": "error", "message": "错误信息"}
       ```
    
    ## 前端使用示例
    ```javascript
    const eventSource = new EventSource('/api/agent/chat/stream');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        switch (data.type) {
            case 'content':
                // 追加文本到界面（打字机效果）
                appendText(data.text);
                break;
            case 'tool_call':
                // 显示工具调用状态
                showToolCall(data.name);
                break;
            case 'done':
                // 流式输出完成
                finalizeResponse(data);
                eventSource.close();
                break;
            case 'error':
                // 处理错误
                showError(data.message);
                eventSource.close();
                break;
        }
    };
    ```
    """
    logger.info(f"收到流式聊天请求 - session_id: {request.session_id}")
    logger.info(f"用户消息: {request.message}")
    
    async def generate() -> AsyncGenerator[str, None]:
        """
        SSE 生成器函数
        
        产生标准 SSE 格式的数据流：
        - 每条消息以 `data: ` 开头
        - 以两个换行符 `\n\n` 结尾
        """
        try:
            async for chunk in run_agent_stream(
                session_id=request.session_id,
                user_message=request.message
            ):
                chunk_type = chunk.get("type")
                
                if chunk_type == "content":
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    
                elif chunk_type == "tool_call":
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    
                elif chunk_type == "tool_result":
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    
                elif chunk_type == "done":
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    
                elif chunk_type == "error":
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    
        except Exception as e:
            logger.error(f"流式输出错误: {str(e)}", exc_info=True)
            error_chunk = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    """
    获取会话历史记录
    
    从 Redis 中获取指定会话的历史消息
    用于页面刷新后恢复对话状态
    
    Args:
        session_id: 会话唯一标识
        
    Returns:
        包含历史消息列表的响应
    """
    logger.info(f"获取会话历史 - session_id: {session_id}")
    
    # TODO: 从 Redis Checkpointer 中获取会话历史
    # 目前返回空列表，后续实现
    
    return {
        "session_id": session_id,
        "messages": []
    }


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """
    清除会话状态
    
    删除指定会话的所有状态数据，开始新对话
    
    Args:
        session_id: 会话唯一标识
        
    Returns:
        操作结果
    """
    logger.info(f"清除会话状态 - session_id: {session_id}")
    
    # TODO: 从 Redis 中删除会话状态
    
    return {
        "session_id": session_id,
        "status": "cleared"
    }
