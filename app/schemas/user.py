"""
用户相关 Schema
"""

from pydantic import BaseModel, EmailStr, Field


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")


class UserCreate(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    real_name: str | None = None
    role: str = Field(default="PLANNER", description="角色: ADMIN, MANAGER, PLANNER, ANALYST")
    department: str | None = None
    email: EmailStr | None = None


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    real_name: str | None
    role: str
    department: str | None
    email: str | None
    status: str

    class Config:
        from_attributes = True
