"""
用户模型
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class UserDB(Base):
    """用户数据库模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)  # 用户唯一ID
    username = Column(String(50), unique=True, index=True, nullable=False)  # 唯一的登录用户名
    email = Column(String(100), unique=True, index=True, nullable=False)  # 唯一的注册邮箱
    hashed_password = Column(String(255), nullable=False)  # 加密后的密码哈希值，绝证明文存储
    full_name = Column(String(100))  # 用户的真实姓名或显示昵称
    institution = Column(String(200))  # 用户所属的机构/学校/公司名称
    research_field = Column(String(100))  # 用户的主要研究领域
    preferences = Column(Text)  # JSON格式存储的用户个性化偏好设置
    is_active = Column(Boolean, default=True)  # 账号是否处于激活状态（可用于软删除或封禁）
    is_premium = Column(Boolean, default=False)  # 是否为高级/付费会员
    created_at = Column(DateTime, default=datetime.utcnow)  # 账号注册时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 资料最后修改时间

class User(BaseModel):
    """用户响应模型 (用于向前端返回数据，已排除密码)"""
    id: int  # 用户ID
    username: str  # 用户名
    email: str  # 邮箱
    full_name: Optional[str] = None  # 全名
    institution: Optional[str] = None  # 所属机构
    research_field: Optional[str] = None  # 研究领域
    is_active: bool = True  # 账号状态
    is_premium: bool = False  # 会员状态
    created_at: datetime  # 注册时间
    
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    """用户创建模型 (用于处理注册请求)"""
    username: str = Field(..., min_length=3, max_length=50)  # 必填：用户名，限制3-50字符
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')  # 必填：邮箱，使用正则验证格式
    password: str = Field(..., min_length=6)  # 必填：明文密码，限制至少6位
    full_name: Optional[str] = None  # 可选：全名
    institution: Optional[str] = None  # 可选：所属机构
    research_field: Optional[str] = None  # 可选：研究领域

class UserUpdate(BaseModel):
    """用户更新模型 (用于处理修改个人资料请求)"""
    full_name: Optional[str] = None  # 可选更新：全名
    institution: Optional[str] = None  # 可选更新：所属机构
    research_field: Optional[str] = None  # 可选更新：研究领域
    preferences: Optional[str] = None  # 可选更新：偏好设置JSON字符串

class UserPreferences(BaseModel):
    """用户偏好设置 (用于结构化 preferences 字段)"""
    research_interests: List[str] = []  # 用户的具体研究兴趣标签列表
    citation_style: str = "APA"  # 默认的首选引用格式 (如 APA, BibTeX, IEEE)
    language: str = "zh"  # 系统及报告生成的首选语言
    notification_enabled: bool = True  # 是否开启系统通知
    auto_save: bool = True  # 是否开启编辑器自动保存