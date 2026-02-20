"""
Phase 1: 数据库初始化测试
验证数据库文件和表结构是否正确创建
"""

import asyncio
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.apikey_storage import APIKeyStorage
from src.storage.user_storage import UserStorage


async def test_database_initialization():
    """测试数据库初始化"""
    print("=" * 50)
    print("Phase 1: 数据库初始化测试")
    print("=" * 50)

    # 清理旧数据
    data_dir = Path("./data")
    if data_dir.exists():
        for f in data_dir.glob("*.db*"):
            f.unlink()
        print("[PASS] 清理旧数据")

    # 初始化数据库
    user_storage = UserStorage()
    apikey_storage = APIKeyStorage()

    await user_storage.init_db()
    await apikey_storage.init_db()
    print("[PASS] 数据库初始化成功")

    # 验证数据库文件存在
    assert (data_dir / "users.db").exists(), "users.db 未创建"
    assert (data_dir / "api_keys.db").exists(), "api_keys.db 未创建"
    print("[PASS] 数据库文件创建成功")

    # 验证可以连接并查询
    users = await user_storage.list_users()
    print(f"[PASS] 用户数据库可访问 (当前用户数量: {len(users)})")

    print("\n[SUCCESS] Phase 1 测试通过\n")
    return True


if __name__ == "__main__":
    try:
        asyncio.run(test_database_initialization())
    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        sys.exit(1)
