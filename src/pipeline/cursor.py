import asyncio
import json
import logging
from copy import copy, deepcopy
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List

from .base import BasePipeline, SSEDecoder

logger = logging.getLogger(__name__)


class CursorPipeline(BasePipeline):
    decoder = SSEDecoder()
    think_bos = "<think>\n"
    think_eos = "\n</think>"

    reasoning_flag = False

    def _extract_think_and_answer(self, text: str) -> str:
        if self.think_bos in text and self.think_eos in text:
            think_text = text.split(self.think_bos)[1].split(self.think_eos)[0]
            new_text = text.replace(self.think_bos + think_text + self.think_eos, "")
            return think_text, new_text
        return None, text

    def preprocess_request(
        self,
        ctx: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        new_payload = copy(payload)
        msg_list = new_payload.get("messages", [])
        new_msg_list = copy(msg_list)
        for i, msg in enumerate(new_msg_list):
            if msg.get("role") == "assistant":
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "ChatID: %s | Content: %s", ctx.get("chat_id"), msg["content"]
                    )
                new_msg = deepcopy(msg)
                think_text, answer_text = self._extract_think_and_answer(
                    msg["content"][0]["text"]
                )
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "ChatID: %s | Think Text: %s | Answer Text: %s",
                        ctx.get("chat_id"),
                        think_text,
                        answer_text,
                    )
                new_msg["reasoning_content"] = think_text
                if len(answer_text) > 0:
                    new_msg["content"] = [{"type": "text", "text": answer_text}]
                else:
                    new_msg["content"] = []
                new_msg_list[i] = new_msg
        new_payload["messages"] = new_msg_list
        return new_payload

    def postprocess_response(
        self, ctx: Dict[str, Any], raw: Dict[str, Any]
    ) -> Dict[str, Any]:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("ChatID: %s | Raw: %s", ctx.get("chat_id"), raw)

        # 处理非流式响应中的 reasoning_content
        choices = raw.get("choices", [])
        if not choices:
            return raw

        choice = choices[0]
        message = choice.get("message", {})
        reasoning_content = message.get("reasoning_content")

        if reasoning_content:
            # 将 reasoning_content 包装成 <think> 标签并前置到 content
            content = message.get("content", "")
            new_content = (
                f"{self.think_bos}{reasoning_content}{self.think_eos}{content}"
            )
            message["content"] = new_content
            # 移除 reasoning_content 字段（Cursor 期望内容在 content 中）
            del message["reasoning_content"]

        return raw

    def _update_final_message(
        self, final_message: Dict[str, Any], data: Dict[str, Any]
    ):
        choices = data.get("choices", [])
        if not choices:
            return
        choice = choices[0]
        delta = choice.get("delta", {})
        if "role" in delta:
            final_message["role"] = delta["role"]
        if "content" in delta:
            content_list = final_message.get("content", [{"type": "text", "text": ""}])
            content_list[0]["text"] += delta["content"]
            final_message["content"] = content_list
        if "reasoning_content" in delta:
            reasoning = final_message.get("reasoning_content", "")
            reasoning += delta["reasoning_content"]
            final_message["reasoning_content"] = reasoning
        if "tool_calls" in delta:
            tool_calls_list = final_message.get("tool_calls", [])
            for tc_delta in delta["tool_calls"]:
                idx = tc_delta.get("index")
                while len(tool_calls_list) <= idx:
                    tool_calls_list.append(
                        {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    )

                target_tc = tool_calls_list[idx]
                if "id" in tc_delta:
                    target_tc["id"] += tc_delta["id"]
                if "function" in tc_delta:
                    f = tc_delta["function"]
                    if "name" in f:
                        target_tc["function"]["name"] += f["name"]
                    if "arguments" in f:
                        target_tc["function"]["arguments"] += f["arguments"]
            final_message["tool_calls"] = tool_calls_list

    def _update_usage(self, usage: Dict[str, Any], data: Dict[str, Any]):
        if "usage" in data and data["usage"]:
            usage["prompt_tokens"] = data["usage"].get("prompt_tokens", 0)
            usage["completion_tokens"] = data["usage"].get("completion_tokens", 0)
            usage["total_tokens"] = data["usage"].get("total_tokens", 0)
            usage["cached_tokens"] = data["usage"].get("cached_tokens", 0)

    def _rewrite_sse_data(
        self, ctx: Dict[str, Any], data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        rewrite_data = []
        model_name = ctx.get("model_name")
        data["model"] = model_name
        choices = data.get("choices", [])
        if not choices:
            return [data]
        choice = choices[0]
        delta = choice.get("delta", {})
        if not self.reasoning_flag and "reasoning_content" in delta:
            new_data = deepcopy(data)
            new_data["choices"][0]["delta"] = {"content": self.think_bos}
            rewrite_data.append(new_data)
            new_data = deepcopy(data)
            new_data["choices"][0]["delta"] = {"content": delta["reasoning_content"]}
            rewrite_data.append(new_data)
            self.reasoning_flag = True
        elif self.reasoning_flag and "reasoning_content" in delta:
            new_data = deepcopy(data)
            new_data["choices"][0]["delta"] = {"content": delta["reasoning_content"]}
            rewrite_data.append(new_data)
        elif self.reasoning_flag and "reasoning_content" not in delta:
            new_data = deepcopy(data)
            new_data["choices"][0]["delta"] = {"content": self.think_eos}
            rewrite_data.append(new_data)
            rewrite_data.append(data)
            self.reasoning_flag = False
        else:
            rewrite_data.append(data)

        return rewrite_data

    def _sync_save_chat_history(self, chat_id: str, chat_history: List[Dict[str, Any]]):
        """同步保存聊天历史到文件（在线程池中执行）"""
        path = Path("chat_history") / f"{chat_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(chat_history, f, ensure_ascii=False, indent=4, sort_keys=True)

    async def _async_save_chat_history(
        self, chat_id: str, chat_history: List[Dict[str, Any]]
    ):
        """异步保存聊天历史（在线程池中执行，带错误处理）"""
        try:
            await asyncio.to_thread(self._sync_save_chat_history, chat_id, chat_history)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("ChatID: %s | Chat history saved successfully", chat_id)
        except Exception as e:
            logger.error("ChatID: %s | Failed to save chat history: %s", chat_id, e)

    def _save_chat_history(self, chat_id: str, chat_history: List[Dict[str, Any]]):
        """异步保存聊天历史（fire-and-forget，不阻塞响应）"""
        asyncio.create_task(self._async_save_chat_history(chat_id, chat_history))

    async def rewrite_sse_lines(
        self, ctx: Dict[str, Any], raw_lines: AsyncIterator[str]
    ) -> AsyncIterator[str]:
        self.reasoning_flag = False
        chat_id = ctx.get("chat_id")
        chat_history = ctx.get("chat_history", [])
        final_message = {}
        usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cached_tokens": 0,
        }
        async for line in raw_lines:
            line = line.strip()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("ChatID: %s | Raw Line: %s", chat_id, line)
            data = self.decoder.decode(line)
            if data:
                self._update_final_message(final_message, data)
                self._update_usage(usage, data)
                rewrite_data = self._rewrite_sse_data(ctx, data)
                for new_data in rewrite_data:
                    new_line = f"data: {json.dumps(new_data, ensure_ascii=False)}"
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            "ChatID: %s | Rewritten Line: %s", chat_id, new_line
                        )
                    yield new_line
            else:
                yield line
        chat_history.append(final_message)
        cache_hit = usage["cached_tokens"]
        cache_miss = usage["total_tokens"] - cache_hit
        completion = usage["completion_tokens"]
        logger.info(
            "ChatID: %s | Cache Hit: %d | Cache Miss: %d | Completion: %d",
            chat_id,
            cache_hit,
            cache_miss,
            completion,
        )
        self._save_chat_history(chat_id, chat_history)
