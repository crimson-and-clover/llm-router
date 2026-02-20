import logging
from copy import copy, deepcopy
from typing import Any, AsyncIterator, Dict

import httpx

from .base import BaseProvider

logger = logging.getLogger(__name__)


def merge_tool_content(msg: dict) -> dict:
    content = msg.get("content")

    if content is None or isinstance(content, str):
        return msg
    new_msg = deepcopy(msg)
    text_parts = []
    for item in content:
        if isinstance(item, str):
            text_parts.append(item)
            continue
        if not isinstance(item, dict):
            text_parts.append(f"\n[Unknown Content Block: {item}]\n")
            continue
        block_type = item.get("type")
        if block_type == "text":
            text_parts.append(item.get("text", ""))
        elif block_type == "image_url":
            url = item.get("image_url", {}).get("url", "")
            text_parts.append(f"\n[Attached Image: {url}]\n")
        else:
            text_parts.append(f"\n[Unsupported Multimodal Block: {block_type}]\n")
    new_msg["content"] = "".join(text_parts)
    return new_msg


class DeepSeekProvider(BaseProvider):
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, br",
        }

    def preprocess_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        new_payload = copy(payload)
        msg_list = new_payload.get("messages", [])
        new_msg_list = copy(msg_list)
        for idx in range(len(new_msg_list)):
            msg = new_msg_list[idx]
            if msg.get("role") == "tool":
                new_msg = merge_tool_content(msg)
                new_msg_list[idx] = new_msg

        new_payload["messages"] = new_msg_list
        return new_payload

    async def chat_completions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        new_payload = self.preprocess_payload(payload)
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{self.base_url}/chat/completions",
                json=new_payload,
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def chat_completions_stream(
        self, payload: Dict[str, Any]
    ) -> AsyncIterator[str]:
        new_payload = self.preprocess_payload(payload)
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=new_payload,
                headers=self._headers(),
            ) as r:
                if r.status_code != 200:
                    text = await r.aread()
                    text = text.decode()
                    logger.error(f"Kimi API Error: {r.status_code} {text}")
                    # save_request("error_request", payload)
                    r.raise_for_status()
                async for line in r.aiter_lines():
                    if len(line) == 0:
                        continue
                    yield line

    async def list_models(self) -> Dict[str, Any]:
        """获取 DeepSeek 模型列表"""
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{self.base_url}/models", headers=self._headers())
            r.raise_for_status()
            return r.json()
