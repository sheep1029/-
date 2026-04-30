from typing import Dict, Any, List
import logging
import re
from .state import WorkflowState

# 导入现有的路由处理函数
from api.routes.papers import search_papers, PaperSearchRequest
from api.routes.analysis import analyze_paper, PaperAnalysisRequest
from api.routes.citations import validate_citation, CitationValidationRequest
from api.routes.writing import writing_coach, WritingCoachRequest

logger = logging.getLogger(__name__)


def _extract_year(paper: Dict[str, Any]) -> int:
    """从论文字段中提取年份"""
    for key in ("published_date", "published", "year"):
        value = paper.get(key)
        if not value:
            continue
        if isinstance(value, int):
            return value
        match = re.search(r"(19|20)\d{2}", str(value))
        if match:
            return int(match.group(0))
    return 0


async def hunter_node(state: WorkflowState) -> Dict[str, Any]:
    """Hunter Agent 节点：负责检索论文"""
    logger.info(f"LangGraph [Hunter Node]: 开始检索 '{state['keywords']}'")
    try:
        search_req = PaperSearchRequest(
            keywords=state["keywords"],
            limit=state["max_results"],
            source="arxiv",
            sources=["arxiv"],
        )
        search_result = await search_papers(search_req)
        papers = search_result.get("papers", [])
        step_record = {
            "step": 1,
            "name": "Hunter - 文献检索",
            "status": "completed",
            "result": {"keywords": state["keywords"], "total_found": len(papers), "papers": papers},
        }
        return {"papers": papers, "steps_history": [step_record]}
    except Exception as e:
        logger.error(f"Hunter Node 失败: {str(e)}")
        return {"error": str(e), "steps_history": [{"step": 1, "name": "Hunter - 文献检索", "status": "failed", "error": str(e)}]}


async def miner_node(state: WorkflowState) -> Dict[str, Any]:
    """Miner Agent 节点：负责分析论文"""
    logger.info("LangGraph [Miner Node]: 开始分析论文")
    papers = state.get("papers", [])
    if not papers:
        logger.warning("没有可分析的论文")
        return {"analyses": [], "steps_history": [{"step": 2, "name": "Miner - 论文分析", "status": "completed", "result": {"total_analyzed": 0, "analyses": []}}]}

    analyses = []
    try:
        for paper in papers[:3]:
            try:
                analysis_req = PaperAnalysisRequest(paper_url=paper.get("url", ""), analysis_type="summary")
                analysis_result = await analyze_paper(analysis_req)
                analyses.append({
                    "paper_id": paper.get("id", ""),
                    "title": paper.get("title", ""),
                    "authors": paper.get("authors", []),
                    "year": _extract_year(paper),
                    "analysis": analysis_result.get("analysis", ""),
                })
            except Exception as e:
                logger.warning(f"分析单篇论文失败 {paper.get('title')}: {str(e)}")
                continue

        step_record = {
            "step": 2,
            "name": "Miner - 论文分析",
            "status": "completed",
            "result": {"total_analyzed": len(analyses), "analyses": analyses},
        }
        return {"analyses": analyses, "steps_history": [step_record]}
    except Exception as e:
        logger.error(f"Miner Node 失败: {str(e)}")
        return {"error": str(e), "steps_history": [{"step": 2, "name": "Miner - 论文分析", "status": "failed", "error": str(e)}]}


