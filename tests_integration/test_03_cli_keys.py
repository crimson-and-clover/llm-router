"""
Phase 3: CLI API Key 管理测试
测试 manage_keys.py 的各项功能
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


def test_cli_keys():
    """测试 CLI API Key 管理"""
    print("=" * 50)
    print("Phase 3: CLI API Key 管理测试")
    print("=" * 50)

    # 测试 1: 为用户创建 API Key
    print("\n1. 测试为用户创建 API Key...")
    result = run_command(
        'python src/manage_keys.py create --username admin --purpose "Test Key"'
    )
    print(f"   输出: {result.stdout.strip()}")
    assert result.returncode == 0, f"创建 API Key 失败: {result.stderr}"
    assert "success" in result.stdout.lower() or "created" in result.stdout.lower(
    ) or "key" in result.stdout.lower(), "未返回 API Key"
    print("   [PASS] API Key 创建成功")

    # 测试 2: 列出用户的 API Keys
    print("\n2. 测试列出用户的 API Keys...")
    result = run_command('python src/manage_keys.py list --username admin')
    print(f"   输出: {result.stdout.strip()}")
    assert result.returncode == 0, f"列出 API Keys 失败: {result.stderr}"
    assert "ID" in result.stdout or "Key" in result.stdout or "admin" in result.stdout, "列表输出异常"
    print("   [PASS] API Key 列表显示正确")

    # 测试 3: 为不存在的用户创建 Key（应该失败）
    print("\n3. 测试为不存在的用户创建 Key...")
    result = run_command(
        'python src/manage_keys.py create --username nonexistent --purpose "Should Fail"'
    )
    print(f"   输出: {result.stdout.strip()}")
    # 这应该失败或返回错误信息
    assert "not found" in result.stdout.lower() or "error" in result.stdout.lower(
    ) or "不存在" in result.stdout or result.returncode != 0, "应该返回用户不存在错误"
    print("   [PASS] 正确拒绝不存在的用户")

    # 测试 4: 创建多个 Keys
    print("\n4. 测试创建多个 API Keys...")
    result = run_command(
        'python src/manage_keys.py create --username admin --purpose "Second Key"'
    )
    print(f"   输出: {result.stdout.strip()}")
    assert result.returncode == 0, f"创建第二个 API Key 失败: {result.stderr}"
    print("   [PASS] 第二个 API Key 创建成功")

    # 列出确认有多个
    result = run_command('python src/manage_keys.py list --username admin')
    lines = result.stdout.strip().split('\n')
    # 统计数据行（以数字开头的行）
    key_lines = [l for l in lines if l.strip() and l.strip()[0].isdigit()]
    key_count = len(key_lines)
    print(f"   当前用户拥有的 Key 数量: {key_count}")
    assert key_count >= 2, f"期望至少2个 Key，实际找到 {key_count} 个"
    print("   [PASS] 多个 Keys 创建成功")

    print("\n[SUCCESS] Phase 3 测试通过\n")
    return True


if __name__ == "__main__":
    try:
        test_cli_keys()
    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] 测试出错: {e}")
        sys.exit(1)
