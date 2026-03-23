"""
车策 Agent - 核心图谱编排模块

使用 LangGraph 构建 ReAct (Reason + Act) 循环
实现智能选车助手的决策流程

核心流程：
1. 推理节点 (reasoning_node): LLM 思考下一步行动
2. 工具节点 (tool_node): 执行工具调用
3. 条件边: 决定是继续循环还是结束
"""

import logging
import json
from typing import Literal, Dict, Any

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.agent.state import (
    AgentState,
    create_initial_state,
    get_redis_checkpointer
)
from app.tools.tavily_search import get_tavily_tools
from app.rag.milvus_store import get_rag_tools

logger = logging.getLogger(__name__)


# ========================================
# 系统提示词
# ========================================

SYSTEM_PROMPT = """

现在是2026年。

你是《车优》，一个专业、高效、有温度的汽车战略顾问。

---

# 【核心身份】

你是一位资深的汽车专家，拥有丰富的行业经验和专业知识。你的职责是帮助用户做出最明智的购车决策。

---

# 【工作流程】

每次收到用户消息时，按以下步骤执行：

## 第一步：理解需求

仔细分析用户的问题，判断他们需要什么：
- 车型推荐
- 价格咨询
- 口碑查询
- 对比分析
- 购车建议

## 第二步：信息收集

如果用户信息不足，温和地询问：
- 预算范围
- 用车场景
- 充电条件
- 家庭成员
- 偏好车型

## 第三步：工具调用

根据需要调用合适的工具：
- `tavily_search_car_news`: 搜索最新汽车新闻
- `tavily_search_car_price`: 搜索价格和优惠
- `tavily_search_car_reviews`: 搜索评测口碑
- `search_car_reviews_rag`: 从车评库检索

## 第四步：综合分析

整合所有信息，给出专业建议：
- 财务匹配度分析
- 场景契合度评估
- 竞品对比
- 购车时机建议

---

# 【输出规范】

使用 Markdown 格式，结构清晰：

### 💡 核心分析
（简明扼要的分析结论）

### 🚗 推荐方案
（具体的车型推荐）

### ⚠️ 注意事项
（需要提醒的风险点）

---

# 【语气要求】

- 专业但不生硬
- 简洁但不冷漠
- 有温度但不啰嗦
- 遇到离谱需求要直接指出

现在，请根据用户的输入开始工作。"""


# ========================================
# LLM 初始化
# ========================================

def get_llm(streaming: bool = False):
    """
    获取 LLM 实例
    
    使用阿里云百炼 SDK (ChatOpenAI 兼容模式) 连接千问模型
    配置温度、重试机制和超时
    
    Args:
        streaming: 是否开启流式输出，默认 False
        
    Returns:
        ChatOpenAI: LLM 实例
    """
    from langchain_openai import ChatOpenAI
    
    return ChatOpenAI(
        model=settings.dashscope_model,
        api_key=settings.dashscope_api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=settings.temperature,
        max_retries=2,
        max_tokens=settings.max_tokens,
        streaming=streaming
    )


def get_llm_with_tools(streaming: bool = False):
    """
    获取绑定工具的 LLM 实例
    
    Args:
        streaming: 是否开启流式输出，默认 False
        
    Returns:
        LLM with tools bound
    """
    llm = get_llm(streaming=streaming)
    tools = get_all_tools()
    return llm.bind_tools(tools)


def get_all_tools():
    """
    获取所有可用工具
    
    Returns:
        List[Tool]: 工具列表
    """
    return get_tavily_tools() + get_rag_tools()


# ========================================
# 节点定义
# ========================================

