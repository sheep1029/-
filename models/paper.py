"""
论文模型
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class PaperDB(Base):
    """论文数据库模型"""
    __tablename__ = "papers"
    
    id = Column(Integer, primary_key=True, index=True)  # 论文记录的唯一主键
    title = Column(String(500), nullable=False, index=True)  # 论文标题
    authors = Column(Text)  # JSON格式存储作者列表
    abstract = Column(Text)  # 论文摘要
    keywords = Column(Text)  # JSON格式存储关键词
    publication_year = Column(Integer)  # 出版/发表年份
    journal = Column(String(200))  # 发表期刊或会议名称
    doi = Column(String(100), unique=True, index=True)  # DOI 唯一标识符
    arxiv_id = Column(String(50), unique=True, index=True)  # arXiv 上的唯一标识符
    pdf_url = Column(String(500))  # PDF 的网络下载链接
    pdf_path = Column(String(500))  # PDF 在服务器本地存储的相对路径
    full_text = Column(Text)  # 解析后的纯文本全文内容
    embeddings = Column(JSON)  # 存储文本的向量嵌入，用于语义搜索
    metadata = Column(JSON)  # 存储额外的元数据（如引用数、抓取来源等）
    quality_score = Column(Float, default=0.0)  # 系统计算的论文质量评分
    relevance_score = Column(Float, default=0.0)  # 与用户当前研究主题的相关性评分
    is_processed = Column(Boolean, default=False)  # 标记是否已经完成文本提取和向量化处理
    user_id = Column(Integer, index=True)  # 添加该论文的用户ID（如果有的话）
    created_at = Column(DateTime, default=datetime.utcnow)  # 记录入库时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 记录最后更新时间

class Paper(BaseModel):
    """论文响应模型"""
    id: int  # 论文唯一标识
    title: str  # 论文标题
    authors: List[str]  # 作者列表
    abstract: Optional[str] = None  # 论文摘要
    keywords: List[str] = []  # 关键词列表
    publication_year: Optional[int] = None  # 发表年份
    journal: Optional[str] = None  # 期刊/会议名称
    doi: Optional[str] = None  # DOI 标识
    arxiv_id: Optional[str] = None  # arXiv 标识
    pdf_url: Optional[str] = None  # PDF 网络链接
    quality_score: float = 0.0  # 质量评分
    relevance_score: float = 0.0  # 相关性评分
    is_processed: bool = False  # 是否已完成后台处理
    created_at: datetime  # 记录创建时间
    
    class Config:
        from_attributes = True

class PaperCreate(BaseModel):
    """论文创建模型"""
    title: str = Field(..., min_length=1, max_length=500)  # 必填：论文标题
    authors: List[str] = []  # 可选：作者列表
    abstract: Optional[str] = None  # 可选：论文摘要
    keywords: List[str] = []  # 可选：关键词列表
    publication_year: Optional[int] = None  # 可选：发表年份
    journal: Optional[str] = None  # 可选：期刊名称
    doi: Optional[str] = None  # 可选：DOI
    arxiv_id: Optional[str] = None  # 可选：arXiv ID
    pdf_url: Optional[str] = None  # 可选：PDF网络链接

class PaperUpdate(BaseModel):
    """论文更新模型"""
    title: Optional[str] = None  # 可选更新：论文标题
    authors: Optional[List[str]] = None  # 可选更新：作者列表
    abstract: Optional[str] = None  # 可选更新：论文摘要
    keywords: Optional[List[str]] = None  # 可选更新：关键词列表
    publication_year: Optional[int] = None  # 可选更新：发表年份
    journal: Optional[str] = None  # 可选更新：期刊名称
    quality_score: Optional[float] = None  # 可选更新：质量评分
    relevance_score: Optional[float] = None  # 可选更新：相关性评分

class PaperSearch(BaseModel):
    """论文搜索模型"""
    query: str = Field(..., min_length=1)  # 必填：搜索查询词
    filters: Dict[str, Any] = {}  # 可选：额外的过滤条件（如年份范围）
    sort_by: str = "relevance"  # 排序依据，默认按相关度
    limit: int = Field(default=20, ge=1, le=100)  # 返回的最大结果数
    offset: int = Field(default=0, ge=0)  # 分页偏移量

class PaperAnalysis(BaseModel):
    """单篇论文深度分析结果"""
    paper_id: int  # 关联的论文ID
    summary: str  # 论文核心总结
    key_findings: List[str]  # 提取出的关键发现列表
    methodology: str  # 使用的研究方法概述
    limitations: List[str]  # 论文存在的局限性
    future_work: List[str]  # 论文中提及的未来工作方向
    novelty_score: float  # 新颖度评分
    impact_score: float  # 影响力评分
    confidence_score: float  # 分析置信度评分