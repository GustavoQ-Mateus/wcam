from fastapi import APIRouter, Request, Response, status

from wcam.api.comparison_schemas import ComparisonCreatedResponse, ComparisonResponse, comparison_response
from wcam.sessions.comparisons import ComparisonNotFoundError, ComparisonStore
from wcam.sessions.manager import SessionManager

PNG_MEDIA_TYPE = "image/png"


def create_dev_router(manager: SessionManager, comparisons: ComparisonStore) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/api/dev/comparisons",
        status_code=status.HTTP_201_CREATED,
        summary="Start a side by side comparison",
        description="Development only. Asks the live phone for the frame it is showing; the console then uploads "
        "the frame it reads from the WCam camera. Keeps the last five comparisons in memory.",
    )
    async def start_comparison() -> ComparisonCreatedResponse:
        return ComparisonCreatedResponse(id=manager.start_comparison())

    @router.put(
        "/api/dev/comparisons/{comparison_id}/pc",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Upload the PC frame of a comparison",
        description="Development only. PNG of the frame read from the WCam camera in the PC browser, up to 20 MB.",
    )
    async def upload_pc(comparison_id: str, request: Request) -> Response:
        await comparisons.receive_pc(comparison_id, await request.body())
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.put(
        "/api/dev/comparisons/{comparison_id}/screen",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Upload a phone screenshot for a comparison",
        description="Development only. PNG screenshot of the phone screen, with its ICC profile, up to 20 MB. "
        "Accepted only once the comparison is ready.",
    )
    async def upload_screen(comparison_id: str, request: Request) -> Response:
        await comparisons.receive_screen(comparison_id, await request.body())
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get(
        "/api/dev/comparisons/{comparison_id}",
        summary="Read a comparison",
        description="Development only. Capture times, the color correction in use and the color difference "
        "between the phone frame, the PC frame and, when uploaded, the phone screenshot.",
    )
    async def read_comparison(comparison_id: str) -> ComparisonResponse:
        return comparison_response(comparisons.find(comparison_id))

    @router.get(
        "/api/dev/comparisons/{comparison_id}/phone.png",
        summary="Download the phone frame of a comparison",
        description="Development only. The frame the phone viewfinder was showing, as the phone sent it.",
    )
    async def phone_image(comparison_id: str) -> Response:
        phone = comparisons.find(comparison_id).phone
        if phone is None:
            raise ComparisonNotFoundError
        return Response(content=phone.png, media_type=PNG_MEDIA_TYPE)

    @router.get(
        "/api/dev/comparisons/{comparison_id}/screen.png",
        summary="Download the phone screenshot of a comparison",
        description="Development only. The screenshot uploaded for the comparison, unchanged.",
    )
    async def screen_image(comparison_id: str) -> Response:
        screen = comparisons.find(comparison_id).screen
        if screen is None:
            raise ComparisonNotFoundError
        return Response(content=screen.png, media_type=PNG_MEDIA_TYPE)

    return router
