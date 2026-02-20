from fastapi import APIRouter, Depends, HTTPException, status

from src.core.dependencies import get_current_user
from src.core.security import generate_secure_key
from src.models import APIKeyCreate, APIKeyResponse
from src.storage import apikey_storage

router = APIRouter()


def mask_key(key_value: str) -> str:
    """脱敏显示 API Key"""
    if len(key_value) <= 12:
        return key_value[:4] + "****" + key_value[-4:]
    return key_value[:8] + "****" + key_value[-8:]


@router.get("/", response_model=list[APIKeyResponse])
async def list_my_keys(current_user: dict = Depends(get_current_user)):
    """列出当前用户的所有 API Key"""
    keys = await apikey_storage.list_api_keys_by_user(current_user["id"])

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


@router.post("/", response_model=APIKeyResponse)
async def create_my_key(
    key_data: APIKeyCreate, current_user: dict = Depends(get_current_user)
):
    """创建新的 API Key"""
    # 生成新 Key
    new_key = generate_secure_key(prefix=key_data.prefix)

    # 保存到数据库
    success = await apikey_storage.add_api_key(
        key_value=new_key, user_id=current_user["id"], purpose=key_data.purpose
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key",
        )

    # 获取刚创建的 Key 信息
    keys = await apikey_storage.list_api_keys_by_user(current_user["id"])
    created_key = None
    for key in keys:
        if key["key_value"] == new_key:
            created_key = key
            break

    if not created_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve created key",
        )

    return APIKeyResponse(
        id=created_key["id"],
        key_value=new_key,  # 只在创建时返回完整 key
        key_masked=mask_key(new_key),
        is_active=True,
        created_at=created_key["created_at"],
        purpose=key_data.purpose,
        user_id=current_user["id"],
    )


@router.delete("/{key_id}")
async def revoke_my_key(key_id: int, current_user: dict = Depends(get_current_user)):
    """吊销自己的 API Key"""
    success = await apikey_storage.revoke_api_key(key_id, current_user["id"])

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not found or you don't have permission to revoke it",
        )

    return {"message": "API key revoked successfully"}
