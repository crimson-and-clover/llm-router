import json
import os
from pathlib import Path

from dotenv import load_dotenv
import requests

load_dotenv()

base_url = os.environ.get("BASE_URL")
api_key = os.environ.get("API_KEY")
print(f"base_url: {base_url}")
print(f"api_key: {api_key}")
print("--------------------------------")

def test_cursor():
    url = f"{base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "test/test",  # Kimi 最新的深度思考模型
        "messages": [
            {"role": "system", "content": "你是 Kimi。"},
            {"role": "user", "content": "1+1 等于几？"},
            {"role": "assistant",
                "content": "1+1 等于 **2**。\n\n（如果在二进制中，1+1 等于 10；但通常默认是十进制，所以答案是 2。）"}
        ],
        "stream": True  # 开启流式输出
    }

    print("--- 开始接收流式响应 ---\n")

    # 使用 stream=True 保持连接
    response = requests.post(url, json=payload, headers=headers, stream=True)

    # 检查状态
    if response.status_code != 200:
        print(f"请求失败: {response.status_code}, {response.text}")
        return

    # 使用 iter_lines 处理 SSE 协议，它会自动处理 Brotli/Gzip 解压
    # for line in response.iter_lines():
    #     print(f"接收：{line}")
    #     if not line:
    #         continue

    print(response.text)


if __name__ == "__main__":
    test_cursor()
