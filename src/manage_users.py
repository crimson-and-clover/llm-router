import argparse
import asyncio
import getpass
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.core.security import hash_password
from src.storage import user_storage


def validate_username(username: str) -> bool:
    """验证用户名格式"""
    if not username or len(username) < 3 or len(username) > 32:
        return False
    return bool(re.match(r"^[a-zA-Z0-9_]+$", username))


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    if not email:
        return False
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """验证密码强度

    Returns:
        (是否有效, 错误信息)
    """
    if not password or len(password) < 6:
        return False, "密码长度至少 6 位"
    if len(password) > 64:
        return False, "密码长度不能超过 64 位"

    # 检查字符类型
    has_letter = bool(re.search(r"[a-zA-Z]", password))
    has_number = bool(re.search(r"\d", password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))

    type_count = sum([has_letter, has_number, has_special])
    if type_count < 2:
        return False, "密码需包含字母、数字或特殊字符中的至少两种"

    return True, ""


def format_status(is_active: bool, is_superuser: bool) -> str:
    """格式化用户状态显示"""
    status_parts = []
    if is_active:
        status_parts.append("Active")
    else:
        status_parts.append("Inactive")

    if is_superuser:
        status_parts.append("Superuser")

    return " | ".join(status_parts)


async def create_superuser(args):
    """创建超级用户"""
    await user_storage.init_db()

    # 清理和验证用户名
    username = args.username.strip()
    if not validate_username(username):
        print("[ERROR] 错误：用户名格式不正确（3-32位字母、数字、下划线）。")
        return

    # 清理和验证邮箱
    email = args.email.strip()
    if not validate_email(email):
        print("[ERROR] 错误：邮箱格式不正确。")
        return

    # 检查用户名是否已存在
    existing_user = await user_storage.get_user_by_username(username)
    if existing_user:
        print(f"[ERROR] 错误：用户名 '{username}' 已存在。")
        return

    # 检查邮箱是否已存在
    existing_email = await user_storage.get_user_by_email(email)
    if existing_email:
        print(f"[ERROR] 错误：邮箱 '{email}' 已存在。")
        return

    # 如果没有提供密码，交互式输入
    password = args.password
    if not password:
        password = getpass.getpass("请输入密码: ")
        if not password:
            print("[ERROR] 错误：密码不能为空。")
            return
        password_confirm = getpass.getpass("请再次输入密码: ")
        if password != password_confirm:
            print("[ERROR] 错误：两次输入的密码不一致。")
            return

    # 验证密码强度
    is_valid, error_msg = validate_password_strength(password)
    if not is_valid:
        print(f"[ERROR] 错误：{error_msg}")
        return

    # 哈希密码（使用 bcrypt）
    password_hash = hash_password(password)

    # 创建超级用户
    user_id = await user_storage.create_user(
        username=username, email=email, password_hash=password_hash, is_superuser=True
    )

    if user_id:
        print("=" * 50)
        print("[OK] 超级用户创建成功！")
        print(f"ID:       {user_id}")
        print(f"Username: {username}")
        print(f"Email:    {email}")
        print("Status:   Active | Superuser")
        print("=" * 50)
    else:
        print("[ERROR] 创建失败：数据库错误。")


async def list_users(args):
    """列出所有用户"""
    await user_storage.init_db()

    users = await user_storage.list_users()

    if not users:
        print("ℹ️  系统中没有用户。")
        return

    print("=" * 80)
    print(f"[LIST] 用户列表 (共 {len(users)} 人)")
    print("=" * 80)
    print(f"{'ID':<6} {'Username':<20} {'Email':<30} {'Status'}")
    print("-" * 80)

    for user in users:
        user_id = user["id"]
        username = user["username"]
        email = user["email"]
        status = format_status(user["is_active"], user["is_superuser"])

        print(f"{user_id:<6} {username:<20} {email:<30} {status}")

    print("=" * 80)

    # 统计信息
    total = len(users)
    active = sum(1 for u in users if u["is_active"])
    superusers = sum(1 for u in users if u["is_superuser"])

    print(f"总计: {total} | 活跃: {active} | 超级用户: {superusers}")


async def deactivate_user(args):
    """吊销用户账号"""
    await user_storage.init_db()

    # 获取用户信息
    user = await user_storage.get_user_by_id(args.user_id)
    if not user:
        print(f"[ERROR] 错误：用户 ID {args.user_id} 不存在。")
        return

    if not user["is_active"]:
        print(f"ℹ️  用户 '{user['username']}' 已经被吊销。")
        return

    # 如果要吊销的是超级用户，检查保护机制
    if user["is_superuser"]:
        can_revoke = await user_storage.can_revoke_superuser(args.user_id)
        if not can_revoke:
            print("[ERROR] 错误：不能吊销最后一个超级用户。")
            return

    # 确认操作
    if not args.force:
        print("⚠️  即将吊销用户：")
        print(f"   ID:       {user['id']}")
        print(f"   Username: {user['username']}")
        print(f"   Email:    {user['email']}")
        confirm = input("确认吊销? (yes/no): ")
        if confirm.lower() != "yes":
            print("[ERROR] 操作已取消。")
            return

    success = await user_storage.deactivate_user(args.user_id)

    if success:
        print(f"[OK] 用户 '{user['username']}' 已成功吊销。")
    else:
        print("[ERROR] 吊销失败：数据库错误。")


