import logging

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from src.core.settings import get_settings
from src.storage import apikey_storage

logger = logging.getLogger(__name__)

router = APIRouter()


class KeyVerifyRequest(BaseModel):
    key: str


class KeyVerifyResponse(BaseModel):
    key_value: str
    user_id: int
    is_active: bool
    purpose: str


@router.post("/verify", response_model=KeyVerifyResponse)
async def verify_api_key(req: KeyVerifyRequest, authorization: str = Header(None)):
    """验证 API Key（供 Worker 回源使用）

    需要 Internal Secret 认证，防止外部滥用
    """
    # 验证内部密钥
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing internal auth")

    token = authorization.replace("Bearer ", "")
    if token != get_settings().internal_secret:
        logger.error(
            f"Invalid internal auth: {token} != {get_settings().internal_secret}"
        )
        raise HTTPException(status_code=403, detail="Invalid internal auth")

    # 查询 API Key
    result = await apikey_storage.get_api_key(req.key)

    if not result:
        raise HTTPException(status_code=404, detail="Key not found")

    if not result.get("is_active"):
        raise HTTPException(status_code=403, detail="Key revoked")

    return KeyVerifyResponse(
        key_value=result["key_value"],
        user_id=result["user_id"],
        is_active=result["is_active"],
        purpose=result.get("purpose", "default"),
    )
