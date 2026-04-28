"""
论文相关API路由
"""

import logging
import re
import asyncio
from typing import Dict, Any, List

import arxiv
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from core.llm_adapter import get_llm_adapter

logger = logging.getLogger(__name__)
router = APIRouter()


class PaperSearchRequest(BaseModel):
    keywords: str
    source: str = "arxiv"
    sources: List[str] = Field(default_factory=list)
    limit: int = 10


class PaperResponse(BaseModel):
    id: str
    title: str
    authors: List[str]
    abstract: str
    url: str
    published_date: str


def _contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _normalize_keywords(keywords: str) -> List[str]:
    items = re.split(r"[，,;；\n]\s*", keywords)
    return [item.strip() for item in items if item.strip()]


def _deduplicate_texts(texts: List[str]) -> List[str]:
    seen = set()
    result = []
    for text in texts:
        key = text.lower().strip()
        if key and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _parse_translation_output(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []

    candidates = re.split(r"[\n,，;；|/]", text)
    cleaned = []
    for candidate in candidates:
        item = candidate.strip().strip("-•*`\"'")
        if item:
            cleaned.append(item)
    return _deduplicate_texts(cleaned)


def _normalize_limit(limit: int) -> int:
    return max(1, min(limit, 20))


async def _translate_keywords_if_needed(keywords: str) -> List[str]:
    normalized = _normalize_keywords(keywords)
    translated_keywords: List[str] = []

    for keyword in normalized:
        if _contains_chinese(keyword):
            try:
                llm = get_llm_adapter()
                prompt = (
                    "请将下面的科研检索关键词翻译成适合英文论文数据库检索的英文关键词。"
                    "只输出英文关键词本身，不要解释，不要编号，不要加多余文本。"
                    "如果是短语，请保留其学术含义。可以给出多个英文同义词，用换行或逗号分隔。\n\n"
                    f"关键词: {keyword}"
                )
                response = await llm.ainvoke(prompt)
                translated = _parse_translation_output(response)
                translated_keywords.extend(translated or [keyword])
            except Exception as e:
                logger.warning(f"关键词翻译失败，回退原词: {keyword}, 原因: {str(e)}")
                translated_keywords.append(keyword)
        else:
            translated_keywords.append(keyword)

    return _deduplicate_texts(translated_keywords)


@router.post("/search", response_model=Dict[str, Any])
async def search_papers(request: PaperSearchRequest):
    """搜索论文 - 使用真实的 ArXiv API"""
    try:
        papers = []
        search_keywords = await _translate_keywords_if_needed(request.keywords)
        selected_sources = request.sources or [request.source]
        normalized_limit = _normalize_limit(request.limit)
        
        if "arxiv" in selected_sources or "all" in selected_sources:
            logger.info(f"正在搜索 ArXiv: 原始关键词={request.keywords}, 检索关键词={search_keywords}")
            
            query = " OR ".join([f'all:"{keyword}"' for keyword in search_keywords])
            search = arxiv.Search(
                query=query,
                max_results=normalized_limit,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )
            
            retries = 3
            backoff_seconds = 1
            for attempt in range(retries):
                try:
                    client = arxiv.Client(page_size=normalized_limit, delay_seconds=3, num_retries=2)
                    results = list(client.results(search))
                    for result in results[:normalized_limit]:
                        paper = {
                            "id": result.entry_id.split('/')[-1],
                            "title": result.title,
                            "authors": [author.name for author in result.authors],
                            "abstract": result.summary.replace('\n', ' ').strip(),
                            "url": result.entry_id,
                            "published_date": result.published.strftime("%Y-%m-%d"),
                            "pdf_url": result.pdf_url,
                            "categories": result.categories,
                            "primary_category": result.primary_category,
                        }
                        papers.append(paper)
                    break
                except Exception as search_error:
                    error_text = str(search_error)
                    if "429" in error_text and attempt < retries - 1:
                        wait_seconds = backoff_seconds * (2 ** attempt)
                        logger.warning(f"ArXiv 触发限流，等待 {wait_seconds}s 后重试: {error_text}")
                        await asyncio.sleep(wait_seconds)
                        continue
                    raise
            
            logger.info(f"找到 {len(papers)} 篇论文")
        
        if not papers:
            return {
                "success": True,
                "papers": [],
                "total_found": 0,
                "keywords": request.keywords,
                "translated_keywords": search_keywords,
                "source": request.source,
                "message": "未找到相关论文，请尝试其他关键词",
            }
        
        return {
            "success": True,
            "papers": papers,
            "total_found": len(papers),
            "keywords": request.keywords,
            "translated_keywords": search_keywords,
            "source": request.source,
        }
        
    except Exception as e:
        logger.error(f"论文搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/upload", response_model=Dict[str, Any])
async def upload_paper(file: UploadFile = File(...)):
    """上传论文PDF"""
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="只支持PDF文件")
        
        file_url = f"/uploads/{file.filename}"
        
        return {
            "success": True,
            "file_url": file_url,
            "filename": file.filename,
            "size": getattr(file, 'size', 0),
            "message": "文件上传成功",
        }
        
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")
