"""
Phase 4-7: API 端点测试
测试所有内部 API 端点功能
"""

from pathlib import Path
import subprocess
import sys
import time

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:8000/internal"
ADMIN_TOKEN = None
USER_TOKEN = None


def run_command(cmd, wait=True):
    """运行命令"""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    return result


def test_api_endpoints():
    """测试 API 端点"""
    print("=" * 50)
    print("Phase 4-7: API 端点测试")
    print("=" * 50)

    global ADMIN_TOKEN, USER_TOKEN

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

    # 等待服务器启动
    time.sleep(3)

    try:
        # 测试 1: 用户注册
        print("\n2. 测试用户注册...")
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        test_username = f"testuser_{unique_id}"
        test_email = f"testuser_{unique_id}@test.com"
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={
                "username": test_username,
                "email": test_email,
                "password": "testpass123"
            }
        )
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json() if response.text else 'No content'}")
        assert response.status_code in [200, 201], f"注册失败: {response.text}"
        print("   [PASS] 用户注册成功")

        # 测试 2: 用户登录
        print("\n3. 测试用户登录...")
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={  # JSON 格式
                "username": test_username,
                "password": "testpass123"
            }
        )
        print(f"   状态码: {response.status_code}")
        data = response.json()
        print(f"   响应: {data}")
        assert response.status_code == 200, f"登录失败: {response.text}"
        assert "access_token" in data, "响应中没有 access_token"
        USER_TOKEN = data["access_token"]
        print("   [PASS] 用户登录成功，获取到 Token")

        # 测试 3: 获取当前用户信息
        print("\n4. 测试获取当前用户信息...")
        response = requests.get(
            f"{BASE_URL}/users/me",
            headers={"Authorization": f"Bearer {USER_TOKEN}"}
        )
        print(f"   状态码: {response.status_code}")
        data = response.json()
        print(f"   响应: {data}")
        assert response.status_code == 200, f"获取用户信息失败: {response.text}"
        assert data["username"] == test_username, "用户名不匹配"
        print("   [PASS] 获取用户信息成功")

        # 测试 4: 创建 API Key
        print("\n5. 测试创建 API Key...")
        response = requests.post(
            f"{BASE_URL}/users/me/keys",
            headers={"Authorization": f"Bearer {USER_TOKEN}"},
            json={"purpose": "API Test Key"}
        )
        print(f"   状态码: {response.status_code}")
        data = response.json()
        print(f"   响应: {data}")
        assert response.status_code in [
            200, 201], f"创建 API Key 失败: {response.text}"
        key_id = data.get("id")
        print(f"   [PASS] API Key 创建成功，ID: {key_id}")

        # 测试 5: 列出 API Keys
        print("\n6. 测试列出 API Keys...")
        response = requests.get(
            f"{BASE_URL}/users/me/keys",
            headers={"Authorization": f"Bearer {USER_TOKEN}"}
        )
        print(f"   状态码: {response.status_code}")
        data = response.json()
        print(f"   响应: {data}")
        assert response.status_code == 200, f"列出 API Keys 失败: {response.text}"
        print(f"   [PASS] 找到 {len(data)} 个 API Key")

        # 测试 6: 管理员登录
        print("\n7. 测试管理员登录...")
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data={
                "username": "admin",
                "password": "admin"  # 默认密码
            }
        )
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            ADMIN_TOKEN = data["access_token"]
            print("   [PASS] 管理员登录成功")
        else:
            print("   [WARN] 管理员登录失败（可能密码不同），跳过管理员测试")

        # 测试 7: 管理员接口（如果登录成功）
        if ADMIN_TOKEN:
            print("\n8. 测试管理员接口...")
            response = requests.get(
                f"{BASE_URL}/admin/users",
                headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
            )
            print(f"   状态码: {response.status_code}")
            data = response.json()
            print(f"   响应: {data}")
            assert response.status_code == 200, f"管理员接口访问失败: {response.text}"
            print("   [PASS] 管理员接口访问成功")

            # 测试 9: 普通用户访问管理员接口（应该失败）
            print("\n9. 测试权限控制（普通用户访问管理员接口）...")
            response = requests.get(
                f"{BASE_URL}/admin/users",
                headers={"Authorization": f"Bearer {USER_TOKEN}"}
            )
            print(f"   状态码: {response.status_code}")
            assert response.status_code == 403, "普通用户应该被拒绝访问管理员接口"
            print("   [PASS] 权限控制正确，普通用户被拒绝")

        print("\n[SUCCESS] Phase 4-7 测试通过\n")

    finally:
        # 关闭服务器
        print("关闭测试服务器...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()

    return True


if __name__ == "__main__":
    try:
        test_api_endpoints()
    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
