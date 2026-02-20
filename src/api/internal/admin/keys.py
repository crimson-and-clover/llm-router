from fastapi import APIRouter, Depends, HTTPException, status

from src.core.dependencies import require_superuser
from src.models import APIKeyResponse
from src.storage import apikey_storage, user_storage

router = APIRouter()


def mask_key(key_value: str) -> str:
    """脱敏显示 API Key"""
    if len(key_value) <= 12:
        return key_value[:4] + "****" + key_value[-4:]
    return key_value[:8] + "****" + key_value[-8:]


@router.get("/{user_id}/keys", response_model=list[APIKeyResponse])
async def list_user_keys(user_id: int, current_user: dict = Depends(require_superuser)):
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


@router.delete("/{user_id}/keys/{key_id}")
async def revoke_any_key(
    user_id: int, key_id: int, current_user: dict = Depends(require_superuser)
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
