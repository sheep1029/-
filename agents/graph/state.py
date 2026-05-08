"""
LangGraph 状态定义：声明工作流在节点间流转时共享的数据结构。
"""
from typing import TypedDict, List, Dict, Any, Optional
import operator
from typing import Annotated

class WorkflowState(TypedDict):
    """
    定义 LangGraph 工作流的共享状态
    """
    # 输入参数 (由前端或外部触发工作流时传入)
    keywords: str  # 必填：用于论文检索的关键词或搜索语句
    max_results: int  # 必填：期望检索回来的论文最大数量限制
    citation_format: str  # 必填：引用的格式要求，例如 "APA", "IEEE", "MLA" 等
    writing_task: Optional[str]  # 选填：具体的写作任务描述或目标（如："写一篇关于大模型幻觉的综述"）
    special_requirements: Optional[str]  # 选填：用户的特殊要求，比如"重点关注2023年之后的论文"或"要求使用中文输出"
    sources: List[str]  # 必填：检索的来源渠道列表，例如 ["arxiv", "local_db"]
    
    # 过程数据与输出 (在各个 Agent 节点流转过程中逐渐填充的数据)
    papers: List[Dict[str, Any]]  # 检索节点(Researcher)输出的结果：包含找到的论文元数据(标题、作者、摘要等)
    analyses: List[Dict[str, Any]]  # 分析节点(Analyst)输出的结果：对检索到的论文进行的深度分析、摘要或创新点提取
    citations: List[Dict[str, Any]]  # 引用节点(Citation)输出的结果：根据 citation_format 格式化后的引用列表数据
    final_report: Optional[str]  # 写作节点(Writer)输出的结果：最终生成的研究报告、综述或文章内容
    
    # 步骤记录 (用于展示执行过程)
    # Annotated 与 operator.add 结合，表示这是一个"追加"更新的字段。
    # 当不同节点返回 steps_history 时，LangGraph 会自动将新列表追加到旧列表后，而不是覆盖。
    steps_history: Annotated[List[Dict[str, Any]], operator.add]
    
    # 错误信息
    error: Optional[str]  # 记录在工作流任何节点执行过程中捕获的致命错误信息，用于异常处理和状态中断
