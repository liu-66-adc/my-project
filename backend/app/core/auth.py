"""认证鉴权模块.

JWT 令牌生成/验证、密码哈希、登录装饰器.
"""

import hashlib
import os
import secrets
import time
from typing import Optional

import jwt

from app.utils.logger import get_logger

logger = get_logger(__name__)

# JWT 密钥
JWT_SECRET = os.environ.get(
    "JWT_SECRET",
    hashlib.sha256("code-practice-platform-v2-secret-key".encode()).hexdigest()
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24
TOKEN_AUDIENCE = "code-practice-platform"


def hash_password(password: str) -> str:
    """对密码进行哈希."""
    salt = secrets.token_hex(8)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def verify_password(password: str, hashed: str) -> bool:
    """验证密码."""
    try:
        salt, h = hashed.split(":", 1)
        return h == hashlib.sha256((salt + password).encode()).hexdigest()
    except Exception:
        return False


def create_token(user_id: str, role: str, username: str) -> str:
    """创建 JWT 令牌."""
    payload = {
        "sub": user_id,
        "role": role,
        "username": username,
        "aud": TOKEN_AUDIENCE,
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRE_HOURS * 3600
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """验证 JWT 令牌，返回 payload 或 None."""
    try:
        payload = jwt.decode(
            token, JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience=TOKEN_AUDIENCE
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("令牌已过期")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"无效令牌: {e}")
        return None
