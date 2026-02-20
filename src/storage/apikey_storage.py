import asyncio
import time
from pathlib import Path
from typing import Dict, Optional

import aiosqlite

# API Key 独立数据库（与用户库分离，通过 user_id 逻辑关联）
DB_DIR = Path("./data")
DB_PATH = DB_DIR / "api_keys.db"

# 内存缓存配置
CACHE_TTL_SECONDS = 60  # 缓存 60 秒


class APIKeyStorage:
    def __init__(self):
        # 确保目录存在
        if not DB_DIR.exists():
            DB_DIR.mkdir(parents=True, exist_ok=True)
        # 内存缓存: {key_value: (result, expires_at)}
        self._cache: Dict[str, tuple] = {}
        self._cache_lock = asyncio.Lock()

    def _get_from_cache(self, key_value: str) -> Optional[dict]:
        """从内存缓存获取 API Key"""
        if key_value in self._cache:
            result, expires_at = self._cache[key_value]
            if time.time() < expires_at:
                return result
            # 过期，删除
            del self._cache[key_value]
        return None

    def _set_cache(self, key_value: str, result: Optional[dict]):
        """设置内存缓存"""
        expires_at = time.time() + CACHE_TTL_SECONDS
        self._cache[key_value] = (result, expires_at)

    async def get_api_key(self, key_value: str) -> Optional[dict]:
        """查询特定的 API Key 是否存在且活跃（带内存缓存）"""
        # 先检查内存缓存
        cached = self._get_from_cache(key_value)
        if cached is not None:
            return cached

        # 缓存未命中，查询数据库
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM api_keys WHERE key_value = ? AND is_active = 1",
                (key_value,),
            ) as cursor:
                row = await cursor.fetchone()
                result = dict(row) if row else None

        # 写入缓存（包括未找到的情况也缓存，防止缓存穿透）
        self._set_cache(key_value, result)
        return result

    async def init_db(self):
        """初始化数据库表并开启 WAL 模式"""
        async with aiosqlite.connect(DB_PATH) as db:
            # 开启 WAL 模式以支持多进程高并发
            await db.execute("PRAGMA journal_mode=WAL;")

            # 创建 API Key 表（无外部约束，通过 user_id 逻辑关联用户）
            await db.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_value TEXT UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    purpose TEXT
                )
            """)
            await db.commit()

    async def add_api_key(
        self, key_value: str, user_id: int, purpose: str = "default"
    ) -> bool:
        """插入新的 API Key"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "INSERT INTO api_keys (key_value, user_id, purpose) VALUES (?, ?, ?)",
                    (key_value, user_id, purpose),
                )
                await db.commit()
                return True
        except aiosqlite.IntegrityError:
            # 如果 Key 已存在（唯一性约束）
            return False

    async def get_api_key(self, key_value: str) -> Optional[dict]:
        """查询特定的 API Key 是否存在且活跃"""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM api_keys WHERE key_value = ? AND is_active = 1",
                (key_value,),
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def list_api_keys_by_user(self, user_id: int) -> list[dict]:
        """列出指定用户的所有 API Key（包括已吊销的）"""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT id, key_value, user_id, is_active, created_at, purpose
                   FROM api_keys
                   WHERE user_id = ?
                   ORDER BY created_at DESC""",
                (user_id,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def list_all_keys(self) -> list[dict]:
        """列出所有 API Key（超级用户用）"""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT id, key_value, user_id, is_active, created_at, purpose
                   FROM api_keys
                   ORDER BY created_at DESC"""
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def revoke_api_key(self, key_id: int, user_id: int) -> bool:
        """吊销指定 ID 的 API Key（只能吊销属于自己的 Key）"""
        async with aiosqlite.connect(DB_PATH) as db:
            # 验证该 Key 是否属于指定用户
            async with db.execute(
                "SELECT user_id FROM api_keys WHERE id = ?", (key_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False  # Key 不存在
                if row[0] != user_id:
                    return False  # 无权操作他人的 Key

            # 执行吊销操作
            cursor = await db.execute(
                "UPDATE api_keys SET is_active = 0 WHERE id = ? AND user_id = ?",
                (key_id, user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def revoke_any_key(self, key_id: int) -> bool:
        """吊销任意 API Key（超级用户用）"""
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "UPDATE api_keys SET is_active = 0 WHERE id = ?", (key_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_api_key(self, key_id: int, user_id: int) -> bool:
        """永久删除指定 ID 的 API Key（只能删除属于自己的 Key）"""
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "DELETE FROM api_keys WHERE id = ? AND user_id = ?", (key_id, user_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_key_by_id(self, key_id: int) -> Optional[dict]:
        """通过 ID 获取 API Key 详情"""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM api_keys WHERE id = ?", (key_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None


# 单例模式供外部调用
storage = APIKeyStorage()
