from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """JWT Token 响应模型"""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT Token Payload 模型"""

    sub: int | None = None  # user_id
    exp: int | None = None  # 过期时间戳


class UserLogin(BaseModel):
    """用户登录请求模型"""

    username: str
    password: str


class UserRegister(BaseModel):
    """用户注册请求模型"""

    username: str
    email: EmailStr
    password: str
