from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from wcam import __version__

type Surface = Literal["console", "phone"]


class Health(BaseModel):
    status: Literal["ok"]
    version: str
    surface: Surface


def create_health_router(surface: Surface) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get(
        "/health",
        summary="Agent health",
        description="Reports that the agent is running, its version and which server answered.",
    )
    async def health() -> Health:
        return Health(status="ok", version=__version__, surface=surface)

    return router
