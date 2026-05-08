"""
任务模型
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TaskDB(Base):
    """任务数据库模型"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)  # 任务的唯一标识ID
    title = Column(String(200), nullable=False)  # 任务的简短标题
    description = Column(Text)  # 任务的详细描述
    task_type = Column(String(50), nullable=False)  # 任务类型，如：literature_search, analysis, writing
    status = Column(String(20), default="pending")  # 任务状态：pending, running, completed, failed
    priority = Column(String(10), default="medium")  # 任务优先级：low, medium, high
    parameters = Column(JSON)  # 任务执行所需的输入参数
    results = Column(JSON)  # 任务执行成功后产生的结构化结果
    error_message = Column(Text)  # 如果任务失败，记录详细的错误信息
    progress = Column(Integer, default=0)  # 任务执行进度百分比 (0-100)
    user_id = Column(Integer, index=True)  # 创建或拥有该任务的用户ID
    created_at = Column(DateTime, default=datetime.utcnow)  # 任务创建时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 任务最后更新时间
    completed_at = Column(DateTime)  # 任务完成（成功或失败）的时间

class Task(BaseModel):
    """任务响应模型"""
    id: int  # 任务ID
    title: str  # 任务标题
    description: Optional[str] = None  # 任务描述
    task_type: str  # 任务类型
    status: str  # 当前任务状态
    priority: str  # 任务优先级
    progress: int = 0  # 当前进度
    results: Optional[Dict[str, Any]] = None  # 任务输出结果
    error_message: Optional[str] = None  # 错误信息
    created_at: datetime  # 创建时间
    updated_at: datetime  # 更新时间
    completed_at: Optional[datetime] = None  # 完成时间
    
    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    """任务创建模型"""
    title: str = Field(..., min_length=1, max_length=200)  # 必填：任务标题
    description: Optional[str] = None  # 可选：任务描述
    task_type: str = Field(..., regex=r'^(literature_search|analysis|writing)$')  # 必填：限定的几个任务类型
    priority: str = Field(default="medium", regex=r'^(low|medium|high)$')  # 可选：任务优先级，默认为中等
    parameters: Dict[str, Any] = {}  # 可选：任务输入参数，默认为空字典

class TaskUpdate(BaseModel):
    """任务更新模型"""
    title: Optional[str] = None  # 可选更新：任务标题
    description: Optional[str] = None  # 可选更新：任务描述
    status: Optional[str] = None  # 可选更新：任务状态
    priority: Optional[str] = None  # 可选更新：任务优先级
    progress: Optional[int] = Field(None, ge=0, le=100)  # 可选更新：进度，限制在 0-100
    results: Optional[Dict[str, Any]] = None  # 可选更新：任务结果
    error_message: Optional[str] = None  # 可选更新：错误信息

class LiteratureSearchTask(BaseModel):
    """文献搜索任务参数"""
    query: str  # 检索关键词或表达式
    max_papers: int = 20  # 期望返回的最大论文数
    year_range: Optional[tuple] = None  # 发表年份范围筛选 (如 [2020, 2024])
    venues: List[str] = []  # 限定检索的会议或期刊列表
    quality_threshold: float = 0.5  # 最低质量/相关性分数阈值

class AnalysisTask(BaseModel):
    """分析任务参数"""
    paper_ids: List[int]  # 目标分析的论文ID列表
    analysis_type: str = "comprehensive"  # 分析模式：comprehensive, methodology, findings 等
    focus_areas: List[str] = []  # 用户希望重点关注的领域或问题

class WritingTask(BaseModel):
    """写作任务参数"""
    paper_ids: List[int]  # 作为写作参考的论文ID列表
    writing_type: str = "review"  # 写作类型：review (综述), summary (总结), critique (评论)
    outline: Optional[List[str]] = None  # 可选的用户预设大纲
    style: str = "academic"  # 写作风格，如 academic (学术), popular (科普)
    length: int = 1000  # 期望生成的文本大致字数