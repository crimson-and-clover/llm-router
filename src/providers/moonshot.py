import logging
from typing import Any, AsyncIterator, Dict

import httpx

from .base import BaseProvider

logger = logging.getLogger(__name__)


def save_request(chat_id: str, payload: dict):
    import json
    from pathlib import Path

    file_path = Path("requests") / f"{chat_id}.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=4, sort_keys=True)
    print(f"Request saved to {file_path}")


class MoonshotProvider(BaseProvider):
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, br",
        }

    async def chat_completions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def chat_completions_stream(
        self, payload: Dict[str, Any]
    ) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
            ) as r:
                if r.status_code != 200:
                    text = await r.aread()
                    text = text.decode()
                    logger.error(f"Moonshot API Error: {r.status_code} {text}")
                    # save_request("error_request", payload)
                    r.raise_for_status()
                async for line in r.aiter_lines():
                    if len(line) == 0:
                        continue
                    yield line

    async def list_models(self) -> Dict[str, Any]:
        """获取 Moonshot 模型列表"""
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{self.base_url}/models", headers=self._headers())
            r.raise_for_status()
            return r.json()
