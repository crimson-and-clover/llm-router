from fastapi import APIRouter, HTTPException, status

from src.core.security import create_access_token, hash_password, verify_password
from src.models import Token, UserLogin, UserRegister, UserResponse
from src.storage import user_storage

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister):
    """用户注册"""
    # 检查用户名是否已存在
    existing_user = await user_storage.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # 检查邮箱是否已存在
    existing_email = await user_storage.get_user_by_email(user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # 哈希密码并创建用户
    password_hash = hash_password(user_data.password)
    user_id = await user_storage.create_user(
        username=user_data.username, email=user_data.email, password_hash=password_hash
    )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )

    # 返回用户信息
    user = await user_storage.get_user_by_id(user_id)
    return UserResponse(**user)


@router.post("/login", response_model=Token)
async def login(login_data: UserLogin):
    """用户登录，返回 JWT Token"""
    # 查找用户
    user = await user_storage.get_user_by_username(login_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查用户是否活跃
    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    # 验证密码
    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 创建 JWT Token
    access_token = create_access_token(data={"sub": user["id"]})

    return Token(access_token=access_token)
