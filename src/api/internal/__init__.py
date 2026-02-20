from fastapi import APIRouter

from .admin import router as admin_router
from .auth import router as auth_router
from .keys import router as keys_router
from .usage import router as usage_router
from .users import router as users_router
from .worker import router as worker_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(users_router, prefix="/users", tags=["Users"])
router.include_router(keys_router, prefix="/users/me/keys", tags=["Keys"])
router.include_router(admin_router, prefix="/admin", tags=["Admin"])
router.include_router(worker_router, prefix="/keys", tags=["Worker"])
router.include_router(usage_router, prefix="/usage", tags=["Usage"])
