from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta, timezone

import aiosqlite

# 数据库路径配置（独立的会话数据库）
DB_DIR = Path("./data")
DB_PATH = DB_DIR / "sessions.db"

# 会话有效期（2小时）
SESSION_EXPIRY_HOURS = 2
# Nonce 有效期（60秒）
NONCE_EXPIRY_SECONDS = 60


class SessionStorage:
    def __init__(self):
        # 确保目录存在
        if not DB_DIR.exists():
            DB_DIR.mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        """初始化会话和 nonce 表"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("PRAGMA journal_mode=WAL;")

            # 创建用户会话表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_secret TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            """)

            # 创建 nonce 记录表（用于防重放）
            await db.execute("""
                CREATE TABLE IF NOT EXISTS nonce_records (
                    nonce TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            """)

            # 创建索引
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id 
                ON user_sessions(user_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_expires 
                ON user_sessions(expires_at)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_nonce_expires 
                ON nonce_records(expires_at)
            """)

            await db.commit()

    async def create_session(self, user_id: int, session_secret: str) -> bool:
        """创建用户会话，返回是否成功"""
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_EXPIRY_HOURS)
            async with aiosqlite.connect(DB_PATH) as db:
                # 删除该用户的旧会话
                await db.execute(
                    "DELETE FROM user_sessions WHERE user_id = ?",
                    (user_id,)
                )
                # 创建新会话
                await db.execute(
                    """INSERT INTO user_sessions (user_id, session_secret, expires_at)
                       VALUES (?, ?, ?)""",
                    (user_id, session_secret, expires_at.isoformat())
                )
                await db.commit()
                return True
        except Exception:
            return False

    async def get_session_secret(self, user_id: int) -> Optional[str]:
        """获取用户的 session_secret（如果未过期）"""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT session_secret, expires_at FROM user_sessions
                   WHERE user_id = ? AND expires_at > ?""",
                (user_id, datetime.now(timezone.utc).isoformat())
            ) as cursor:
                row = await cursor.fetchone()
                return row["session_secret"] if row else None

    async def delete_session(self, user_id: int) -> bool:
        """删除用户会话（登出时使用）"""
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "DELETE FROM user_sessions WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def is_nonce_valid(self, nonce: str) -> bool:
        """检查 nonce 是否有效（未被使用过且未过期）"""
        async with aiosqlite.connect(DB_PATH) as db:
            # 检查 nonce 是否已存在
            async with db.execute(
                "SELECT 1 FROM nonce_records WHERE nonce = ?",
                (nonce,)
            ) as cursor:
                if await cursor.fetchone():
                    return False  # nonce 已存在，无效
            return True

    async def record_nonce(self, nonce: str) -> bool:
        """记录 nonce（使用后记录，防止重放）"""
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=NONCE_EXPIRY_SECONDS)
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    """INSERT INTO nonce_records (nonce, expires_at)
                       VALUES (?, ?)""",
                    (nonce, expires_at.isoformat())
                )
                await db.commit()
                return True
        except aiosqlite.IntegrityError:
            # nonce 已存在
            return False
        except Exception:
            return False

    async def cleanup_expired(self) -> int:
        """清理过期的会话和 nonce，返回清理数量"""
        async with aiosqlite.connect(DB_PATH) as db:
            # 清理过期会话
            cursor1 = await db.execute(
                "DELETE FROM user_sessions WHERE expires_at <= ?",
                (datetime.now(timezone.utc).isoformat(),)
            )
            # 清理过期 nonce
            cursor2 = await db.execute(
                "DELETE FROM nonce_records WHERE expires_at <= ?",
                (datetime.now(timezone.utc).isoformat(),)
            )
            await db.commit()
            return cursor1.rowcount + cursor2.rowcount


# 单例模式供外部调用
session_storage = SessionStorage()