async def activate_user(args):
    """激活用户账号"""
    await user_storage.init_db()

    user = await user_storage.get_user_by_id(args.user_id)
    if not user:
        print(f"[ERROR] 错误：用户 ID {args.user_id} 不存在。")
        return

    if user["is_active"]:
        print(f"ℹ️  用户 '{user['username']}' 已经是活跃状态。")
        return

    success = await user_storage.activate_user(args.user_id)

    if success:
        print(f"[OK] 用户 '{user['username']}' 已成功激活。")
    else:
        print("[ERROR] 激活失败：数据库错误。")


async def promote_user(args):
    """提升用户为超级用户"""
    await user_storage.init_db()

    user = await user_storage.get_user_by_id(args.user_id)
    if not user:
        print(f"[ERROR] 错误：用户 ID {args.user_id} 不存在。")
        return

    if user["is_superuser"]:
        print(f"ℹ️  用户 '{user['username']}' 已经是超级用户。")
        return

    success = await user_storage.promote_to_superuser(args.user_id)

    if success:
        print(f"[OK] 用户 '{user['username']}' 已提升为超级用户。")
    else:
        print("[ERROR] 提升失败：数据库错误。")


async def demote_user(args):
    """取消用户超级用户权限"""
    await user_storage.init_db()

    user = await user_storage.get_user_by_id(args.user_id)
    if not user:
        print(f"[ERROR] 错误：用户 ID {args.user_id} 不存在。")
        return

    if not user["is_superuser"]:
        print(f"ℹ️  用户 '{user['username']}' 不是超级用户。")
        return

    # 检查保护机制
    can_revoke = await user_storage.can_revoke_superuser(args.user_id)
    if not can_revoke:
        print("[ERROR] 错误：不能取消最后一个超级用户的权限。")
        return

    # 确认操作
    if not args.force:
        print("⚠️  即将取消用户的超级用户权限：")
        print(f"   ID:       {user['id']}")
        print(f"   Username: {user['username']}")
        print(f"   Email:    {user['email']}")
        confirm = input("确认取消超级用户权限? (yes/no): ")
        if confirm.lower() != "yes":
            print("[ERROR] 操作已取消。")
            return

    success = await user_storage.demote_from_superuser(args.user_id)

    if success:
        print(f"[OK] 用户 '{user['username']}' 的超级用户权限已取消。")
    else:
        print("[ERROR] 取消失败：数据库错误。")


async def main():
    parser = argparse.ArgumentParser(
        description="用户管理工具 - 用于创建和管理超级用户",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 创建超级用户
  python src/manage_users.py create-superuser --username admin --email admin@example.com

  # 列出所有用户
  python src/manage_users.py list-users

  # 吊销用户
  python src/manage_users.py deactivate-user --user-id 123

  # 提升用户为超级用户
  python src/manage_users.py promote-user --user-id 456
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 创建超级用户
    create_parser = subparsers.add_parser("create-superuser", help="创建新的超级用户")
    create_parser.add_argument("--username", required=True, help="用户名")
    create_parser.add_argument("--email", required=True, help="邮箱地址")
    create_parser.add_argument("--password", help="密码（如果不提供将交互式输入）")
    create_parser.set_defaults(func=create_superuser)

    # 列出用户
    list_parser = subparsers.add_parser("list-users", help="列出所有用户")
    list_parser.set_defaults(func=list_users)

    # 吊销用户
    deactivate_parser = subparsers.add_parser("deactivate-user", help="吊销用户账号")
    deactivate_parser.add_argument(
        "--user-id", type=int, required=True, help="要吊销的用户 ID"
    )
    deactivate_parser.add_argument(
        "--force", action="store_true", help="强制吊销，跳过确认提示"
    )
    deactivate_parser.set_defaults(func=deactivate_user)

    # 激活用户
    activate_parser = subparsers.add_parser(
        "activate-user", help="激活已吊销的用户账号"
    )
    activate_parser.add_argument(
        "--user-id", type=int, required=True, help="要激活的用户 ID"
    )
    activate_parser.set_defaults(func=activate_user)

    # 提升为超级用户
    promote_parser = subparsers.add_parser(
        "promote-user", help="将普通用户提升为超级用户"
    )
    promote_parser.add_argument(
        "--user-id", type=int, required=True, help="要提升的用户 ID"
    )
    promote_parser.set_defaults(func=promote_user)

    # 取消超级用户权限
    demote_parser = subparsers.add_parser("demote-user", help="取消用户的超级用户权限")
    demote_parser.add_argument(
        "--user-id", type=int, required=True, help="要取消权限的用户 ID"
    )
    demote_parser.add_argument(
        "--force", action="store_true", help="强制取消，跳过确认提示"
    )
    demote_parser.set_defaults(func=demote_user)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    await args.func(args)


if __name__ == "__main__":
    asyncio.run(main())
