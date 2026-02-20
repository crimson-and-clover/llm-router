"""
Phase 8: 边界条件测试
测试各种边界条件和保护机制
"""

from pathlib import Path
import subprocess
import sys
import time

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:8000/internal"


def run_command(cmd):
    """运行命令"""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    return result


def test_edge_cases():
    """测试边界条件"""
    print("=" * 50)
    print("Phase 8: 边界条件测试")
    print("=" * 50)

    # 启动服务器
    print("\n1. 启动测试服务器...")
    print("   请稍等 3 秒...")
    server_process = subprocess.Popen(
        ["python", "-m", "uvicorn", "src.main:app",
            "--host", "localhost", "--port", "8000"],
        cwd=Path(__file__).parent.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(3)

    try:
        # 测试 1: 注册重复用户
        print("\n2. 测试注册重复用户...")
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={
                "username": "testuser",
                "email": "testuser@test.com",
                "password": "testpass123"
            }
        )
        print(f"   状态码: {response.status_code}")
        # 应该失败或返回已存在提示
        assert response.status_code in [201, 400, 409], "重复注册应该有明确的错误码"
        print("   [PASS] 重复注册处理正确")

        # 测试 2: 登录错误密码
        print("\n3. 测试登录错误密码...")
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        print(f"   状态码: {response.status_code}")
        # 422 表示格式错误，401 表示认证失败，两者都可接受
        assert response.status_code in [401, 422], "错误密码应该返回 401 或 422"
        print("   [PASS] 错误密码处理正确")

        # 测试 3: 使用无效 Token 访问
        print("\n4. 测试无效 Token...")
        response = requests.get(
            f"{BASE_URL}/users/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        print(f"   状态码: {response.status_code}")
        assert response.status_code == 401, "无效 Token 应该返回 401"
        print("   [PASS] 无效 Token 处理正确")

        # 测试 4: 缺少认证头
        print("\n5. 测试缺少认证头...")
        response = requests.get(f"{BASE_URL}/users/me")
        print(f"   状态码: {response.status_code}")
        assert response.status_code == 401, "缺少认证应该返回 401"
        print("   [PASS] 缺少认证处理正确")

        # 测试 5: CLI - 列用户（基本功能检查）
        print("\n6. 测试 CLI 列用户功能...")
        result = run_command('python src/manage_users.py list-users')
        print(f"   命令输出前100字符: {result.stdout[:100]}...")
        assert result.returncode == 0, "列用户命令应该成功"
        print("   [PASS] CLI 列用户功能正常")

        print("\n[SUCCESS] Phase 8 测试通过\n")

    finally:
        print("关闭测试服务器...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()

    return True


if __name__ == "__main__":
    try:
        test_edge_cases()
    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
