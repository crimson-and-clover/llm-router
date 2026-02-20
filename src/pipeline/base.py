import json
import logging
from typing import Any, AsyncIterator, Dict

logger = logging.getLogger(__name__)


class BasePipeline:
    def preprocess_request(
        self,
        ctx: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "ChatID: %s | Preprocess Request: %s", ctx.get("chat_id"), payload
            )
        return payload

    def postprocess_response(
        self, ctx: Dict[str, Any], raw: Dict[str, Any]
    ) -> Dict[str, Any]:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "ChatID: %s | Postprocess Response: %s", ctx.get("chat_id"), raw
            )
        return raw

    async def rewrite_sse_lines(
        self, ctx: Dict[str, Any], raw_lines: AsyncIterator[str]
    ) -> AsyncIterator[str]:
        async for line in raw_lines:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "ChatID: %s | Rewrite SSE Line: %s", ctx.get("chat_id"), line
                )
            yield line


class SSEDecoder:
    def __init__(self):
        self.buffer = ""

    def decode(self, line: str) -> Dict[str, Any]:
        line = line.strip()
        if not line or not line.startswith("data: "):
            return None
        data_content = line[len("data: ") :]
        if data_content == "[DONE]":
            return None
        data = json.loads(data_content)
        return data
