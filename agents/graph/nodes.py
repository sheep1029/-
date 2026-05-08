"""
LangGraph 工作流节点：包含各个智能体在图流转中的具体执行逻辑。
"""
from typing import Dict, Any, List
import logging
import re
import json
import asyncio
from .state import WorkflowState

from core.llm_adapter import get_llm_adapter
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

    # 设置中心节点（搜索关键词）
    topic = state.get("keywords", "research topic")
    topic_node_id = f"topic_{re.sub(r'[^a-zA-Z0-9]+', '_', topic).strip('_').lower() or 'research'}"
    add_node(topic_node_id, "Topic", topic, {"keywords": topic})

    task_keywords = {
        # 任务类型映射：字典的 key 是内部的短标识，value 是该任务可能在论文中出现的同义关键词列表
        "code": ["code generation", "code completion", "program synthesis"],  # 代码相关任务：代码生成、代码补全、程序综合
        "llm": ["large language models", "foundation models", "instruction tuning"],  # 大语言模型相关任务：大模型、基础模型、指令微调
        "retrieval": ["retrieval", "search", "information retrieval"],  # 检索相关任务：检索、搜索、信息检索
        "reasoning": ["reasoning", "chain of thought", "planning"],  # 推理相关任务：推理、思维链、规划
    }
    
    dataset_candidates = [
        # 预设的知名数据集列表，格式为：(节点ID标识, 数据集显示名称)
        ("dataset_arxiv", "ArXiv"),  # 学术论文数据集
        ("dataset_cora", "Cora"),  # 论文引用网络数据集
        ("dataset_pubmed", "PubMed"),  # 生物医学文献数据集
        ("dataset_wmt", "WMT"),  # 机器翻译评估数据集
        ("dataset_imagenet", "ImageNet"),  # 计算机视觉图像分类数据集
        ("dataset_cifar", "CIFAR"),  # 计算机视觉图像数据集 (CIFAR-10/100)
        ("dataset_squad", "SQuAD"),  # 斯坦福问答数据集
        ("dataset_glue", "GLUE"),  # 通用语言理解评估基准
        ("dataset_codesearchnet", "CodeSearchNet"),  # 代码搜索与理解数据集
        ("dataset_the_stack", "The Stack"),  # 大规模代码预训练数据集
    ]
    
    # 预设的常用评估指标列表
    metric_candidates = [
        "Accuracy",  # 准确率，常用于分类任务
        "F1",  # F1分数，精确率和召回率的调和平均，常用于分类和检索
        "BLEU",  # 机器翻译常用评估指标
        "ROUGE",  # 文本摘要常用评估指标
        "AUC",  # ROC曲线下面积，用于评估二分类模型
        "Precision",  # 精确率
        "Recall",  # 召回率
        "pass@k",  # 代码生成任务常用评估指标
        "Perplexity"  # 困惑度，语言模型常用评估指标
    ]
    
    # 预设的常见研究局限性或挑战列表
    limitation_candidates = [
        "Data Contamination",  # 数据污染（例如测试集泄露到训练集中）
        "Bias",  # 模型或数据偏见
        "Overfitting",  # 过拟合
        "Scalability",  # 可扩展性问题
        "Privacy",  # 隐私保护问题
        "Ethics"  # 伦理道德问题
    ]

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

    # ==== LLM 兜底抽取逻辑开始 ====
    try:
        from core.config import get_config
        config = get_config()
        llm = get_llm_adapter() if config.llm.api_key else None
    except Exception as e:
        logger.warning(f"获取 LLM 适配器失败，跳过 LLM 兜底抽取: {e}")
        llm = None

    if llm and analyses:
        logger.info("LangGraph [KnowledgeGraph Node]: 启动 LLM 兜底抽取实体")

        async def extract_entities_for_paper(analysis_dict: Dict[str, Any]) -> tuple:
            paper_id = f"paper_{analysis_dict.get('paper_id', 'unknown')}"
            text = f"Title: {analysis_dict.get('title', '')}\nAbstract/Analysis: {analysis_dict.get('analysis', '')}"
            prompt = f"""
请从以下学术论文分析文本中提取核心的结构化学术实体。
不要提取太宽泛的词汇，重点提取以下类别中未被充分涵盖的具体专业词汇：
- tasks: 具体的研究任务（如：指令微调，知识蒸馏，图像分割等）
- methods: 使用的具体算法、模型或技术名称（如：LoRA, ResNet, PPO等）
- datasets: 使用的数据集名称
- metrics: 评估指标名称
- limitations: 具体的局限性或挑战

必须严格只输出合法的 JSON 对象，不包含任何 Markdown 标记或多余的文字说明，格式如下：
{{
    "tasks": ["任务1", "任务2"],
    "methods": ["方法1"],
    "datasets": [],
    "metrics": ["指标1"],
    "limitations": []
}}

文本内容：
{text}
"""
            try:
                res = await llm.ainvoke(prompt)
                # 清理返回文本中的 markdown 代码块标记
                cleaned = re.sub(r'```json|```', '', res).strip()
                return paper_id, json.loads(cleaned)
            except Exception as e:
                logger.warning(f"LLM entity extraction failed for {paper_id}: {e}")
                return paper_id, {}

        # 并发请求 LLM
        tasks_list = [extract_entities_for_paper(a) for a in analyses]
        llm_results = await asyncio.gather(*tasks_list)

        for paper_id, entities in llm_results:
            if not entities:
                continue
            
            # 将 LLM 抽取到的实体补充进图谱
            for t in entities.get("tasks", []):
                t_id = f"task_{re.sub(r'[^a-zA-Z0-9]+', '_', t).lower()}"
                add_node(t_id, "Task", t.title(), {"description": t})
                add_edge(paper_id, t_id, "ADDRESSES", {"evidence": "LLM extracted"})
                detected_tasks.add(t.title())
                
            for m in entities.get("methods", []):
                m_id = f"method_{re.sub(r'[^a-zA-Z0-9]+', '_', m).lower()}"
                add_node(m_id, "Method", m.title(), {"description": m})
                add_edge(paper_id, m_id, "USES_METHOD", {"evidence": "LLM extracted"})
                detected_methods.add(m.title())
                
            for d in entities.get("datasets", []):
                d_id = f"dataset_{re.sub(r'[^a-zA-Z0-9]+', '_', d).lower()}"
                add_node(d_id, "Dataset", d, {"domain": "academic dataset"})
                add_edge(paper_id, d_id, "USES_DATASET", {"evidence": "LLM extracted"})
                detected_datasets.add(d)
                
            for m in entities.get("metrics", []):
                m_id = f"metric_{re.sub(r'[^a-zA-Z0-9]+', '_', m).lower()}"
                add_node(m_id, "Metric", m, {"description": f"Evaluation metric: {m}"})
                add_edge(paper_id, m_id, "EVALUATED_BY", {"evidence": "LLM extracted"})
                detected_metrics.add(m)
                
            for l in entities.get("limitations", []):
                l_id = f"limitation_{re.sub(r'[^a-zA-Z0-9]+', '_', l).lower()}"
                add_node(l_id, "Limitation", l, {"description": l})
                add_edge(paper_id, l_id, "HAS_LIMITATION", {"evidence": "LLM extracted"})
                detected_limitations.add(l)
    # ==== LLM 兜底抽取逻辑结束 ====

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
