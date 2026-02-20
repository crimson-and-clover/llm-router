import hashlib
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from src.core.settings import get_settings


def generate_secure_key(prefix: str = "sk", length: int = 64) -> str:
    """
    生成高熵的安全 API Key。
    格式: prefix-随机字符串 (例如: sk-J7a_x9...)
    """
    alphabet = string.ascii_lowercase + string.digits
    random_str = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}-{random_str}"


def sha256_hash(data: str) -> str:
    """对字符串进行 SHA256 哈希（用于前端密码预哈希）"""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    """
    使用 bcrypt 对密码进行哈希处理。
    注意：传入的 password 应该是前端已经 SHA256 哈希后的值
    自动处理加盐。
    bcrypt 限制密码最大 72 字节。
    """
    # bcrypt 限制密码最大 72 字节
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码是否与哈希密码匹配。
    注意：传入的 plain_password 应该是前端已经 SHA256 哈希后的值
    """
    password_bytes = plain_password.encode("utf-8")[:72]
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT 访问令牌。

    Args:
        data: 要编码到令牌中的数据（通常包含 sub: user_id）
        expires_delta: 过期时间增量，默认从配置读取

    Returns:
        JWT 令牌字符串
    """
    settings = get_settings()
    to_encode = data.copy()

    # 将 sub 转换为字符串（JWT 标准要求）
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码并验证 JWT 令牌。

    Args:
        token: JWT 令牌字符串

    Returns:
        解码后的 payload 字典，如果验证失败返回 None
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        return None
