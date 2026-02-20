from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.security import decode_access_token
from src.storage import user_storage

# 使用 HTTPBearer 提取 Authorization Header
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
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
