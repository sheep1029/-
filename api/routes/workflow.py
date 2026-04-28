"""
工作流API路由 - 协调多个智能体完成复杂任务
"""

import uuid
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import logging
import asyncio

from agents.graph.workflow import research_graph

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic模型
class WorkflowRequest(BaseModel):
    keywords: str = Field(..., description="研究关键词")
    analysis_type: str = "summary"  # summary, innovation, comparison, comprehensive
    citation_format: str = Field(default="bibtex", description="引用格式要求")
    writing_task: Optional[str] = Field(default=None, description="报告写作任务描述")
    special_requirements: Optional[str] = Field(default=None, description="用户特殊要求")
    limit: int = Field(default=5, description="最大搜索结果数")
    sources: List[str] = Field(default_factory=lambda: ["arxiv", "ieee"], description="数据来源，可多选")

class WorkflowStatus(BaseModel):
    workflow_id: str
    status: str  # running, completed, failed
    current_step: str
    progress: int  # 0-100

@router.post("/complete", response_model=Dict[str, Any])
async def complete_workflow(request: WorkflowRequest):
    """
    执行完整的科研工作流：检索 -> 分析 -> 生成引用 -> 输出报告
    基于 LangGraph 的底层编排实现
    """
    workflow_id = str(uuid.uuid4())
    logger.info(f"开始执行工作流 [{workflow_id}]: {request.keywords}")

    try:
        # 1. 构造初始状态
        initial_state = {
            "keywords": request.keywords,
            "max_results": request.limit,
            "citation_format": request.citation_format,
            "writing_task": request.writing_task,
            "special_requirements": request.special_requirements,
            "sources": request.sources,
            "papers": [],
            "analyses": [],
            "citations": [],
            "final_report": None,
            "steps_history": [],
            "error": None
        }

        # 2. 调用 LangGraph 编译的图
        final_state = await research_graph.ainvoke(initial_state)

        # 3. 检查执行过程中是否有节点报错
        if final_state.get("error"):
            logger.error(f"工作流执行中止, 错误: {final_state['error']}")
            # 可以选择在这里抛出 HTTP 异常，或者将错误包装在结果中返回
            # raise HTTPException(status_code=500, detail=final_state["error"])

        # 4. 将最终状态转化为旧 API 的格式，保证前端无需修改
        results = {
            "success": not bool(final_state.get("error")),
            "workflow_id": workflow_id,
            "status": "completed" if not final_state.get("error") else "failed",
            "steps": final_state.get("steps_history", []),
            "final_report": final_state.get("final_report")
        }

        logger.info(f"工作流执行完成 [{workflow_id}]")
        return results

    except Exception as e:
        logger.error(f"工作流执行异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"工作流执行失败: {str(e)}")

@router.post("/search-and-analyze", response_model=Dict[str, Any])
async def search_and_analyze(request: WorkflowRequest):
    """
    简化工作流：搜索 + 分析
    只执行搜索和分析步骤
    """
    try:
        results = {
            "status": "running",
            "steps": []
        }

        # 步骤 1: 搜索论文
        from api.routes.papers import search_papers, PaperSearchRequest

        search_result = await search_papers(PaperSearchRequest(
            keywords=request.keywords,
            sources=["arxiv"],
            limit=request.limit
        ))

        papers = search_result.get("papers", [])
        results["steps"].append({
            "step": 1,
            "name": "搜索论文",
            "status": "completed",
            "papers": papers
        })

        if not papers:
            raise HTTPException(status_code=404, detail="未找到相关论文")

        # 步骤 2: 分析第一篇论文
        from api.routes.analysis import analyze_paper, PaperAnalysisRequest

        first_paper = papers[0]
        analysis_result = await analyze_paper(PaperAnalysisRequest(
            paper_url=first_paper["url"],
            analysis_type=request.analysis_type
        ))

        results["steps"].append({
            "step": 2,
            "name": "分析论文",
            "status": "completed",
            "analysis": analysis_result
        })

        results["status"] = "completed"
        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索和分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"执行失败: {str(e)}")

@router.get("/status/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """获取工作流状态"""
    try:
        # 这里可以实现工作流状态跟踪
        # 暂时返回模拟状态
        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "progress": 100,
            "message": "工作流已完成"
        }
    except Exception as e:
        logger.error(f"获取工作流状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
