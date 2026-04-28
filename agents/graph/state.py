from typing import TypedDict, List, Dict, Any, Optional
import operator
from typing import Annotated

class WorkflowState(TypedDict):
    """
    定义 LangGraph 工作流的共享状态
    """
    # 输入参数
    keywords: str
    max_results: int
    citation_format: str
    writing_task: Optional[str]
    special_requirements: Optional[str]
    sources: List[str]
    
    # 过程数据与输出
    papers: List[Dict[str, Any]]
    analyses: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    final_report: Optional[str]
    
    # 步骤记录 (用于展示执行过程)
    steps_history: Annotated[List[Dict[str, Any]], operator.add]
    
    # 错误信息
    error: Optional[str]
