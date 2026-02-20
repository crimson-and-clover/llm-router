"""单元测试：测试 DeepSeek 和 Kimi Provider 的接口"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

from dotenv import load_dotenv
import pytest

from src.providers import DeepSeekProvider, KimiProvider
from src.providers.deepseek import merge_tool_content

# 加载 .env 文件
load_dotenv()

# 从环境变量读取配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "test-api-key")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
KIMI_API_KEY = os.getenv("KIMI_API_KEY", "test-kimi-key")
KIMI_BASE_URL = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn")


# =============================================================================
# DeepSeek Provider Tests
# =============================================================================


class TestDeepSeekProvider:
    """测试 DeepSeekProvider 类"""

    @pytest.fixture
    def provider(self):
        """创建测试用的 provider 实例"""
        return DeepSeekProvider(
            base_url=DEEPSEEK_BASE_URL,
            api_key=DEEPSEEK_API_KEY
        )

    @pytest.fixture
    def sample_payload(self):
        """示例请求 payload"""
        return {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"}
            ],
            "stream": False
        }

    @pytest.fixture
    def sample_response(self):
        """示例 API 响应"""
        return {
            "id": "test-id",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "deepseek-chat",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help you today?"
                    },
                    "finish_reason": "stop"
                }
            ]
        }

    def test_init(self, provider):
        """测试初始化"""
        assert provider.base_url == DEEPSEEK_BASE_URL
        assert provider.api_key == DEEPSEEK_API_KEY

    def test_headers(self, provider):
        """测试请求头生成"""
        headers = provider._headers()
        assert headers["Authorization"] == f"Bearer {DEEPSEEK_API_KEY}"
        assert headers["Accept"] == "application/json"
        assert headers["Accept-Encoding"] == "gzip, br"

    def test_preprocess_payload_no_tool_messages(self, provider, sample_payload):
        """测试 payload 预处理：没有 tool 消息时保持不变"""
        result = provider.preprocess_payload(sample_payload)
        assert result == sample_payload
        # 确保创建了新的对象，没有修改原 payload
        assert result is not sample_payload

    def test_preprocess_payload_with_tool_messages(self, provider):
        """测试 payload 预处理：处理 tool 消息"""
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": "Hello"},
                {
                    "role": "tool",
                    "content": [
                        {"type": "text", "text": "Tool result"},
                        {"type": "image_url", "image_url": {
                            "url": "http://example.com/image.png"}}
                    ]
                }
            ]
        }
        result = provider.preprocess_payload(payload)

        tool_msg = result["messages"][1]
        assert tool_msg["role"] == "tool"
        assert "[Attached Image: http://example.com/image.png]" in tool_msg["content"]
        assert "Tool result" in tool_msg["content"]

    @pytest.mark.asyncio
    async def test_chat_completions_success(self, provider, sample_payload, sample_response):
        """测试 chat_completions 成功调用"""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_response
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await provider.chat_completions(sample_payload)

        assert result == sample_response
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == f"{DEEPSEEK_BASE_URL}/chat/completions"
        assert call_args[1]["json"]["model"] == "deepseek-chat"

    @pytest.mark.asyncio
    async def test_chat_completions_http_error(self, provider, sample_payload):
        """测试 chat_completions HTTP 错误处理"""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception) as exc_info:
                await provider.chat_completions(sample_payload)
            assert "HTTP Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_chat_completions_stream_success(self, provider):
        """测试流式响应成功"""
        payload = {"model": "deepseek-chat",
                   "messages": [{"role": "user", "content": "Hello"}]}

        mock_stream_response = MagicMock()
        mock_stream_response.status_code = 200
        mock_stream_response.aiter_lines = MagicMock(return_value=AsyncIteratorMock([
            "data: {}",
            "data: {}",
            ""
        ]))
        mock_stream_response.__aenter__ = AsyncMock(
            return_value=mock_stream_response)
        mock_stream_response.__aexit__ = AsyncMock(return_value=None)

        # stream() 返回一个异步上下文管理器，所以需要设置为 AsyncMock
        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_stream_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            lines = []
            async for line in provider.chat_completions_stream(payload):
                lines.append(line)

        assert len(lines) == 2

    @pytest.mark.asyncio
    async def test_chat_completions_stream_error(self, provider):
        """测试流式响应错误处理"""
        payload = {"model": "deepseek-chat",
                   "messages": [{"role": "user", "content": "Hello"}]}

        mock_stream_response = MagicMock()
        mock_stream_response.status_code = 401
        mock_stream_response.aread = AsyncMock(return_value=b"Unauthorized")
        mock_stream_response.__aenter__ = AsyncMock(
            return_value=mock_stream_response)
        mock_stream_response.__aexit__ = AsyncMock(return_value=None)

        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_stream_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception):
                async for _ in provider.chat_completions_stream(payload):
                    pass

    @pytest.mark.asyncio
    async def test_list_models_success(self, provider):
        """测试获取模型列表成功"""
        sample_models = {
            "object": "list",
            "data": [
                {
                    "id": "deepseek-chat",
                    "object": "model",
                    "created": 1234567890,
                    "owned_by": "deepseek"
                },
                {
                    "id": "deepseek-coder",
                    "object": "model",
                    "created": 1234567891,
                    "owned_by": "deepseek"
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = sample_models
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await provider.list_models()

        assert result == sample_models
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert call_args[0][0] == f"{DEEPSEEK_BASE_URL}/models"

    @pytest.mark.asyncio
    async def test_list_models_http_error(self, provider):
        """测试获取模型列表 HTTP 错误"""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API Error")

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception) as exc_info:
                await provider.list_models()
            assert "API Error" in str(exc_info.value)


# =============================================================================
# Kimi Provider Tests
# =============================================================================


class TestKimiProvider:
    """测试 KimiProvider 类"""

    @pytest.fixture
    def provider(self):
        """创建测试用的 provider 实例"""
        return KimiProvider(
            base_url=KIMI_BASE_URL,
            api_key=KIMI_API_KEY
        )

    @pytest.fixture
    def sample_payload(self):
        """示例请求 payload"""
        return {
            "model": "moonshot-v1-8k",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"}
            ]
        }

    @pytest.fixture
    def sample_response(self):
        """示例 API 响应"""
        return {
            "id": "kimi-test-id",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "moonshot-v1-8k",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I assist you?"
                    },
                    "finish_reason": "stop"
                }
            ]
        }

    def test_init(self, provider):
        """测试初始化"""
        assert provider.base_url == KIMI_BASE_URL
        assert provider.api_key == KIMI_API_KEY

    def test_headers(self, provider):
        """测试请求头生成"""
        headers = provider._headers()
        assert headers["Authorization"] == f"Bearer {KIMI_API_KEY}"
        assert headers["Accept"] == "application/json"

    @pytest.mark.asyncio
    async def test_chat_completions_success(self, provider, sample_payload, sample_response):
        """测试 chat_completions 成功调用"""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_response
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await provider.chat_completions(sample_payload)

        assert result == sample_response
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == f"{KIMI_BASE_URL}/chat/completions"

    @pytest.mark.asyncio
    async def test_chat_completions_http_error(self, provider, sample_payload):
        """测试 chat_completions HTTP 错误处理"""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API Error")

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception) as exc_info:
                await provider.chat_completions(sample_payload)
            assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_chat_completions_stream_success(self, provider):
        """测试流式响应成功"""
        payload = {"model": "moonshot-v1-8k",
                   "messages": [{"role": "user", "content": "Hello"}]}

        mock_stream_response = MagicMock()
        mock_stream_response.status_code = 200
        mock_stream_response.aiter_lines = MagicMock(return_value=AsyncIteratorMock([
            'data: {"id":"1","choices":[{"delta":{"content":"Hi"}}]}',
            'data: {"id":"1","choices":[{"delta":{"content":" there"}}]}',
            ""
        ]))
        mock_stream_response.__aenter__ = AsyncMock(
            return_value=mock_stream_response)
        mock_stream_response.__aexit__ = AsyncMock(return_value=None)

        # stream() 返回一个异步上下文管理器，所以需要设置为 MagicMock
        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_stream_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            lines = []
            async for line in provider.chat_completions_stream(payload):
                lines.append(line)

        assert len(lines) == 2

    @pytest.mark.asyncio
    async def test_chat_completions_stream_error(self, provider):
        """测试流式响应错误处理"""
        payload = {"model": "moonshot-v1-8k",
                   "messages": [{"role": "user", "content": "Hello"}]}

        mock_stream_response = MagicMock()
        mock_stream_response.status_code = 429
        mock_stream_response.aread = AsyncMock(return_value=b"Rate Limited")
        mock_stream_response.__aenter__ = AsyncMock(
            return_value=mock_stream_response)
        mock_stream_response.__aexit__ = AsyncMock(return_value=None)

        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_stream_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception):
                async for _ in provider.chat_completions_stream(payload):
                    pass

    @pytest.mark.asyncio
    async def test_list_models_success(self, provider):
        """测试获取模型列表成功"""
        sample_models = {
            "object": "list",
            "data": [
                {
                    "id": "moonshot-v1-8k",
                    "object": "model",
                    "created": 1234567890,
                    "owned_by": "moonshot"
                },
                {
                    "id": "moonshot-v1-32k",
                    "object": "model",
                    "created": 1234567891,
                    "owned_by": "moonshot"
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = sample_models
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await provider.list_models()

        assert result == sample_models
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert call_args[0][0] == f"{KIMI_BASE_URL}/models"

    @pytest.mark.asyncio
    async def test_list_models_http_error(self, provider):
        """测试获取模型列表 HTTP 错误"""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API Error")

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception) as exc_info:
                await provider.list_models()
            assert "API Error" in str(exc_info.value)


# =============================================================================
# Utility Function Tests
# =============================================================================


class TestMergeToolContent:
    """测试 merge_tool_content 函数"""

    def test_merge_string_content(self):
        """测试字符串内容保持不变"""
        msg = {"role": "user", "content": "Hello"}
        result = merge_tool_content(msg)
        assert result == msg

    def test_merge_none_content(self):
        """测试 None 内容保持不变"""
        msg = {"role": "user", "content": None}
        result = merge_tool_content(msg)
        assert result == msg

    def test_merge_text_block(self):
        """测试合并文本块"""
        msg = {
            "role": "tool",
            "content": [
                {"type": "text", "text": "Part 1"},
                {"type": "text", "text": "Part 2"}
            ]
        }
        result = merge_tool_content(msg)
        assert result["content"] == "Part 1Part 2"

    def test_merge_image_url_block(self):
        """测试合并图片 URL 块"""
        msg = {
            "role": "tool",
            "content": [
                {"type": "image_url", "image_url": {
                    "url": "http://example.com/img.png"}}
            ]
        }
        result = merge_tool_content(msg)
        assert "[Attached Image: http://example.com/img.png]" in result["content"]

    def test_merge_mixed_blocks(self):
        """测试合并混合类型块"""
        msg = {
            "role": "tool",
            "content": [
                {"type": "text", "text": "Here is the result:"},
                {"type": "image_url", "image_url": {
                    "url": "http://example.com/chart.png"}},
                {"type": "text", "text": "End of result"}
            ]
        }
        result = merge_tool_content(msg)
        assert "Here is the result:" in result["content"]
        assert "[Attached Image: http://example.com/chart.png]" in result["content"]
        assert "End of result" in result["content"]

    def test_merge_string_in_list(self):
        """测试列表中的字符串元素"""
        msg = {
            "role": "tool",
            "content": ["Plain text", {"type": "text", "text": "Structured text"}]
        }
        result = merge_tool_content(msg)
        assert "Plain text" in result["content"]
        assert "Structured text" in result["content"]

    def test_merge_unknown_block_type(self):
        """测试未知块类型"""
        msg = {
            "role": "tool",
            "content": [
                {"type": "unknown_type", "data": "some data"}
            ]
        }
        result = merge_tool_content(msg)
        assert "[Unsupported Multimodal Block: unknown_type]" in result["content"]

    def test_merge_non_dict_item(self):
        """测试非字典元素"""
        msg = {
            "role": "tool",
            "content": [123, {"type": "text", "text": "text"}]
        }
        result = merge_tool_content(msg)
        assert "[Unknown Content Block: 123]" in result["content"]
        assert "text" in result["content"]

    def test_does_not_modify_original(self):
        """测试不修改原始消息"""
        msg = {
            "role": "tool",
            "content": [{"type": "text", "text": "Test"}]
        }
        original_content = msg["content"]
        result = merge_tool_content(msg)
        assert msg["content"] is original_content
        assert result["content"] != original_content


# =============================================================================
# Integration Tests - 真实 API 请求
# =============================================================================

# 检查是否有真实的 API Key（不是默认值）
HAS_REAL_DEEPSEEK_KEY = DEEPSEEK_API_KEY != "test-api-key"
HAS_REAL_KIMI_KEY = KIMI_API_KEY != "test-kimi-key"


class TestDeepSeekProviderIntegration:
    """DeepSeek 真实 API 集成测试"""

    @pytest.fixture
    def provider(self):
        """创建真实的 provider 实例"""
        return DeepSeekProvider(
            base_url=DEEPSEEK_BASE_URL,
            api_key=DEEPSEEK_API_KEY
        )

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_REAL_DEEPSEEK_KEY, reason="没有配置真实的 DEEPSEEK_API_KEY")
    async def test_chat_completions_real(self, provider):
        """测试真实的 chat_completions 调用（打印响应）"""
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": "你好，请用一句话介绍自己"}
            ],
            "stream": False
        }

        print("\n" + "=" * 60)
        print("发送请求到 DeepSeek API...")
        print(f"URL: {DEEPSEEK_BASE_URL}/chat/completions")
        print(f"Model: {payload['model']}")
        print(f"Messages: {payload['messages']}")
        print("=" * 60)

        result = await provider.chat_completions(payload)

        print("\n【DeepSeek 响应】")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("=" * 60)

        # 验证响应结构
        assert "id" in result
        assert "choices" in result
        assert len(result["choices"]) > 0
        assert "message" in result["choices"][0]
        assert "content" in result["choices"][0]["message"]
        print(f"✅ 响应内容: {result['choices'][0]['message']['content'][:50]}...")

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_REAL_DEEPSEEK_KEY, reason="没有配置真实的 DEEPSEEK_API_KEY")
    async def test_chat_completions_stream_real(self, provider):
        """测试真实的流式响应（打印响应）"""
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": "你好"}
            ],
            "stream": True
        }

        print("\n" + "=" * 60)
        print("发送流式请求到 DeepSeek API...")
        print("=" * 60)

        chunks = []
        async for line in provider.chat_completions_stream(payload):
            if line.startswith("data: ") and line != "data: [DONE]":
                chunks.append(line)
                print(f"  📦 {line}...")

        print("=" * 60)
        print(f"✅ 共收到 {len(chunks)} 个数据块")
        assert len(chunks) > 0

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_REAL_DEEPSEEK_KEY, reason="没有配置真实的 DEEPSEEK_API_KEY")
    async def test_list_models_real(self, provider):
        """测试真实的获取模型列表（打印响应）"""
        print("\n" + "=" * 60)
        print("发送请求到 DeepSeek API 获取模型列表...")
        print(f"URL: {DEEPSEEK_BASE_URL}/models")
        print("=" * 60)

        result = await provider.list_models()

        print("\n【DeepSeek 模型列表】")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("=" * 60)

        # 验证响应结构
        assert "object" in result
        assert result["object"] == "list"
        assert "data" in result
        assert len(result["data"]) > 0
        print(f"✅ 共获取到 {len(result['data'])} 个模型")


class TestKimiProviderIntegration:
    """Kimi 真实 API 集成测试"""

    @pytest.fixture
    def provider(self):
        """创建真实的 provider 实例"""
        return KimiProvider(
            base_url=KIMI_BASE_URL,
            api_key=KIMI_API_KEY
        )

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_REAL_KIMI_KEY, reason="没有配置真实的 KIMI_API_KEY")
    async def test_chat_completions_real(self, provider):
        """测试真实的 chat_completions 调用（打印响应）"""
        payload = {
            "model": "moonshot-v1-8k",
            "messages": [
                {"role": "user", "content": "你好，请用一句话介绍自己"}
            ],
            "stream": False
        }

        print("\n" + "=" * 60)
        print("发送请求到 Kimi API...")
        print(f"URL: {KIMI_BASE_URL}/chat/completions")
        print(f"Model: {payload['model']}")
        print(f"Messages: {payload['messages']}")
        print("=" * 60)

        result = await provider.chat_completions(payload)

        print("\n【Kimi 响应】")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("=" * 60)

        # 验证响应结构
        assert "id" in result
        assert "choices" in result
        assert len(result["choices"]) > 0
        assert "message" in result["choices"][0]
        assert "content" in result["choices"][0]["message"]
        print(f"✅ 响应内容: {result['choices'][0]['message']['content'][:50]}...")

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_REAL_KIMI_KEY, reason="没有配置真实的 KIMI_API_KEY")
    async def test_chat_completions_stream_real(self, provider):
        """测试真实的流式响应（打印响应）"""
        payload = {
            "model": "kimi-k2.5",
            "messages": [
                {"role": "user", "content": "你好"}
            ],
            "stream": True
        }

        print("\n" + "=" * 60)
        print("发送流式请求到 Kimi API...")
        print("=" * 60)

        chunks = []
        async for line in provider.chat_completions_stream(payload):
            if line.startswith("data: ") and line != "data: [DONE]":
                chunks.append(line)
                print(f"  📦 {line}...")

        print("=" * 60)
        print(f"✅ 共收到 {len(chunks)} 个数据块")
        assert len(chunks) > 0

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_REAL_KIMI_KEY, reason="没有配置真实的 KIMI_API_KEY")
    async def test_list_models_real(self, provider):
        """测试真实的获取模型列表（打印响应）"""
        print("\n" + "=" * 60)
        print("发送请求到 Kimi API 获取模型列表...")
        print(f"URL: {KIMI_BASE_URL}/models")
        print("=" * 60)

        result = await provider.list_models()

        print("\n【Kimi 模型列表】")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("=" * 60)

        # 验证响应结构
        assert "object" in result
        assert result["object"] == "list"
        assert "data" in result
        assert len(result["data"]) > 0
        print(f"✅ 共获取到 {len(result['data'])} 个模型")


# =============================================================================
# Helper Classes
# =============================================================================


class AsyncIteratorMock:
    """用于 mock 异步迭代的辅助类"""

    def __init__(self, items):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item