def reasoning_node(state: AgentState) -> dict:
    """
    推理节点
    
    LLM 思考节点，决定下一步行动：
    - 直接回答用户
    - 调用工具获取信息
    - 询问更多信息
    
    这是 ReAct 循环的核心节点
    
    Args:
        state: 当前 Agent 状态
        
    Returns:
        dict: 更新后的状态
    """
    logger.info("执行推理节点 - LLM 思考下一步行动")
    
    # 检查迭代次数，防止无限循环
    iteration = state.get("iteration_count", 0)
    if iteration >= settings.max_iterations:
        logger.warning(f"达到最大迭代次数 {settings.max_iterations}，强制结束")
        return {
            "should_continue": False,
            "current_step": "max_iterations"
        }
    
    # 获取 LLM 并绑定工具
    llm = get_llm_with_tools()
    
    # 构建消息
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    
    # 调用 LLM
    response = llm.invoke(messages)
    
    logger.info(f"LLM 响应: {response.content[:200] if response.content else '无内容'}...")
    
    # 检查是否有工具调用
    has_tool_calls = bool(response.tool_calls)
    
    if has_tool_calls:
        logger.info(f"LLM 决定调用工具: {[tc['name'] for tc in response.tool_calls]}")
        return {
            "messages": [response],
            "should_continue": True,
            "current_step": "tool_call",
            "iteration_count": iteration + 1
        }
    else:
        # 没有工具调用，直接返回结果
        logger.info("LLM 决定直接回答")
        return {
            "messages": [response],
            "should_continue": False,
            "current_step": "final",
            "final_response": response.content,
            "iteration_count": iteration + 1
        }


def tool_node(state: AgentState) -> dict:
    """
    工具执行节点
    
    执行 LLM 决定的工具调用，支持知识缓存：
    1. 查询前检查 Milvus 缓存
    2. 缓存命中则直接返回
    3. 缓存未命中则调用工具并保存结果
    
    Args:
        state: 当前 Agent 状态
        
    Returns:
        dict: 更新后的状态
    """
    logger.info("执行工具节点 - 执行工具调用")
    
    from app.rag.milvus_store import KnowledgeCache
    
    last_message = state["messages"][-1]
    
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        logger.warning("没有工具调用需要执行")
        return {"current_step": "reasoning"}
    
    tools = {tool.name: tool for tool in get_all_tools()}
    cache = KnowledgeCache()
    tool_messages = []
    
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        logger.info(f"执行工具: {tool_name}, 参数: {json.dumps(tool_args, ensure_ascii=False)}")
        
        if tool_name in tools:
            try:
                query = json.dumps(tool_args, ensure_ascii=False)
                
                logger.info(f"检查缓存: {tool_name}")
                cached_result = cache.check_cache(query)
                logger.info(f"缓存检查完成: {tool_name}")
                
                if cached_result:
                    result = f"[缓存命中]\n\n{cached_result}"
                    logger.info(f"使用缓存结果: {tool_name}")
                else:
                    logger.info(f"调用工具: {tool_name}")
                    result = tools[tool_name].invoke(tool_args)
                    logger.info(f"工具调用完成: {tool_name}")
                    
                    cache.save_to_cache(
                        query=query,
                        result=str(result),
                        tool_name=tool_name
                    )
                
                tool_messages.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"]
                ))
                logger.info(f"工具执行成功: {tool_name}")
                
            except Exception as e:
                error_msg = f"工具执行失败: {str(e)}"
                tool_messages.append(ToolMessage(
                    content=error_msg,
                    tool_call_id=tool_call["id"]
                ))
                logger.error(error_msg)
        else:
            tool_messages.append(ToolMessage(
                content=f"未知工具: {tool_name}",
                tool_call_id=tool_call["id"]
            ))
    
    return {
        "messages": tool_messages,
        "current_step": "reasoning"
    }


# ========================================
# 路由函数
# ========================================

