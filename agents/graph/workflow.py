"""
LangGraph 工作流定义：定义多智能体协同的有向图结构。
"""
from langgraph.graph import StateGraph, START, END
import logging

from .state import WorkflowState
from .nodes import hunter_node, miner_node, knowledge_graph_node, validator_node, coach_node

logger = logging.getLogger(__name__)

workflow = StateGraph(WorkflowState)
workflow.add_node("hunter", hunter_node)
workflow.add_node("miner", miner_node)
workflow.add_node("knowledge_graph", knowledge_graph_node)
workflow.add_node("validator", validator_node)
workflow.add_node("coach", coach_node)

workflow.add_edge(START, "hunter")
workflow.add_edge("hunter", "miner")
workflow.add_edge("miner", "knowledge_graph")
workflow.add_edge("knowledge_graph", "validator")


def should_run_coach(state: WorkflowState):
    if state.get("error"):
        logger.warning("Graph 发生错误，提前结束工作流")
        return END
    if state.get("writing_task"):
        return "coach"
    return END


workflow.add_conditional_edges(
    "validator",
    should_run_coach,
    {"coach": "coach", END: END},
)
workflow.add_edge("coach", END)

research_graph = workflow.compile()
