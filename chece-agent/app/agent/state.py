"""
车策 Agent - 状态定义模块

定义 LangGraph Agent 在执行过程中需要维护的状态结构
使用 TypedDict 确保类型安全，支持多轮对话状态持久化
"""

import logging
from typing import TypedDict, List, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

logger = logging.getLogger(__name__)


# ========================================
# 槽位定义 - 用户信息提取
# ========================================

class InfoSlots(TypedDict):
    """
    信息槽位结构
    
    用于追踪用户已提供的信息，支持多轮对话状态保持
    每个槽位都有 filled 状态标记，便于判断是否需要追问
    
    Attributes:
        budget: 购车预算，如 "20万"、"15-25万"
        income: 月薪/年收入，如 "月薪2万"
        target_car: 意向车型，如 "极氪001"、"比亚迪汉"
        scenario: 用车场景，如 "通勤"、"家用"
        charging_condition: 充电条件，如 "有家充桩"
        family_size: 家庭成员数量
        mileage: 年/日均里程
    """
    budget: Optional[str]
    budget_filled: bool
    
    income: Optional[str]
    income_filled: bool
    
    target_car: Optional[str]
    target_car_filled: bool
    
    scenario: Optional[str]
    scenario_filled: bool
    
    charging_condition: Optional[str]
    charging_filled: bool
    
    family_size: Optional[int]
    family_size_filled: bool
    
    mileage: Optional[str]
    mileage_filled: bool


class SlotStatus(TypedDict):
    """
    槽位状态追踪
    
    记录哪些槽位已填写，哪些仍缺失
    用于判断是否需要追问用户
    """
    filled_slots: List[str]
    missing_slots: List[str]
    all_required_filled: bool


# ========================================
# 工具调用状态
# ========================================

class ToolCallState(TypedDict):
    """
    工具调用状态
    
    追踪 Agent 的工具调用情况
    """
    tool_name: Optional[str]
    tool_args: Optional[dict]
    tool_result: Optional[str]
    tool_error: Optional[str]


# ========================================
# Agent 核心状态
# ========================================

class AgentState(TypedDict):
    """
    LangGraph Agent 核心状态
    
    这是整个 Agent 工作流中传递的核心状态对象，
    包含对话历史、用户信息、槽位状态、工具调用等
    
    使用 Annotated[List, add] 实现消息累加，
    确保多轮对话消息不会丢失
    
    Attributes:
        messages: 对话消息列表，使用 Annotated 实现消息累加
        info_slots: 结构化的信息槽位，追踪已填写和缺失的信息
        slot_status: 槽位状态汇总
        tool_calls: 工具调用记录
        current_step: 当前执行步骤，用于调试和路由
        should_continue: 是否继续执行（用于条件边判断）
        need_more_info: 是否需要向用户追问更多信息
        logic_break_triggered: 是否触发了逻辑熔断
        final_response: 最终响应内容
        recommendations: 推荐车型列表
    """
    # 对话历史 - 使用 add_messages 实现消息累加（LangGraph 标准 reducer）
    messages: Annotated[List[BaseMessage], add_messages]
    
    # 槽位信息
    info_slots: Optional[InfoSlots]
    slot_status: Optional[SlotStatus]
    
    # 工具调用状态
    tool_calls: Optional[List[ToolCallState]]
    
    # 执行控制
    current_step: Optional[str]
    should_continue: bool
    iteration_count: int
    
    # 业务状态
    need_more_info: bool
    logic_break_triggered: bool
    
    # 输出结果
    final_response: Optional[str]
    recommendations: Optional[List[dict]]


# ========================================
# 状态工厂函数
# ========================================

def create_initial_state(user_message: str) -> dict:
    """
    创建初始状态
    
    为新的对话创建一个干净的初始状态对象
    
    Args:
        user_message: 用户的第一条消息
        
    Returns:
        包含初始消息的 Agent 状态字典
    """
    from langchain_core.messages import HumanMessage
    
    return {
        # 初始消息
        "messages": [HumanMessage(content=user_message)],
        
        # 槽位初始化 - 全部为空
        "info_slots": {
            "budget": None,
            "budget_filled": False,
            "income": None,
            "income_filled": False,
            "target_car": None,
            "target_car_filled": False,
            "scenario": None,
            "scenario_filled": False,
            "charging_condition": None,
            "charging_filled": False,
            "family_size": None,
            "family_size_filled": False,
            "mileage": None,
            "mileage_filled": False,
        },
        
        # 槽位状态
        "slot_status": {
            "filled_slots": [],
            "missing_slots": ["budget", "income", "target_car", "scenario", "charging_condition"],
            "all_required_filled": False
        },
        
        # 工具调用
        "tool_calls": [],
        
        # 执行控制
        "current_step": "init",
        "should_continue": True,
        "iteration_count": 0,
        
        # 业务状态
        "need_more_info": False,
        "logic_break_triggered": False,
        
        # 输出
        "final_response": None,
        "recommendations": None
    }


# ========================================
# Redis Checkpointer 配置
# ========================================

def get_redis_checkpointer():
    """
    获取 Checkpointer 实例
    
    用于 LangGraph 状态持久化，支持多轮对话状态恢复
    
    注意：Redis Checkpointer 需要 RedisJSON 模块支持，
    Windows 版本的 Redis 通常不包含此模块，因此默认使用内存存储。
    
    Returns:
        MemorySaver: 内存检查点器实例
    """
    from langgraph.checkpoint.memory import MemorySaver
    
    logger.info("使用内存存储作为 Checkpointer（RedisJSON 模块不可用）")
    return MemorySaver()
