import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.security import decode_access_token
from src.storage import session_storage, user_storage

# 请求签名有效期（秒）
SIGNATURE_EXPIRY_SECONDS = 60

# 使用 HTTPBearer 提取 Authorization Header
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        security_scheme),
) -> dict:
    """
    依赖函数：从 JWT Token 获取当前登录用户。

    Args:
        credentials: HTTP Authorization 头中的 Bearer Token

    Returns:
        用户字典，包含用户所有信息

    Raises:
        HTTPException: 401 如果认证失败
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception

    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    # 查询用户信息（sub 是字符串，需要转换为 int）
    user = await user_storage.get_user_by_id(int(user_id_str))
    if user is None:
        raise credentials_exception

    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    return user


async def require_superuser(current_user: dict = Depends(get_current_user)) -> dict:
    """
    依赖函数：验证当前用户是否为超级用户。

    Args:
        current_user: 当前登录用户信息

    Returns:
        用户字典（如果是超级用户）

    Raises:
        HTTPException: 403 如果不是超级用户
    """
    if not current_user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required",
        )
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        security_scheme),
) -> Optional[dict]:
    """
    依赖函数：可选认证，不强制要求登录。

    Args:
        credentials: HTTP Authorization 头中的 Bearer Token

    Returns:
        用户字典或 None（如果未提供有效 Token）
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        return None

    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        return None

    user = await user_storage.get_user_by_id(int(user_id))
    if user and user.get("is_active"):
        return user

    return None


async def verify_request_signature(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    依赖函数：验证请求签名（防重放和篡改）。

    验证流程：
    1. 提取时间戳、nonce 和签名
    2. 验证时间戳是否在有效期内（60秒）
    3. 验证 nonce 是否已被使用
    4. 获取用户的 session_secret
    5. 使用相同算法计算签名并对比

    Args:
        request: FastAPI 请求对象
        current_user: 当前登录用户（依赖 get_current_user）

    Returns:
        用户字典（验证通过）

    Raises:
        HTTPException: 401 如果签名验证失败
    """
    signature_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid request signature",
    )

    # 提取请求头
    timestamp_str = request.headers.get("X-Request-Timestamp")
    nonce = request.headers.get("X-Request-Nonce")
    signature = request.headers.get("X-Request-Signature")

    if not timestamp_str or not nonce or not signature:
        raise signature_exception

    # 1. 验证时间戳
    try:
        timestamp = int(timestamp_str)
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        if abs(now - timestamp) > SIGNATURE_EXPIRY_SECONDS * 1000:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Request timestamp expired",
            )
    except ValueError:
        raise signature_exception

    # 2. 验证 nonce 是否已使用（防重放）
    if not await session_storage.is_nonce_valid(nonce):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Request nonce already used",
        )

    # 3. 获取用户的 session_secret
    session_secret = await session_storage.get_session_secret(current_user["id"])
    if not session_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
        )

    # 4. 计算 body 哈希（如果有）
    body = await request.body()
    body_hash = hashlib.sha256(body).hexdigest() if body else ""

    # 5. 构建待签名数据（与前端的顺序一致）
    method = request.method.upper()
    path = request.url.path
    payload = f"{method}{path}{timestamp}{nonce}{body_hash}"

    # 6. 计算预期签名
    expected_signature = hmac.new(
        session_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # 7. 对比签名（常量时间比较，防时序攻击）
    if not hmac.compare_digest(signature, expected_signature):
        raise signature_exception

    # 8. 记录 nonce（标记为已使用）
    await session_storage.record_nonce(nonce)

    return current_user


async def require_superuser_with_signature(
    current_user: dict = Depends(verify_request_signature),
) -> dict:
    """
    依赖函数：验证请求签名并验证超级用户权限。

    Args:
        current_user: 当前登录用户信息（已通过签名验证）

    Returns:
        用户字典（如果是超级用户）

    Raises:
        HTTPException: 403 如果不是超级用户
    """
    if not current_user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required",
        )
    return current_user
