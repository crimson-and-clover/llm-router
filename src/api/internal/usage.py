import logging

from fastapi import APIRouter, Header, HTTPException

from src.core.settings import get_settings
from src.models import UsageSettlementRequest, UsageSettlementResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/settle", response_model=UsageSettlementResponse)
async def settle_usage(req: UsageSettlementRequest, authorization: str = Header(None)):
    """用量结算接口（供 Settlement Worker 使用）

    接收 Worker 发送的批量用量数据，进行结算处理
    需要 Internal Secret 认证
    """
    # 验证内部密钥
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing internal auth")

    token = authorization.replace("Bearer ", "")
    if token != get_settings().internal_secret:
        logger.error(f"Invalid internal auth for settlement: {token}")
        raise HTTPException(status_code=403, detail="Invalid internal auth")

    entries = req.entries
    logger.info(f"[Settlement] Received {len(entries)} usage entries")

    # TODO: 实现具体的结算逻辑
    # 目前直接返回成功

    logger.info(f"[Settlement] Processed {len(entries)} entries successfully")

    return UsageSettlementResponse(success=True, processedCount=len(entries))
