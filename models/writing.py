"""
写作模型
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class WritingDB(Base):
    """写作数据库模型"""
    __tablename__ = "writing"
    
    id = Column(Integer, primary_key=True, index=True)  # 写作记录的唯一主键
    title = Column(String(200), nullable=False)  # 写作产出物的标题
    writing_type = Column(String(50), nullable=False)  # 写作类型：如 review(综述), summary(总结), critique(评论), proposal(提案)
    content = Column(Text)  # 完整的最终文本内容 (通常是 Markdown 格式)
    outline = Column(JSON)  # 文章的树状大纲结构
    sections = Column(JSON)  # 分章节的具体内容映射表
    citations = Column(JSON)  # 格式化后的引用文献列表
    metadata = Column(JSON)  # 其他扩展元数据
    quality_score = Column(Float, default=0.0)  # 系统或大模型给出的文章质量评估分数
    word_count = Column(Integer, default=0)  # 文章总字数/词数统计
    status = Column(String(20), default="draft")  # 当前状态：draft(草稿), reviewing(审核中), completed(已完成)
    paper_ids = Column(JSON)  # 写作过程中参考的核心论文ID列表
    user_id = Column(Integer, index=True)  # 触发生成该文本的用户ID
    task_id = Column(Integer, index=True)  # 负责生成该文本的异步任务ID
    created_at = Column(DateTime, default=datetime.utcnow)  # 记录创建时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 记录最后修改时间

class Writing(BaseModel):
    """写作响应模型"""
    id: int  # 写作记录ID
    title: str  # 文章标题
    writing_type: str  # 写作类型
    content: Optional[str] = None  # 完整文章内容
    outline: List[Dict[str, Any]] = []  # 文章大纲
    sections: Dict[str, str] = {}  # 章节名与内容的映射
    citations: List[Dict[str, Any]] = []  # 引用列表
    quality_score: float = 0.0  # 文章质量得分
    word_count: int = 0  # 文章字数
    status: str = "draft"  # 当前状态
    created_at: datetime  # 创建时间
    
    class Config:
        from_attributes = True

class WritingCreate(BaseModel):
    """写作创建模型"""
    title: str = Field(..., min_length=1, max_length=200)  # 必填：目标文章标题
    writing_type: str = Field(..., regex=r'^(review|summary|critique|proposal)$')  # 必填：必须是预定义的写作类型之一
    paper_ids: List[int] = []  # 可选：作为参考的论文ID列表
    outline: Optional[List[Dict[str, Any]]] = None  # 可选：用户预设的定制化大纲

class WritingUpdate(BaseModel):
    """写作更新模型"""
    title: Optional[str] = None  # 可选更新：文章标题
    content: Optional[str] = None  # 可选更新：文章内容
    outline: Optional[List[Dict[str, Any]]] = None  # 可选更新：文章大纲
    sections: Optional[Dict[str, str]] = None  # 可选更新：章节内容
    citations: Optional[List[Dict[str, Any]]] = None  # 可选更新：引用列表
    status: Optional[str] = None  # 可选更新：文章状态
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)  # 可选更新：质量得分

class LiteratureReview(BaseModel):
    """文献综述 (针对 writing_type 为 review)"""
    introduction: str  # 引言部分
    methodology_review: str  # 对已有研究方法的梳理回顾
    findings_synthesis: str  # 对各论文研究发现的综合论述
    discussion: str  # 深度讨论与分析
    conclusion: str  # 结论部分
    references: List[Dict[str, Any]]  # 标准化参考文献列表

class PaperSummary(BaseModel):
    """论文总结 (针对 writing_type 为 summary)"""
    background: str  # 研究背景概述
    methods: str  # 核心研究方法提炼
    results: str  # 主要研究结果提炼
    conclusions: str  # 论文作者的核心结论
    significance: str  # 该研究的意义与价值

class PaperCritique(BaseModel):
    """论文评述 (针对 writing_type 为 critique)"""
    strengths: List[str]  # 论文的优点与创新之处
    weaknesses: List[str]  # 论文的缺点与不足
    methodological_issues: List[str]  # 方法论层面可能存在的问题
    interpretation_concerns: List[str]  # 结果解释或结论推导方面的疑虑
    suggestions: List[str]  # 改进建议

class ResearchProposal(BaseModel):
    """研究提案 (针对 writing_type 为 proposal)"""
    background: str  # 课题背景与动机
    problem_statement: str  # 明确的问题陈述
    research_questions: List[str]  # 拟解决的具体研究问题
    methodology: str  # 拟采用的研究方法与方案
    expected_outcomes: str  # 预期的研究成果
    significance: str  # 课题的科学意义或应用价值
    timeline: str  # 预期的研究时间线规划

class WritingSection(BaseModel):
    """写作章节"""
    title: str  # 章节标题
    content: str  # 章节文本内容
    subsections: List['WritingSection'] = []  # 子章节列表 (递归结构)
    citations: List[str] = []  # 本章节中引用的文献标识列表

# 解决前向引用
WritingSection.model_rebuild()