async def knowledge_graph_node(state: WorkflowState) -> Dict[str, Any]:
    """KnowledgeGraphBuilder 节点：从论文和分析结果中抽取知识图谱"""
    logger.info("LangGraph [KnowledgeGraph Node]: 开始构建知识图谱")

    papers = state.get("papers", [])
    analyses = state.get("analyses", [])

    if not papers and not analyses:
        step_record = {"step": 3, "name": "KnowledgeGraph - 知识图谱构建", "status": "completed", "result": {"total_nodes": 0, "total_edges": 0, "message": "没有可构建图谱的数据"}}
        return {"knowledge_graph": {"nodes": [], "edges": [], "summary": {"message": "没有可构建图谱的数据"}}, "steps_history": [step_record]}

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    node_map = set()

    def add_node(node_id: str, node_type: str, label: str, properties: Dict[str, Any] = None):
        if node_id in node_map:
            return
        node_map.add(node_id)
        nodes.append({"id": node_id, "type": node_type, "label": label, "properties": properties or {}})

    def add_edge(source: str, target: str, edge_type: str, properties: Dict[str, Any] = None):
        if source and target:
            edges.append({"source": source, "target": target, "type": edge_type, "properties": properties or {}})

    topic = state.get("keywords", "research topic")
    topic_node_id = f"topic_{re.sub(r'[^a-zA-Z0-9]+', '_', topic).strip('_').lower() or 'research'}"
    add_node(topic_node_id, "Topic", topic, {"keywords": topic})

    task_keywords = {
        "code": ["code generation", "code completion", "program synthesis"],
        "llm": ["large language models", "foundation models", "instruction tuning"],
        "retrieval": ["retrieval", "search", "information retrieval"],
        "reasoning": ["reasoning", "chain of thought", "planning"],
    }
    dataset_candidates = [
        ("dataset_arxiv", "ArXiv"),
        ("dataset_cora", "Cora"),
        ("dataset_pubmed", "PubMed"),
        ("dataset_wmt", "WMT"),
        ("dataset_imagenet", "ImageNet"),
        ("dataset_cifar", "CIFAR"),
        ("dataset_squad", "SQuAD"),
        ("dataset_glue", "GLUE"),
        ("dataset_codesearchnet", "CodeSearchNet"),
        ("dataset_the_stack", "The Stack"),
    ]
    metric_candidates = ["Accuracy", "F1", "BLEU", "ROUGE", "AUC", "Precision", "Recall", "pass@k", "Perplexity"]
    limitation_candidates = ["Data Contamination", "Bias", "Overfitting", "Scalability", "Privacy", "Ethics"]

    detected_tasks = set()
    detected_methods = set()
    detected_datasets = set()
    detected_metrics = set()
    detected_limitations = set()

    for paper in papers:
        paper_id = f"paper_{paper.get('id', 'unknown')}"
        paper_title = paper.get("title", "Unknown Title")
        paper_text = " ".join([paper_title, paper.get("abstract", ""), str(paper.get("categories", [])), str(paper.get("primary_category", ""))]).lower()
        add_node(paper_id, "Paper", paper_title, {"title": paper_title, "authors": paper.get("authors", []), "year": _extract_year(paper), "source": paper.get("source", "arxiv"), "url": paper.get("url", "")})
        add_edge(paper_id, topic_node_id, "ADDRESSES", {"evidence": "paper matched current search topic"})

        for task_name, keywords_list in task_keywords.items():
            if any(keyword in paper_text for keyword in keywords_list):
                task_id = f"task_{task_name}"
                task_label = task_name.replace("_", " ").title()
                add_node(task_id, "Task", task_label, {"description": task_label})
                add_edge(paper_id, task_id, "ADDRESSES", {"evidence": f"matched {task_name}"})
                detected_tasks.add(task_label)

        if any(keyword in paper_text for keyword in ["transformer", "attention"]):
            add_node("method_transformer", "Method", "Transformer", {"description": "Attention-based sequence modeling"})
            add_edge(paper_id, "method_transformer", "USES_METHOD", {"evidence": "matched transformer/attention"})
            detected_methods.add("Transformer")

        if any(keyword in paper_text for keyword in ["bert", "pretrain", "pre-trained", "pretraining"]):
            add_node("method_pretraining", "Method", "Pretraining", {"description": "Pre-trained language modeling"})
            add_edge(paper_id, "method_pretraining", "USES_METHOD", {"evidence": "matched pretraining"})
            detected_methods.add("Pretraining")

        for dataset_id, dataset_label in dataset_candidates:
            if dataset_label.lower() in paper_text:
                add_node(dataset_id, "Dataset", dataset_label, {"domain": "academic dataset"})
                add_edge(paper_id, dataset_id, "USES_DATASET", {"evidence": f"matched {dataset_label}"})
                detected_datasets.add(dataset_label)

        for metric_label in metric_candidates:
            if metric_label.lower() in paper_text:
                metric_id = f"metric_{re.sub(r'[^a-zA-Z0-9]+', '_', metric_label).lower()}"
                add_node(metric_id, "Metric", metric_label, {"description": f"Evaluation metric: {metric_label}"})
                add_edge(paper_id, metric_id, "EVALUATED_BY", {"evidence": f"matched {metric_label}"})
                detected_metrics.add(metric_label)

        for limitation_label in limitation_candidates:
            if limitation_label.lower() in paper_text:
                limitation_id = f"limitation_{re.sub(r'[^a-zA-Z0-9]+', '_', limitation_label).lower()}"
                add_node(limitation_id, "Limitation", limitation_label, {"description": limitation_label})
                add_edge(paper_id, limitation_id, "HAS_LIMITATION", {"evidence": f"matched {limitation_label}"})
                detected_limitations.add(limitation_label)

    summary = {
        "topic": topic,
        "paper_count": len(papers),
        "analysis_count": len(analyses),
        "main_tasks": sorted(detected_tasks),
        "main_methods": sorted(detected_methods),
        "main_datasets": sorted(detected_datasets),
        "common_metrics": sorted(detected_metrics),
        "observed_limitations": sorted(detected_limitations),
    }
    knowledge_graph = {"nodes": nodes, "edges": edges, "summary": summary}
    step_record = {
        "step": 3,
        "name": "KnowledgeGraph - 知识图谱构建",
        "status": "completed",
        "result": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "summary": summary,
            "nodes": nodes,
            "edges": edges,
            "knowledge_graph": knowledge_graph,
        },
    }
    return {"knowledge_graph": knowledge_graph, "steps_history": [step_record]}


