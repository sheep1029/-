from langgraph.graph import StateGraph, START, END
import logging

from .state import WorkflowState
from .nodes import hunter_node, miner_node, validator_node, coach_node

logger = logging.getLogger(__name__)

# 初始化状态图
workflow = StateGraph(WorkflowState)

# 1. 添加节点 (Nodes)
workflow.add_node("hunter", hunter_node)
workflow.add_node("miner", miner_node)
workflow.add_node("validator", validator_node)
workflow.add_node("coach", coach_node)

# 2. 定义控制流边 (Edges)
# 设置入口节点
workflow.add_edge(START, "hunter")

# 线性工作流: 搜索 -> 分析 -> 生成引用
workflow.add_edge("hunter", "miner")
workflow.add_edge("miner", "validator")

# 条件跳转函数
def should_run_coach(state: WorkflowState):
    """
    判断是否需要执行Coach节点来生成综合报告
    """
    if state.get("error"):
        logger.warning("Graph 发生错误，提前结束工作流")
        return END
        
    if state.get("writing_task"):
        return "coach"
    
    return END

# 添加条件边：验证完成后，根据用户是否请求写作任务决定去向
workflow.add_conditional_edges(
    "validator",
    should_run_coach,
    {
        "coach": "coach",
        END: END
    }
)

# Coach 执行完后直接结束
workflow.add_edge("coach", END)

# 3. 编译成可执行应用 (Compiled App)
research_graph = workflow.compile()
