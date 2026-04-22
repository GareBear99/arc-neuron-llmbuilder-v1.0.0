from __future__ import annotations

from fastapi import APIRouter

from arc_lang.api.routers import acquisition_router, core_router, knowledge_router, runtime_router

router = APIRouter()
router.include_router(core_router)
router.include_router(runtime_router)
router.include_router(knowledge_router)
router.include_router(acquisition_router)
