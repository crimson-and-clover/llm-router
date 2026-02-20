"""Test Provider - 用于性能测试的模拟 Provider

此 Provider 不调用外部 API，而是快速返回模拟响应，
用于测试 API Mirror 本身的性能而不受外部服务影响。
"""

import json
import time
from typing import Any, AsyncIterator, Dict, Optional

from .base import BaseProvider


class TestProvider(BaseProvider):
    """测试用 Provider，提供快速、可预测的响应"""

    def __init__(
        self,
        fixed_response: Optional[str] = None,
        response_delay_ms: float = 0.0,  # 移除延迟用于极限性能测试
        stream_chunk_count: int = 10,
        stream_chunk_delay_ms: float = 0.0,  # 移除延迟
    ):
        """
        Args:
            fixed_response: 固定响应内容，None则使用默认内容
            response_delay_ms: 非流式响应延迟（毫秒）
            stream_chunk_count: 流式响应分块数量
            stream_chunk_delay_ms: 流式响应块间延迟（毫秒）
        """
        self.fixed_response = (
            fixed_response or "This is a test response from TestProvider."
        )
        self.response_delay_ms = response_delay_ms
        self.stream_chunk_count = stream_chunk_count
        self.stream_chunk_delay_ms = stream_chunk_delay_ms

    def _split_content(self, content: str, chunks: int) -> list:
        """将内容分割成多个块"""
        words = content.split()
        if chunks >= len(words):
            return words

        result = []
        chunk_size = len(words) // chunks
        for i in range(chunks):
            start = i * chunk_size
            if i == chunks - 1:
                end = len(words)
            else:
                end = (i + 1) * chunk_size
            result.append(" ".join(words[start:end]))
        return result

    async def chat_completions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """模拟非流式聊天完成"""
        # 模拟延迟
        # await asyncio.sleep(self.response_delay_ms / 1000)

        # 构建标准 OpenAI 格式响应
        model = payload.get("model", "test-model")
        messages = payload.get("messages", [])

        # 根据请求生成响应
        user_message = ""
        if messages:
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break

        response_content = self.fixed_response
        if "hello" in user_message.lower() or "hi" in user_message.lower():
            response_content = "Hello! This is TestProvider speaking."
        elif "long" in user_message.lower() or "paragraph" in user_message.lower():
            response_content = " ".join(
                ["This is a longer response for testing purposes." * 5]
            )

        return {
            "id": f"test-{int(time.time() * 1000)}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": response_content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": len(user_message.split()) * 2,
                "completion_tokens": len(response_content.split()),
                "total_tokens": len(user_message.split()) * 2
                + len(response_content.split()),
            },
        }

    async def chat_completions_stream(
        self, payload: Dict[str, Any]
    ) -> AsyncIterator[str]:
        """模拟流式聊天完成"""
        model = payload.get("model", "test-model")
        messages = payload.get("messages", [])

        # 获取用户消息
        user_message = ""
        if messages:
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break

        response_content = self.fixed_response
        if "hello" in user_message.lower() or "hi" in user_message.lower():
            response_content = "Hello! This is TestProvider speaking for stream test."
        elif "long" in user_message.lower() or "paragraph" in user_message.lower():
            response_content = " ".join(
                [f"Stream chunk {i} " for i in range(self.stream_chunk_count)]
            )

        # 分割内容
        chunks = self._split_content(response_content, self.stream_chunk_count)

        # 生成 SSE 格式流
        for i, chunk in enumerate(chunks):
            # await asyncio.sleep(self.stream_chunk_delay_ms / 1000)

            data = {
                "id": f"test-{int(time.time() * 1000)}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": chunk + " " if i < len(chunks) - 1 else chunk
                        },
                        "finish_reason": None if i < len(chunks) - 1 else "stop",
                    }
                ],
            }
            yield f"data: {json.dumps(data)}"

        yield "data: [DONE]"

    async def list_models(self) -> Dict[str, Any]:
        """返回测试模型列表"""
        # await asyncio.sleep(10 / 1000)  # 10ms 延迟

        return {
            "object": "list",
            "data": [
                {
                    "id": "test-fast",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "test-provider",
                },
                {
                    "id": "test-slow",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "test-provider",
                },
                {
                    "id": "test-stream",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "test-provider",
                },
            ],
        }