def should_continue(state: AgentState) -> Literal["tool_node", "end"]:
    """
    决定是否继续循环
    
    直接检查最后一条消息是否有 tool_calls，而不是依赖状态变量。
    这是更健壮的路由逻辑，符合 OpenAI API 协议要求。
    
    Args:
        state: 当前状态
        
    Returns:
        下一个节点名称
    """
    messages = state.get("messages", [])
    if not messages:
        return "end"
    
    last_message = messages[-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        logger.info(f"路由到工具节点，待执行工具: {[tc['name'] for tc in last_message.tool_calls]}")
        return "tool_node"
    
    logger.info("无工具调用，路由到结束节点")
    return "end"


# ========================================
# 构建工作流图
# ========================================

def build_graph(streaming: bool = False):
    """
    构建 LangGraph 工作流图
    
    创建一个基于 ReAct 模式的 Agent 工作流：
    
    ```
    START -> reasoning -> [tool_node -> reasoning]* -> END
    ```
    
    工作流节点：
    - reasoning: LLM 推理节点，决定下一步行动
    - tool_node: 工具执行节点
    
    条件边：
    - 如果 LLM 决定调用工具 -> tool_node
    - 如果 LLM 决定直接回答 -> END
    
    Args:
        streaming: 是否启用流式输出模式，默认 False
        
    Returns:
        CompiledGraph: 编译后的工作流
    """
    logger.info(f"构建 ReAct Agent 工作流图, streaming={streaming}")
    
    workflow = StateGraph(AgentState)
    
    def reasoning_node_streaming(state: AgentState) -> dict:
        """
        推理节点（支持流式输出）
        
        使用 streaming=True 的 LLM 实例，
        配合 LangGraph astream_events 实现流式输出
        """
        logger.info("执行推理节点 - LLM 思考下一步行动 (streaming mode)")
        
        iteration = state.get("iteration_count", 0)
        if iteration >= settings.max_iterations:
            logger.warning(f"达到最大迭代次数 {settings.max_iterations}，强制结束")
            return {
                "should_continue": False,
                "current_step": "max_iterations"
            }
        
        llm = get_llm_with_tools(streaming=True)
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = llm.invoke(messages)
        
        logger.info(f"LLM 响应: {response.content[:200] if response.content else '无内容'}...")
        
        has_tool_calls = bool(response.tool_calls)
        
        if has_tool_calls:
            logger.info(f"LLM 决定调用工具: {[tc['name'] for tc in response.tool_calls]}")
            return {
                "messages": [response],
                "should_continue": True,
                "current_step": "tool_call",
                "iteration_count": iteration + 1
            }
        else:
            logger.info("LLM 决定直接回答")
            return {
                "messages": [response],
                "should_continue": False,
                "current_step": "final",
                "final_response": response.content,
                "iteration_count": iteration + 1
            }
    
    if streaming:
        workflow.add_node("reasoning", reasoning_node_streaming)
    else:
        workflow.add_node("reasoning", reasoning_node)
    
    workflow.add_node("tool_node", tool_node)
    workflow.set_entry_point("reasoning")
    
    workflow.add_conditional_edges(
        "reasoning",
        should_continue,
        {
            "tool_node": "tool_node",
            "end": END
        }
    )
    
    workflow.add_edge("tool_node", "reasoning")
    
    checkpointer = get_redis_checkpointer()
    app = workflow.compile(checkpointer=checkpointer)
    
    logger.info("ReAct Agent 工作流图构建完成")
    
    return app


# ========================================
# 全局工作流实例
# ========================================

_graph = None
_graph_streaming = None


def get_graph():
    """
    获取工作流实例（单例模式）
    
    Returns:
        CompiledGraph: 编译后的工作流（非流式）
    """
    global _graph
    if _graph is None:
        _graph = build_graph(streaming=False)
    return _graph


def get_graph_streaming():
    """
    获取流式工作流实例（单例模式）
    
    用于 SSE 流式输出场景，LLM 配置 streaming=True
    
    Returns:
        CompiledGraph: 编译后的工作流（流式）
    """
    global _graph_streaming
    if _graph_streaming is None:
        _graph_streaming = build_graph(streaming=True)
    return _graph_streaming


# ========================================
# 运行 Agent
# ========================================

async def run_agent(session_id: str, user_message: str) -> Dict[str, Any]:
    """
    运行 Agent 工作流
    
    这是主要的入口函数，处理用户消息并返回结果
    
    执行流程：
    1. 创建初始状态
    2. 调用工作流执行
    3. 解析结果并返回
    
    Args:
        session_id: 会话 ID，用于状态持久化
        user_message: 用户消息
        
    Returns:
        Dict: 包含 content、recommendations 等的结果
    """
    logger.info(f"运行 Agent - session_id: {session_id}")
    logger.info(f"用户消息: {user_message}")
    
    try:
        # 获取工作流
        graph = get_graph()
        
        # 创建初始状态
        initial_state = create_initial_state(user_message)
        
        # 配置（用于 Redis 持久化）
        config = {
            "configurable": {
                "thread_id": session_id
            }
        }
        
        # 执行工作流
        logger.info("开始执行 ReAct 工作流...")
        result = graph.invoke(initial_state, config)
        logger.info("工作流执行完成")
        
        # 提取最终响应
        messages = result.get("messages", [])
        final_content = ""
        
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                final_content = msg.content
                break
        
        # 解析推荐车型（如果有）
        recommendations = parse_recommendations(final_content)
        
        # 清理 JSON 代码块
        if "```json" in final_content:
            final_content = final_content.split("```json")[0].strip()
        
        logger.info(f"Agent 执行完成 - session_id: {session_id}")
        
        return {
            "content": final_content,
            "recommendations": recommendations,
            "need_more_info": result.get("need_more_info", False),
            "missing_fields": result.get("slot_status", {}).get("missing_slots", [])
        }
        
    except Exception as e:
        logger.error(f"Agent 执行失败: {str(e)}", exc_info=True)
        
        return {
            "content": f"抱歉，处理您的请求时遇到了问题。请稍后重试。\n\n错误信息: {str(e)}",
            "recommendations": [],
            "need_more_info": False,
            "missing_fields": None
        }


async def run_agent_stream(session_id: str, user_message: str):
    """
    流式运行 Agent 工作流
    
    使用 LangGraph 的 astream_events 异步流式输出 Agent 的回复内容
    通过 Qwen 模型的 streaming=True 配置实现打字机效果
    
    Args:
        session_id: 会话 ID
        user_message: 用户消息
        
    Yields:
        Dict: 流式输出块
            - {"type": "content", "text": "..."} - 内容片段
            - {"type": "tool_call", "name": "...", "args": {...}} - 工具调用
            - {"type": "tool_result", "name": "...", "result": "..."} - 工具结果
            - {"type": "done", "session_id": "...", "recommendations": [...]} - 完成
            - {"type": "error", "message": "..."} - 错误
    """
    logger.info(f"流式运行 Agent - session_id: {session_id}")
    logger.info(f"用户消息: {user_message}")
    
    try:
        graph = get_graph_streaming()
        initial_state = create_initial_state(user_message)
        config = {"configurable": {"thread_id": session_id}}
        
        final_content = ""
        
        async for event in graph.astream_events(initial_state, config, version="v2"):
            event_type = event.get("event")
            event_name = event.get("name", "")
            data = event.get("data", {})
            
            if event_type == "on_chat_model_stream":
                chunk = data.get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    text = chunk.content
                    final_content += text
                    yield {"type": "content", "text": text}
                    
            elif event_type == "on_tool_start":
                tool_name = event_name
                tool_args = data.get("input", {})
                logger.info(f"工具调用开始: {tool_name}")
                yield {"type": "tool_call", "name": tool_name, "args": tool_args}
                
            elif event_type == "on_tool_end":
                tool_name = event_name
                tool_result = data.get("output", "")
                logger.info(f"工具调用结束: {tool_name}")
                yield {"type": "tool_result", "name": tool_name, "result": str(tool_result)[:200]}
                
            elif event_type == "on_chain_end":
                output = data.get("output", {})
                
                if isinstance(output, dict) and "messages" in output:
                    messages = output.get("messages", [])
                    for msg in reversed(messages):
                        if hasattr(msg, "content") and msg.content:
                            if not final_content:
                                final_content = msg.content
                            break
        
        recommendations = parse_recommendations(final_content)
        
        if "```json" in final_content:
            final_content = final_content.split("```json")[0].strip()
        
        yield {
            "type": "done",
            "session_id": session_id,
            "content": final_content,
            "recommendations": recommendations
        }
        
        logger.info(f"流式 Agent 执行完成 - session_id: {session_id}")
        
    except Exception as e:
        logger.error(f"流式 Agent 执行失败: {str(e)}", exc_info=True)
        yield {"type": "error", "message": str(e)}


def parse_recommendations(content: str) -> list:
    """
    从 LLM 回复中解析推荐车型
    
    Args:
        content: LLM 回复内容
        
    Returns:
        List[Dict]: 推荐车型列表
    """
    
    try:
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
            data = json.loads(json_str)
            return data.get("recommendations", [])
        
        if "{" in content and "recommendations" in content:
            start = content.find("{")
            end = content.rfind("}") + 1
            json_str = content[start:end]
            data = json.loads(json_str)
            return data.get("recommendations", [])
            
    except Exception as e:
        logger.warning(f"解析推荐车型失败: {str(e)}")
    
    return []
