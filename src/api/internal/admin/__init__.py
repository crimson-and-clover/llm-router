from fastapi import APIRouter

from .keys import router as keys_router
from .users import router as users_router

router = APIRouter()

router.include_router(users_router, prefix="/users")
router.include_router(keys_router, prefix="/users")
