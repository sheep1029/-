from typing import Dict, Any
import logging
from .state import WorkflowState

# 导入现有的路由处理函数
from api.routes.papers import search_papers, PaperSearchRequest
from api.routes.analysis import analyze_paper, PaperAnalysisRequest
from api.routes.citations import validate_citation, CitationValidationRequest
from api.routes.writing import writing_coach, WritingCoachRequest

logger = logging.getLogger(__name__)

async def hunter_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Hunter Agent 节点：负责检索论文
    """
    logger.info(f"LangGraph [Hunter Node]: 开始检索 '{state['keywords']}'")
    try:
        # 调用现有的搜索逻辑
        search_req = PaperSearchRequest(
            keywords=state["keywords"],
            limit=state["max_results"]
        )
        search_result = await search_papers(search_req)
        papers = search_result.get("papers", [])

        step_record = {
            "step": 1,
            "name": "Hunter - 文献检索",
            "status": "completed",
            "result": {
                "keywords": state["keywords"],
                "total_found": len(papers),
                "papers": papers
            }
        }
        return {"papers": papers, "steps_history": [step_record]}
    except Exception as e:
        logger.error(f"Hunter Node 失败: {str(e)}")
        step_record = {
            "step": 1,
            "name": "Hunter - 文献检索",
            "status": "failed",
            "error": str(e)
        }
        return {"error": str(e), "steps_history": [step_record]}

async def miner_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Miner Agent 节点：负责分析论文
    """
    logger.info("LangGraph [Miner Node]: 开始分析论文")
    papers = state.get("papers", [])
    if not papers:
        logger.warning("没有可分析的论文")
        return {"analyses": [], "steps_history": [{
            "step": 2, "name": "Miner - 论文分析", "status": "completed", "result": {"total_analyzed": 0, "analyses": []}
        }]}

    analyses = []
    try:
        # 限制分析前3篇
        for paper in papers[:3]:
            try:
                analysis_req = PaperAnalysisRequest(
                    paper_url=paper.get("url", ""),
                    analysis_type="summary"
                )
                analysis_result = await analyze_paper(analysis_req)
                analyses.append({
                    "paper_id": paper["id"],
                    "title": paper["title"],
                    "analysis": analysis_result.get("analysis", "")
                })
            except Exception as e:
                logger.warning(f"分析单篇论文失败 {paper.get('title')}: {str(e)}")
                continue

        step_record = {
            "step": 2,
            "name": "Miner - 论文分析",
            "status": "completed",
            "result": {
                "total_analyzed": len(analyses),
                "analyses": analyses
            }
        }
        return {"analyses": analyses, "steps_history": [step_record]}
    except Exception as e:
        logger.error(f"Miner Node 失败: {str(e)}")
        step_record = {
            "step": 2, "name": "Miner - 论文分析", "status": "failed", "error": str(e)
        }
        return {"error": str(e), "steps_history": [step_record]}

async def validator_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Validator Agent 节点：负责生成和校验引用
    """
    logger.info("LangGraph [Validator Node]: 开始生成引用")
    papers = state.get("papers", [])
    if not papers:
        return {"citations": [], "steps_history": [{
            "step": 3, "name": "Validator - 引用生成", "status": "completed", "result": {"total_citations": 0, "citations": []}
        }]}

    citations = []
    try:
        # 为前3篇论文生成引用
        for paper in papers[:3]:
            try:
                authors_str = ", ".join(paper["authors"][:3])
                if len(paper["authors"]) > 3:
                    authors_str += " et al."

                citation_text = f"{authors_str} ({paper.get('published_date', '')[:4]}). {paper['title']}. arXiv:{paper['id']}"

                req = CitationValidationRequest(
                    citation=citation_text,
                    format=state.get("citation_format", "bibtex")
                )
                citation_result = await validate_citation(req)

                citations.append({
                    "paper_id": paper["id"],
                    "title": paper["title"],
                    "authors": paper.get("authors", []),
                    "year": paper.get("published_date", "")[:4] if paper.get("published_date") else "",
                    "url": paper.get("url", ""),
                    "formatted_citation": citation_result.get("formatted_citation", "")
                })
            except Exception as e:
                logger.warning(f"生成引用失败: {str(e)}")
                continue

        step_record = {
            "step": 3,
            "name": "Validator - 引用生成",
            "status": "completed",
            "result": {
                "total_citations": len(citations),
                "citations": citations
            }
        }
        return {"citations": citations, "steps_history": [step_record]}
    except Exception as e:
        logger.error(f"Validator Node 失败: {str(e)}")
        step_record = {
            "step": 3, "name": "Validator - 引用生成", "status": "failed", "error": str(e)
        }
        return {"error": str(e), "steps_history": [step_record]}

async def coach_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Coach Agent 节点：负责生成综合报告
    """
    logger.info("LangGraph [Coach Node]: 开始生成综合报告")
    writing_task = state.get("writing_task")
    if not writing_task:
        # 如果没有指定写作任务，直接跳过
        return {"final_report": None}

    papers = state.get("papers", [])
    analyses = state.get("analyses", [])
    citations = state.get("citations", [])
    keywords = state.get("keywords", "")

    try:
        # 组装上下文给 Coach
        report_text = f"# 关于 '{keywords}' 的研究综述\n\n"
        report_text += f"## 搜索结果\n找到 {len(papers)} 篇相关论文\n\n"

        if analyses:
            report_text += "## 论文分析\n"
            for i, analysis in enumerate(analyses[:3], 1):
                report_text += f"\n### {i}. {analysis['title']}\n"
                report_text += f"{analysis['analysis'][:500]}...\n"

        if citations:
            report_text += "\n## 参考文献\n"
            for i, citation in enumerate(citations, 1):
                report_text += f"{i}. {citation['formatted_citation']}\n"

        req = WritingCoachRequest(
            text=report_text,
            style="academic",
            task=writing_task,
            special_requirements=state.get("special_requirements")
        )
        writing_result = await writing_coach(req)
        final_report = writing_result.get("result", "")

        step_record = {
            "step": 4,
            "name": "Coach - 报告生成",
            "status": "completed",
            "result": {
                "report_length": len(final_report),
                "report": final_report
            }
        }
        return {"final_report": final_report, "steps_history": [step_record]}
    except Exception as e:
        logger.error(f"Coach Node 失败: {str(e)}")
        step_record = {
            "step": 4, "name": "Coach - 报告生成", "status": "failed", "error": str(e)
        }
        return {"error": str(e), "steps_history": [step_record]}
