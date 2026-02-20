from pathlib import Path
from typing import Optional

import aiosqlite

# 数据库路径配置（独立数据库）
DB_DIR = Path("./data")
DB_PATH = DB_DIR / "users.db"


class UserStorage:
    def __init__(self):
        # 确保目录存在
        if not DB_DIR.exists():
            DB_DIR.mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        """初始化用户表"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("PRAGMA journal_mode=WAL;")

            # 创建用户表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    is_superuser INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def create_user(
        self, username: str, email: str, password_hash: str, is_superuser: bool = False
    ) -> Optional[int]:
        """创建新用户，返回用户 ID"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute(
                    """INSERT INTO users (username, email, password_hash, is_superuser)
                       VALUES (?, ?, ?, ?)""",
                    (username, email, password_hash, 1 if is_superuser else 0),
                )
                await db.commit()
                return cursor.lastrowid
        except aiosqlite.IntegrityError:
            # 用户名或邮箱已存在
            return None

    async def get_user_by_username(self, username: str) -> Optional[dict]:
        """通过用户名获取用户信息"""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """通过 ID 获取用户信息"""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """通过邮箱获取用户信息"""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def list_users(self) -> list[dict]:
        """列出所有用户"""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT id, username, email, is_active, is_superuser, created_at
                   FROM users ORDER BY created_at DESC"""
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def deactivate_user(self, user_id: int) -> bool:
        """吊销用户账号（设置 is_active = 0）"""
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "UPDATE users SET is_active = 0 WHERE id = ?", (user_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def activate_user(self, user_id: int) -> bool:
        """激活用户账号"""
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "UPDATE users SET is_active = 1 WHERE id = ?", (user_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def promote_to_superuser(self, user_id: int) -> bool:
        """提升用户为超级用户"""
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "UPDATE users SET is_superuser = 1 WHERE id = ?", (user_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def demote_from_superuser(self, user_id: int) -> bool:
        """取消用户超级用户权限"""
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "UPDATE users SET is_superuser = 0 WHERE id = ?", (user_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def count_superusers(self) -> int:
        """统计超级用户数量"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM users WHERE is_superuser = 1 AND is_active = 1"
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def can_revoke_superuser(self, user_id: int) -> bool:
        """
        检查是否可以吊销/取消该超级用户权限
        规则：必须保留至少一个活跃的超级用户
        """
        async with aiosqlite.connect(DB_PATH) as db:
            # 先检查该用户是否是目前唯一的活跃超级用户
            async with db.execute(
                """SELECT COUNT(*) FROM users
                   WHERE is_superuser = 1 AND is_active = 1 AND id != ?""",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
                other_superusers = row[0] if row else 0
                return other_superusers > 0

    async def is_superuser(self, user_id: int) -> bool:
        """检查用户是否为超级用户"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT is_superuser FROM users WHERE id = ? AND is_active = 1",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return bool(row[0]) if row else False


# 单例模式供外部调用
storage = UserStorage()
