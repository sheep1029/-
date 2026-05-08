"""
分析模型
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class AnalysisDB(Base):
    """分析数据库模型"""
    __tablename__ = "analysis"
    
    id = Column(Integer, primary_key=True, index=True)  # 分析记录唯一标识
    title = Column(String(200), nullable=False)  # 分析报告的标题
    analysis_type = Column(String(50), nullable=False)  # 分析类型（如综合、方法论等）
    paper_ids = Column(JSON)  # 分析所基于的论文ID列表
    methodology = Column(Text)  # 论文使用的方法论概述
    findings = Column(JSON)  # 分析发现的具体内容（结构化JSON）
    insights = Column(Text)  # 深度分析洞察与观点
    limitations = Column(Text)  # 论文或研究的局限性
    recommendations = Column(Text)  # 基于分析的未来研究建议
    confidence_score = Column(Float, default=0.0)  # 分析结果的置信度评分 (0-1)
    novelty_score = Column(Float, default=0.0)  # 研究的新颖度评分 (0-1)
    impact_score = Column(Float, default=0.0)  # 研究的影响力预期评分 (0-1)
    metadata = Column(JSON)  # 其他扩展元数据信息
    user_id = Column(Integer, index=True)  # 创建该分析的用户ID
    task_id = Column(Integer, index=True)  # 生成该分析关联的后台任务ID
    created_at = Column(DateTime, default=datetime.utcnow)  # 记录创建时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 记录最后更新时间

class Analysis(BaseModel):
    """分析响应模型，是AnalysisDB的精简版。避免直接返回数据库模型到前端，保持响应简洁。"""
    id: int  # 分析记录唯一标识
    title: str  # 分析报告的标题
    analysis_type: str  # 分析类型
    methodology: Optional[str] = None  # 论文使用的方法论概述
    findings: Dict[str, Any] = {}  # 分析发现的具体内容
    insights: Optional[str] = None  # 深度分析洞察与观点
    limitations: Optional[str] = None  # 研究局限性
    recommendations: Optional[str] = None  # 未来研究建议
    confidence_score: float = 0.0  # 分析结果的置信度评分
    novelty_score: float = 0.0  # 研究的新颖度评分
    impact_score: float = 0.0  # 研究的影响力预期评分
    created_at: datetime  # 记录创建时间
    
    class Config:
        from_attributes = True

class AnalysisCreate(BaseModel):
    """当用户想要创建请求模型的时候，用这个实体来校验前端传来的参数。"""
    title: str = Field(..., min_length=1, max_length=200)  # 必填，分析报告的标题
    analysis_type: str = Field(..., regex=r'^(comprehensive|methodology|findings|gap|trend)$')  # 必填，必须是预定义的分析类型之一
    paper_ids: List[int] = []  # 可选，分析所基于的论文ID列表
    methodology: Optional[str] = None  # 可选，预设的方法论信息

class AnalysisUpdate(BaseModel):
    """当用户想要更新请求模型的时候，用这个实体来校验前端传来的参数。"""
    title: Optional[str] = None  # 可选更新：分析报告标题
    methodology: Optional[str] = None  # 可选更新：方法论概述
    findings: Optional[Dict[str, Any]] = None  # 可选更新：分析发现内容
    insights: Optional[str] = None  # 可选更新：深度分析洞察
    limitations: Optional[str] = None  # 可选更新：研究局限性
    recommendations: Optional[str] = None  # 可选更新：未来研究建议
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)  # 可选更新：置信度评分，限制0.0到1.0之间
    novelty_score: Optional[float] = Field(None, ge=0.0, le=1.0)  # 可选更新：新颖度评分，限制0.0到1.0之间
    impact_score: Optional[float] = Field(None, ge=0.0, le=1.0)  # 可选更新：影响力评分，限制0.0到1.0之间

class ComprehensiveAnalysis(BaseModel):
    """综合分析结果"""
    summary: str  # 整体分析的文本摘要
    key_findings: List[str]  # 核心研究发现列表
    methodological_trends: List[str]  # 方法论演进与趋势列表
    research_gaps: List[str]  # 识别出的当前研究缺口列表
    future_directions: List[str]  # 对未来研究方向的建议列表
    quality_assessment: Dict[str, float]  # 多维度的论文质量评估打分字典
    citation_network: Dict[str, Any]  # 论文之间的引用关系网络结构数据

class MethodologyAnalysis(BaseModel):
    """方法论分析结果"""
    common_methods: List[str]  # 领域内常用的研究方法列表
    method_comparison: Dict[str, Any]  # 不同方法之间的多维度对比数据
    strengths_weaknesses: Dict[str, List[str]]  # 各方法的优缺点分析字典
    best_practices: List[str]  # 该领域的最佳实践或推荐操作列表

class FindingsAnalysis(BaseModel):
    """研究发现分析"""
    consensus_points: List[str]  # 领域内已达成共识的研究结论列表
    controversial_points: List[str]  # 领域内存在争议或矛盾的观点列表
    emerging_patterns: List[str]  # 最新涌现出的研究模式或现象列表
    evidence_strength: Dict[str, float]  # 各项发现的证据强度支持打分

class GapAnalysis(BaseModel):
    """研究缺口分析"""
    identified_gaps: List[str]  # 具体被识别出的研究空白或缺陷列表
    gap_categories: Dict[str, List[str]]  # 按类别划分的研究缺口字典
    opportunity_areas: List[str]  # 有潜力的高价值突破领域列表
    research_questions: List[str]  # 建议的未来具体研究问题列表

class TrendAnalysis(BaseModel):
    """趋势分析结果"""
    temporal_trends: Dict[str, Any]  # 随时间变化的趋势数据（如发文量、热度）
    topic_evolution: List[str]  # 核心研究主题的演进路径
    emerging_topics: List[str]  # 正在快速增长的新兴研究主题
    citation_trends: Dict[str, Any]  # 引用关系网络随时间的变化趋势