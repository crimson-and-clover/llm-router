#!/usr/bin/env python3
"""
简单的 Chat Completions API 测试脚本

用法:
    python test_chat_complete.py                    # 非流式测试
    python test_chat_complete.py --stream           # 流式测试
    python test_chat_complete.py --model kimi/kimi-latest
    python test_chat_complete.py --api-key your_key
"""

import argparse
import json

import requests


def test_chat_completions(
    api_key: str,
    base_url: str = "http://localhost:8787",
    model: str = "test/test-model",
    stream: bool = False,
    message: str = "你好，请简单介绍一下你自己。",
) -> None:
    """测试 chat completions API"""

    url = f"{base_url}/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json; charset=utf-8",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个有用的AI助手。"},
            {"role": "user", "content": message},
        ],
        "stream": stream,
    }

    print(f"\n{'='*60}")
    print(f"请求 URL: {url}")
    print(f"模型: {model}")
    print(f"流式: {stream}")
    print(f"{'='*60}\n")

    try:
        response = requests.post(
            url, headers=headers, json=payload, stream=stream, timeout=60
        )
        response.raise_for_status()

        if stream:
            # 流式响应处理
            print("流式响应内容:\n")
            full_content = ""
            for line in response.iter_lines():
                if line:
                    line_text = line.decode("utf-8")
                    if line_text.startswith("data: "):
                        data = line_text[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                print(content, end="", flush=True)
                                full_content += content
                        except json.JSONDecodeError:
                            continue
            print("\n\n" + "=" * 60)
            print(f"完整响应 ({len(full_content)} 字符)")
        else:
            # 非流式响应处理
            data = response.json()
            print("响应结果:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0].get("message", {}).get("content", "")
                print(f"\n{'='*60}")
                print(f"AI 回复:\n{content}")
                print(f"{'='*60}")

            if "usage" in data:
                usage = data["usage"]
                print("\nToken 使用:")
                print(f"  - Prompt: {usage.get('prompt_tokens', 0)}")
                print(f"  - Completion: {usage.get('completion_tokens', 0)}")
                print(f"  - Total: {usage.get('total_tokens', 0)}")

        print("\n✅ 测试成功!")

    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP 错误: {e}")
        try:
            error_data = e.response.json()
            print(f"错误详情: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
        except Exception:
            print(f"响应内容: {e.response.text}")
    except requests.exceptions.ConnectionError:
        print(f"\n❌ 连接错误: 无法连接到 {base_url}")
        print("请确认服务是否已启动")
    except Exception as e:
        print(f"\n❌ 错误: {e}")


def test_models_list(api_key: str, base_url: str = "http://localhost:8787") -> None:
    """测试获取模型列表"""

    url = f"{base_url}/api/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}

    print(f"\n{'='*60}")
    print(f"获取模型列表: {url}")
    print(f"{'='*60}\n")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        print("可用模型:")
        for model in data.get("data", []):
            print(f"  - {model['id']} (owned_by: {model.get('owned_by', 'unknown')})")

        print(f"\n✅ 共 {len(data.get('data', []))} 个模型")

    except Exception as e:
        print(f"❌ 错误: {e}")


def main():
    parser = argparse.ArgumentParser(description="Chat Completions API 测试脚本")
    parser.add_argument(
        "--api-key", default="test-key", help="API Key (默认: test-key)"
    )
    parser.add_argument(
        "--base-url", default="http://localhost:8787", help="API 基础 URL"
    )
    parser.add_argument(
        "--model", default="test/test-model", help="模型名称 (格式: provider/model)"
    )
    parser.add_argument("--stream", action="store_true", help="启用流式响应")
    parser.add_argument(
        "--message", default="你好，请简单介绍一下你自己。", help="测试消息内容"
    )
    parser.add_argument("--list-models", action="store_true", help="仅获取模型列表")

    args = parser.parse_args()

    if args.list_models:
        test_models_list(args.api_key, args.base_url)
    else:
        test_chat_completions(
            api_key=args.api_key,
            base_url=args.base_url,
            model=args.model,
            stream=args.stream,
            message=args.message,
        )


if __name__ == "__main__":
    main()
