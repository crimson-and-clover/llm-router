from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    """用户基础模型"""

    username: str
    email: EmailStr


class UserCreate(UserBase):
    """创建用户请求模型"""

    password: str


class UserResponse(UserBase):
    """用户响应模型（返回给客户端）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime


class UserInDB(UserBase):
    """数据库中的用户模型（包含敏感信息）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    password_hash: str
    is_active: bool
    is_superuser: bool
    created_at: datetime


class APIKeyCreate(BaseModel):
    """创建 API Key 请求模型"""

    purpose: str = "default"
    prefix: str = "sk"


class APIKeyResponse(BaseModel):
    """API Key 响应模型"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    key_value: Optional[str] = None  # 只在创建时返回完整 key
    key_masked: str  # 脱敏显示
    is_active: bool
    created_at: datetime
    purpose: str
    user_id: int
