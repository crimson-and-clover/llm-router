import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import platform

from fastapi import FastAPI

from src.api.routes_chat import router as chat_router
from src.api.routes_internal import router as internal_router
from src.core.logging import (
    reconfigure_hypercorn_logging,
    reconfigure_uvicorn_logging,
    setup_logging,
    stop_logging,
)
from src.core.settings import get_settings
from src.providers import DeepSeekProvider, MoonshotProvider, TestProvider, ZaiProvider
from src.storage import apikey_storage, user_storage

# uvloop 在 Windows 上不可用，只在非 Windows 平台使用
if platform.system() != "Windows":
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    await user_storage.init_db()
    await apikey_storage.init_db()

    # Uvicorn/Hypercorn 启动后重新配置日志（防止覆盖配置）
    settings = get_settings()
    reconfigure_uvicorn_logging(log_access=settings.log_access)
    reconfigure_hypercorn_logging(log_access=settings.log_access)

    yield
    # 关闭时停止日志监听器
    stop_logging()


def create_app():
    settings = get_settings()
    # 初始化日志系统，传入完整配置
    setup_logging(
        debug=settings.debug,
        log_level=settings.log_level,
        log_async=settings.log_async,
        log_format=settings.log_format,
        log_access=settings.log_access,
    )

    app = FastAPI(lifespan=lifespan)

    # 初始化模型提供商
    app.state.providers = {
        "moonshot": MoonshotProvider(
            settings.moonshot_base_url, settings.moonshot_api_key
        ),
        "deepseek": DeepSeekProvider(
            settings.deepseek_base_url, settings.deepseek_api_key
        ),
        "zai": ZaiProvider(settings.zai_base_url, settings.zai_api_key),
        "test": TestProvider(),
    }

    # 注册路由
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(internal_router, prefix="/internal")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    from src.core.settings import get_settings

    settings = get_settings()

    # 根据配置决定是否启用访问日志
    access_log = settings.log_access
    log_level = settings.log_level.lower() if settings.log_level else "info"

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=12000,
        access_log=access_log,  # 控制访问日志
        log_level=log_level,  # 统一日志级别
    )
