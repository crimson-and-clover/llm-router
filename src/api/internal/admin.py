from fastapi import APIRouter, Depends, HTTPException, status

from src.core.dependencies import require_superuser_with_signature
from src.core.security import hash_password
from src.models import APIKeyResponse, UserCreate, UserResponse
from src.storage import apikey_storage, user_storage

router = APIRouter()


def mask_key(key_value: str) -> str:
    """脱敏显示 API Key"""
    if len(key_value) <= 12:
        return key_value[:4] + "****" + key_value[-4:]
    return key_value[:8] + "****" + key_value[-8:]


# ========== 用户管理 ==========

@router.get("/users", response_model=list[UserResponse])
async def list_all_users(current_user: dict = Depends(require_superuser_with_signature)):
    """列出所有用户（超级用户专用）"""
    users = await user_storage.list_users()
    return [UserResponse(**user) for user in users]


@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate, current_user: dict = Depends(require_superuser_with_signature)
):
    """超级用户创建新用户（超级用户专用）"""
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


@router.post("/users/{user_id}/promote")
async def promote_user(user_id: int, current_user: dict = Depends(require_superuser_with_signature)):
    """提升用户为超级用户（超级用户专用）"""
    # 检查用户是否存在
    user = await user_storage.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a superuser",
        )

    success = await user_storage.promote_to_superuser(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to promote user",
        )

    return {"message": "User promoted to superuser successfully"}


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int, current_user: dict = Depends(require_superuser_with_signature)
):
    """吊销用户账号（超级用户专用）"""
    # 不能吊销自己
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    # 检查用户是否存在
    user = await user_storage.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # 如果要吊销的是超级用户，检查是否需要保护
    if user.get("is_superuser"):
        can_revoke = await user_storage.can_revoke_superuser(user_id)
        if not can_revoke:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last superuser",
            )

    success = await user_storage.deactivate_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate user",
        )

    return {"message": "User deactivated successfully"}


@router.post("/users/{user_id}/activate")
async def activate_user(user_id: int, current_user: dict = Depends(require_superuser_with_signature)):
    """激活已吊销的用户账号（超级用户专用）"""
    user = await user_storage.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    success = await user_storage.activate_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate user",
        )

    return {"message": "User activated successfully"}


# ========== API Key 管理 ==========

@router.get("/users/{user_id}/keys", response_model=list[APIKeyResponse])
async def list_user_keys(user_id: int, current_user: dict = Depends(require_superuser_with_signature)):
    """查看任意用户的 API Keys（超级用户专用）"""
    # 检查用户是否存在
    user = await user_storage.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    keys = await apikey_storage.list_api_keys_by_user(user_id)

    result = []
    for key in keys:
        result.append(
            APIKeyResponse(
                id=key["id"],
                key_masked=mask_key(key["key_value"]),
                is_active=bool(key["is_active"]),
                created_at=key["created_at"],
                purpose=key.get("purpose", "default"),
                user_id=key["user_id"],
            )
        )

    return result


@router.delete("/users/{user_id}/keys/{key_id}")
async def revoke_any_key(
    user_id: int, key_id: int, current_user: dict = Depends(require_superuser_with_signature)
):
    """吊销任意用户的 API Key（超级用户专用）"""
    # 先检查 Key 是否存在且属于该用户
    key = await apikey_storage.get_key_by_id(key_id)
    if not key or key["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Key not found"
        )

    success = await apikey_storage.revoke_any_key(key_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke key",
        )

    return {"message": "API key revoked successfully"}
