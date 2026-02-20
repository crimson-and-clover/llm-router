"""
Phase 6: 边缘 Worker 能力测试
测试边缘 Worker 的各项 API 功能
"""

import requests
import sys
import json
import time
import os
from pathlib import Path
import dotenv
dotenv.load_dotenv()


# Worker 基础配置
WORKER_URL = "http://localhost:8787"
API_BASE = f"{WORKER_URL}/api/v1"

# 测试用的 API Key（需要用户提前配置）
TEST_API_KEY = None

# 允许的模型（白名单）
ALLOWED_MODELS = {
    "deepseek": ["deepseek-chat"],
    "kimi": ["moonshot-v1-8k"],
    "test": ["test"],
}


def load_api_key():
    """加载测试用的 API Key"""
    global TEST_API_KEY

    # 尝试从环境变量或 .env 文件加载
    TEST_API_KEY = os.getenv("TEST_API_KEY")
    return TEST_API_KEY


def test_health_check():
    """测试健康检查端点"""
    print("\n1. 测试健康检查...")

    # GET /ping
    response = requests.get(
        f"{API_BASE}/ping",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"}
    )
    assert response.status_code == 200, f"GET /ping 失败: {response.status_code}"
    assert response.text == "OK", f"GET /ping 响应不正确: {response.text}"
    print("   [PASS] GET /api/v1/ping")

    # POST /ping
    response = requests.post(
        f"{API_BASE}/ping",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"}
    )
    assert response.status_code == 200, f"POST /ping 失败: {response.status_code}"
    assert response.text == "OK", f"POST /ping 响应不正确: {response.text}"
    print("   [PASS] POST /api/v1/ping")


def test_authentication():
    """测试认证机制"""
    print("\n2. 测试认证机制...")

    # 无认证
    response = requests.get(f"{API_BASE}/models")
    assert response.status_code == 401, f"无认证应返回 401，实际: {response.status_code}"
    print("   [PASS] 无认证返回 401")

    # 无效 API Key
    response = requests.get(
        f"{API_BASE}/models",
        headers={"Authorization": "Bearer invalid-key"}
    )
    assert response.status_code == 401, f"无效 Key 应返回 401，实际: {response.status_code}"
    print("   [PASS] 无效 API Key 返回 401")

    # 错误的 Authorization 格式
    response = requests.get(
        f"{API_BASE}/models",
        headers={"Authorization": "Basic dGVzdDp0ZXN0"}
    )
    assert response.status_code == 401, f"错误格式应返回 401，实际: {response.status_code}"
    print("   [PASS] 错误 Authorization 格式返回 401")


def test_models_list():
    """测试模型列表（验证白名单限制）"""
    print("\n3. 测试模型列表...")

    response = requests.get(
        f"{API_BASE}/models",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"}
    )
    assert response.status_code == 200, f"获取模型列表失败: {response.status_code}"

    data = response.json()
    assert data.get("object") == "list", "响应格式不正确"
    assert "data" in data, "响应缺少 data 字段"

    models = data["data"]
    model_ids = [m["id"] for m in models]
    print(f"   可用模型: {model_ids}")

    # 验证白名单
    for model_id in model_ids:
        provider, model_name = model_id.split("/", 1)
        assert provider in ALLOWED_MODELS, f"Provider '{provider}' 不在白名单中"
        assert model_name in ALLOWED_MODELS[provider], f"模型 '{model_name}' 不在白名单中"

    # 验证必须包含指定的模型
    expected_models = [
        f"deepseek/{ALLOWED_MODELS['deepseek'][0]}",
        f"kimi/{ALLOWED_MODELS['kimi'][0]}"
    ]
    for expected in expected_models:
        assert expected in model_ids, f"缺少必需的模型: {expected}"

    print("   [PASS] 模型列表符合白名单限制")
    return model_ids


