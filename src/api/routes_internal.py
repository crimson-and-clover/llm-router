"""Internal API Routes

内部 API 路由聚合器，所有内部路由通过 api/internal/ 目录下的模块组织。
"""

from fastapi import APIRouter

from src.api.internal import router as internal_router

router = APIRouter()

# 聚合所有内部路由
router.include_router(internal_router)
