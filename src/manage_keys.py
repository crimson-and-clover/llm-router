import argparse
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.core.security import generate_secure_key
from src.storage import apikey_storage, user_storage


def mask_key(key_value: str) -> str:
    """脱敏显示 API Key，只显示前缀和后几位"""
    if len(key_value) <= 12:
        return key_value[:4] + "****" + key_value[-4:]
    return key_value[:8] + "****" + key_value[-8:]


async def create_key(args):
    """创建新的 API Key"""
    # 初始化数据库
    await user_storage.init_db()
    await apikey_storage.init_db()

    # 通过用户名获取用户 ID
    user = await user_storage.get_user_by_username(args.username)
    if not user:
        print(f"[ERROR] 错误：用户 '{args.username}' 不存在。请先创建用户。")
        return

    if not user["is_active"]:
        print(f"[ERROR] 错误：用户 '{args.username}' 已被吊销。")
        return

    user_id = user["id"]

    # 生成安全 Key
    new_key = generate_secure_key(prefix=args.prefix)

    # 写入数据库
    success = await apikey_storage.add_api_key(new_key, user_id, args.purpose)

    if success:
        print("=" * 50)
        print("[OK] API Key 创建成功！")
        print(f"User:    {args.username} (ID: {user_id})")
        print(f"Key:     {new_key}")
        print(f"Purpose: {args.purpose}")
        print("=" * 50)
    else:
        print("[ERROR] 创建失败：可能数据库连接有问题或 Key 已存在。")


async def list_keys(args):
    """列出用户的所有 API Key"""
    await user_storage.init_db()
    await apikey_storage.init_db()

    # 通过用户名获取用户 ID
    user = await user_storage.get_user_by_username(args.username)
    if not user:
        print(f"[ERROR] 错误：用户 '{args.username}' 不存在。")
        return

    user_id = user["id"]
    keys = await apikey_storage.list_api_keys_by_user(user_id)

    if not keys:
        print(f"ℹ️ 用户 '{args.username}' 没有 API Key。")
        return

    print("=" * 80)
    print(f"[LIST] 用户 '{args.username}' 的 API Key 列表：")
    print("=" * 80)
    print(f"{'ID':<6} {'Key':<30} {'Purpose':<15} {'Status':<10} {'Created At'}")
    print("-" * 80)

    for key in keys:
        key_id = key["id"]
        key_masked = mask_key(key["key_value"])
        purpose = key["purpose"] or "default"
        status = "[ACTIVE] Active" if key["is_active"] else "[REVOKED] Revoked"
        created_at = key["created_at"]

        print(f"{key_id:<6} {key_masked:<30} {purpose:<15} {status:<10} {created_at}")

    print("=" * 80)
    print(f"总计: {len(keys)} 个 API Key")


async def revoke_key(args):
    """吊销指定的 API Key"""
    await user_storage.init_db()
    await apikey_storage.init_db()

    # 通过用户名获取用户 ID
    user = await user_storage.get_user_by_username(args.username)
    if not user:
        print(f"[ERROR] 错误：用户 '{args.username}' 不存在。")
        return

    user_id = user["id"]

    # 先列出用户的 Key，方便确认
    keys = await apikey_storage.list_api_keys_by_user(user_id)
    target_key = None

    for key in keys:
        if key["id"] == args.key_id:
            target_key = key
            break

    if not target_key:
        print(
            f"[ERROR] 未找到 ID 为 {args.key_id} 的 API Key，或该 Key 不属于用户 '{args.username}'。"
        )
        return

    if not target_key["is_active"]:
        print(f"ℹ️ ID 为 {args.key_id} 的 API Key 已经被吊销。")
        return

    # 确认操作
    if not args.force:
        print("⚠️  即将吊销以下 API Key：")
        print(f"   ID:      {target_key['id']}")
        print(f"   Key:     {mask_key(target_key['key_value'])}")
        print(f"   Purpose: {target_key['purpose'] or 'default'}")
        confirm = input("确认吊销? (yes/no): ")
        if confirm.lower() != "yes":
            print("[ERROR] 操作已取消。")
            return

    success = await apikey_storage.revoke_api_key(args.key_id, user_id)

    if success:
        print(f"[OK] API Key (ID: {args.key_id}) 已成功吊销。")
    else:
        print("[ERROR] 吊销失败：可能 Key 不存在或无权操作。")


async def main():
    parser = argparse.ArgumentParser(
        description="API Key 管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 为用户创建 API Key
  python src/manage_keys.py create --username alice --purpose "production"

  # 列出用户的所有 API Key
  python src/manage_keys.py list --username alice

  # 吊销 API Key
  python src/manage_keys.py revoke --username alice --key-id 123
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 创建 Key 子命令
    create_parser = subparsers.add_parser("create", help="创建新的 API Key")
    create_parser.add_argument("--username", required=True, help="用户名（必须已存在）")
    create_parser.add_argument(
        "--prefix", default="sk", help="API Key 的前缀 (默认: sk)"
    )
    create_parser.add_argument(
        "--purpose", default="default", help="API Key 的用途 (默认: default)"
    )
    create_parser.set_defaults(func=create_key)

    # 列出 Key 子命令
    list_parser = subparsers.add_parser("list", help="列出用户的所有 API Key")
    list_parser.add_argument("--username", required=True, help="用户名")
    list_parser.set_defaults(func=list_keys)

    # 吊销 Key 子命令
    revoke_parser = subparsers.add_parser("revoke", help="吊销指定的 API Key")
    revoke_parser.add_argument("--username", required=True, help="用户名")
    revoke_parser.add_argument(
        "--key-id", type=int, required=True, help="要吊销的 API Key ID"
    )
    revoke_parser.add_argument(
        "--force", action="store_true", help="强制吊销，跳过确认提示"
    )
    revoke_parser.set_defaults(func=revoke_key)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    await args.func(args)


if __name__ == "__main__":
    asyncio.run(main())