def test_chat_completion_non_stream(provider: str, model: str):
    """测试非流式对话完成"""
    print(f"\n4. 测试 {provider}/{model} 非流式对话...")

    response = requests.post(
        f"{API_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {TEST_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": f"{provider}/{model}",
            "messages": [{"role": "user", "content": "Hello, who are you?"}],
            "stream": False
        }
    )

    assert response.status_code == 200, f"请求失败: {response.status_code} - {response.text}"

    data = response.json()
    assert "choices" in data, "响应缺少 choices"
    assert len(data["choices"]) > 0, "choices 为空"
    assert data["choices"][0]["message"]["content"], "响应内容为空"
    assert "usage" in data, "响应缺少 usage"

    content = data["choices"][0]["message"]["content"]
    usage = data["usage"]
    print(f"   响应: {content[:50]}...")
    print(
        f"   Token 用量: prompt={usage.get('prompt_tokens')}, completion={usage.get('completion_tokens')}")
    print(f"   [PASS] {provider}/{model} 非流式对话")


def test_chat_completion_stream(provider: str, model: str):
    """测试流式对话完成"""
    print(f"\n5. 测试 {provider}/{model} 流式对话...")

    response = requests.post(
        f"{API_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {TEST_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": f"{provider}/{model}",
            "messages": [{"role": "user", "content": "Say hello briefly"}],
            "stream": True
        },
        stream=True
    )

    assert response.status_code == 200, f"请求失败: {response.status_code} - {response.text}"
    assert "text/event-stream" in response.headers.get(
        "Content-Type", ""), "Content-Type 不正确"

    # 读取流式响应
    chunks = []
    for line in response.iter_lines():
        if line:
            line_str = line.decode("utf-8")
            if line_str.startswith("data: "):
                data = line_str[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get("content"):
                        chunks.append(chunk["choices"][0]["delta"]["content"])
                except json.JSONDecodeError:
                    pass

    full_content = "".join(chunks)
    assert len(full_content) > 0, "流式响应内容为空"
    print(f"   响应: {full_content[:50]}...")
    print(f"   接收 {len(chunks)} 个 chunk")
    print(f"   [PASS] {provider}/{model} 流式对话")


def test_error_handling():
    """测试错误处理"""
    print("\n6. 测试错误处理...")

    # 无效模型格式（无斜杠）
    response = requests.post(
        f"{API_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {TEST_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "invalid-model",
            "messages": [{"role": "user", "content": "Hello"}]
        }
    )
    assert response.status_code == 404, f"无效模型格式应返回 404，实际: {response.status_code}"
    print("   [PASS] 无效模型格式返回 404")

    # 不存在的 Provider
    response = requests.post(
        f"{API_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {TEST_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "nonexistent/model",
            "messages": [{"role": "user", "content": "Hello"}]
        }
    )
    assert response.status_code == 404, f"不存在 Provider 应返回 404，实际: {response.status_code}"
    print("   [PASS] 不存在 Provider 返回 404")

    # 无效 JSON
    response = requests.post(
        f"{API_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {TEST_API_KEY}",
            "Content-Type": "application/json"
        },
        data="invalid json"
    )
    assert response.status_code == 400, f"无效 JSON 应返回 400，实际: {response.status_code}"
    print("   [PASS] 无效 JSON 返回 400")


def test_worker_availability():
    """测试 Worker 是否可用"""
    print("\n0. 检查 Worker 可用性...")
    try:
        response = requests.get(f"{WORKER_URL}/api/v1/ping", timeout=5)
        print(f"   Worker 运行在 {WORKER_URL}")
        return True
    except requests.ConnectionError:
        print(f"   [ERROR] 无法连接到 Worker: {WORKER_URL}")
        print("   请确保 Worker 已启动: cd worker && npm run dev")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Phase 6: 边缘 Worker 能力测试")
    print("=" * 60)

    # 加载配置
    load_api_key()
    print(f"   使用 API Key: {TEST_API_KEY[:10]}...")

    # 检查 Worker 可用性
    if not test_worker_availability():
        print("\n[FAIL] Worker 未启动，测试中止")
        sys.exit(1)

    try:
        # 运行测试
        test_health_check()
        test_authentication()
        model_ids = test_models_list()

        # 测试 Kimi
        kimi_model = ALLOWED_MODELS["kimi"][0]
        test_chat_completion_non_stream("kimi", kimi_model)
        test_chat_completion_stream("kimi", kimi_model)

        # 测试 DeepSeek
        deepseek_model = ALLOWED_MODELS["deepseek"][0]
        test_chat_completion_non_stream("deepseek", deepseek_model)
        test_chat_completion_stream("deepseek", deepseek_model)

        test_error_handling()

        print("\n" + "=" * 60)
        print("[SUCCESS] Phase 6 测试通过!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n[FAIL] 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