async def validator_node(state: WorkflowState) -> Dict[str, Any]:
    """Validator Agent 节点：负责校验引用"""
    logger.info("LangGraph [Validator Node]: 开始校验引用")
    analyses = state.get("analyses", [])
    if not analyses:
        return {"citations": [], "steps_history": [{"step": 4, "name": "Validator - 引用校验", "status": "completed", "result": {"total_validated": 0, "citations": []}}]}

    citations = []
    try:
        for analysis in analyses[:3]:
            citation_req = CitationValidationRequest(
                citation=str({
                    "title": analysis.get("title", ""),
                    "authors": analysis.get("authors", []),
                    "year": analysis.get("year", 2024),
                    "journal": "",
                    "doi": "",
                    "arxiv_id": "",
                }),
                format=state.get("citation_format", "bibtex"),
            )
            citation_result = await validate_citation(citation_req)
            citations.append({
                "title": analysis.get("title", "Unknown Title"),
                "authors": analysis.get("authors", []),
                "year": analysis.get("year", 2024),
                "formatted_citation": citation_result.get("formatted_citation", citation_result.get("citation", "")),
                "raw_result": citation_result,
            })

        step_record = {"step": 4, "name": "Validator - 引用校验", "status": "completed", "result": {"total_validated": len(citations), "citations": citations}}
        return {"citations": citations, "steps_history": [step_record]}
    except Exception as e:
        logger.error(f"Validator Node 失败: {str(e)}")
        return {"error": str(e), "steps_history": [{"step": 4, "name": "Validator - 引用校验", "status": "failed", "error": str(e)}]}


async def coach_node(state: WorkflowState) -> Dict[str, Any]:
    """Coach Agent 节点：负责生成最终报告"""
    logger.info("LangGraph [Coach Node]: 开始生成报告")
    keywords = state.get("keywords", "")
    analyses = state.get("analyses", [])
    knowledge_graph = state.get("knowledge_graph", {})

    try:
        if not analyses:
            report_text = f"# 关于 '{keywords}' 的研究综述\n\n暂无足够分析结果生成详细报告。"
            return {"final_report": report_text, "steps_history": [{"step": 5, "name": "Coach - 报告生成", "status": "completed", "result": {"report_length": len(report_text), "report": report_text}}]}

        prompt = f"""
请基于以下论文分析和知识图谱，生成一份结构化的学术研究综述。

研究主题: {keywords}

论文分析:
{analyses}

知识图谱摘要:
{knowledge_graph.get('summary', {})}

要求：
1. 包含研究背景、核心方法、关键发现、研究空白和未来方向
2. 如有知识图谱中的方法/数据集/任务/指标信息，请自然融入综述
3. 输出 Markdown 格式
"""
        writing_result = await writing_coach(WritingCoachRequest(text=prompt, style="formal", task="improve", special_requirements=state.get("special_requirements")))
        final_report = writing_result.get("result", "")
        step_record = {"step": 5, "name": "Coach - 报告生成", "status": "completed", "result": {"report_length": len(final_report), "report": final_report}}
        return {"final_report": final_report, "steps_history": [step_record]}
    except Exception as e:
        logger.error(f"Coach Node 失败: {str(e)}")
        return {"error": str(e), "steps_history": [{"step": 5, "name": "Coach - 报告生成", "status": "failed", "error": str(e)}]}
