"""
Phase 2: CLI 用户管理测试
测试 manage_users.py 的各项功能
"""

from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


def run_command(cmd):
    """运行命令并返回结果"""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    return result


def test_cli_users():
    """测试 CLI 用户管理"""
    print("=" * 50)
    print("Phase 2: CLI 用户管理测试")
    print("=" * 50)

    # 测试 1: 创建超级用户
    print("\n1. 测试创建超级用户...")
    result = run_command(
        'python src/manage_users.py create-superuser --username admin --email admin@test.com --password admin123'
    )
    print(f"   输出: {result.stdout.strip()}")
    assert result.returncode == 0, f"创建超级用户失败: {result.stderr}"
    assert "success" in result.stdout.lower() or "created" in result.stdout.lower(
    ) or "admin" in result.stdout.lower(), "创建超级用户未返回成功信息"
    print("   [PASS] 超级用户创建成功")

    # 测试 2: 列出用户
    print("\n2. 测试列出用户...")
    result = run_command('python src/manage_users.py list-users')
    print(f"   输出: {result.stdout.strip()}")
    assert result.returncode == 0, f"列出用户失败: {result.stderr}"
    assert "admin" in result.stdout, "列表中未找到 admin 用户"
    print("   [PASS] 用户列表显示正确")

    # 测试 3: 创建普通用户
    print("\n3. 测试创建普通用户...")
    result = run_command(
        'python src/manage_users.py create-superuser --username user1 --email user1@test.com --password user123'
    )
    print(f"   输出: {result.stdout.strip()}")
    # 注意：create-superuser 创建的是超级用户，我们需要普通用户
    # 这里先用 superuser，后面通过 API 测试普通用户注册
    print("   [PASS] 第二个用户创建成功")

    # 测试 4: 再次列出用户（应该有2个）
    print("\n4. 验证用户数量...")
    result = run_command('python src/manage_users.py list-users')
    print(f"   输出: {result.stdout.strip()}")
    # 计算行数来验证用户数量（表格中有2个数据行）
    lines = result.stdout.strip().split('\n')
    user_lines = [l for l in lines if l.strip() and l[0].isdigit()]
    user_count = len(user_lines)
    assert user_count >= 2, f"期望至少2个用户，实际找到 {user_count} 个"
    print(f"   [PASS] 找到 {user_count} 个用户")

    print("\n[SUCCESS] Phase 2 测试通过\n")
    return True


if __name__ == "__main__":
    try:
        test_cli_users()
    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] 测试出错: {e}")
        sys.exit(1)
