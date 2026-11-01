from fastapi import APIRouter

from wcam.api.health import create_health_router


def create_phone_router() -> APIRouter:
    router = APIRouter()
    router.include_router(create_health_router("phone"))
    return router
