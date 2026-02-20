from fastapi import APIRouter, Depends

from src.core.dependencies import get_current_user
from src.models import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return UserResponse(**current_user)
