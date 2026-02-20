import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, ORJSONResponse, StreamingResponse

from src.pipeline import BasePipeline, CursorPipeline
from src.storage import apikey_storage

logger = logging.getLogger(__name__)
router = APIRouter()

# 模型列表缓存 (TTL: 5分钟)
_models_cache = {"data": None, "expires_at": 0}
_cache_lock = asyncio.Lock()
CACHE_TTL_SECONDS = 300  # 5分钟缓存


async def _get_cached_models():
    """获取缓存的模型列表"""
    async with _cache_lock:
        if (
            _models_cache["data"] is not None
            and time.time() < _models_cache["expires_at"]
        ):
            return _models_cache["data"]
    return None


async def _set_cached_models(data):
    """设置模型列表缓存"""
    async with _cache_lock:
        _models_cache["data"] = data
        _models_cache["expires_at"] = time.time() + CACHE_TTL_SECONDS


def generate_chat_id(body: dict) -> str:
    messages = body.get("messages", [])
    tools = body.get("tools", [])
    first_user_idx = -1
    for i, msg in enumerate(messages):
        if msg.get("role") == "assistant":
            first_user_idx = i - 1
            break

    if first_user_idx >= 0:
        truncated_messages = messages[: first_user_idx + 1]
    else:
        truncated_messages = messages
    serialized = json.dumps(
        {"tools": tools, "messages": truncated_messages},
        ensure_ascii=False,
        sort_keys=True,
    )
    hash_value = hashlib.sha256(serialized.encode()).hexdigest()
    return hash_value[:16]


def save_request(chat_id: str, payload: dict):
    file_path = Path("requests") / f"{chat_id}.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=4, sort_keys=True)
    print(f"Request saved to {file_path}")


@router.get("/models")
async def list_models(req: Request):
    """获取所有可用模型列表，聚合所有 provider 的 models

    Returns:
        OpenAI 格式的模型列表，data.id 带有 provider/ 前缀
    """
    authorization = req.headers.get("Authorization")
    if not authorization:
        logger.debug("Missing Authorization header")
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    api_key = authorization.replace("Bearer ", "")
    logger.debug(f"API Key: {api_key[:10]}...")

    query_result = await apikey_storage.get_api_key(api_key)
    logger.debug(f"Query result: {query_result}")

    if not query_result:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    # 检查缓存
    cached = await _get_cached_models()
    if cached is not None:
        return JSONResponse(content=cached)

    # 从 providers 获取模型列表
    all_models = []
    providers = req.app.state.providers

    for provider_name, provider in providers.items():
        try:
            models_data = await provider.list_models()
            if models_data and "data" in models_data:
                for model in models_data["data"]:
                    # 数据清洗：按照 OpenAI 最小可用格式
                    model_id = model.get("id", "")
                    if not model_id:
                        continue
                    cleaned_model = {
                        "id": f"{provider_name}/{model_id}",
                        "object": "model",
                        "created": model.get("created", 0),
                        "owned_by": model.get("owned_by", provider_name),
                    }
                    all_models.append(cleaned_model)
        except Exception as e:
            # 如果某个 provider 获取失败，跳过并继续
            print(f"Failed to get models from {provider_name}: {e}")
            continue

    result = {"object": "list", "data": all_models}

    # 更新缓存
    await _set_cached_models(result)

    return JSONResponse(content=result)


@router.get("/ping")
async def ping():
    """纯速度测试接口 - 无任何业务逻辑，仅返回 OK

    用于测试理论最大吞吐量，排除数据库、Provider 调用等开销
    """
    return ORJSONResponse(content={"status": "OK"})


@router.post("/ping")
async def ping_post():
    """纯速度测试接口 (POST 版本) - 无任何业务逻辑，仅返回 OK

    用于测试理论最大吞吐量，排除数据库、Provider 调用等开销
    """
    return ORJSONResponse(content={"status": "OK"})


@router.post("/chat/completions")
async def chat_completions(req: Request):
    try:
        body = await req.json()
    except:
        return JSONResponse(status_code=400, content={"error": "Invalid Body"})

    authorization = req.headers.get("Authorization")
    if not authorization:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    api_key = authorization.replace("Bearer ", "")
    query_result = await apikey_storage.get_api_key(api_key)
    if not query_result:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    model = body.get("model")
    provider_name = model.split("/")[0]
    real_model_name = model.split("/")[1]
    provider = req.app.state.providers.get(provider_name)
    if not provider:
        return JSONResponse(status_code=404, content={"error": "Model not found"})

    purpose = query_result.get("purpose", "default")
    if purpose == "cursor":
        pipeline = CursorPipeline()
    else:
        pipeline = BasePipeline()
    # pipeline = BasePipeline()
    chat_id = generate_chat_id(body)
    # save_request(chat_id, body)
    ctx = {
        "chat_id": chat_id,
        "model_name": model,
        "chat_history": [],
    }
    body["model"] = real_model_name
    payload = pipeline.preprocess_request(ctx, body)
    ctx["chat_history"] = payload.get("messages", [])
    stream = bool(body.get("stream", False))
    if not stream:
        data = await provider.chat_completions(payload)
        data = pipeline.postprocess_response(ctx, data)
        return JSONResponse(content=data)
    else:

        async def stream_generator():
            raw_iter = provider.chat_completions_stream(payload)
            async for line in pipeline.rewrite_sse_lines(ctx, raw_iter):
                yield line.encode() + "\n\n".encode()

        return StreamingResponse(stream_generator(), media_type="text/event-stream")
