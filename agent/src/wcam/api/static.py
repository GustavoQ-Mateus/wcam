from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from wcam.api.errors import error_response

INDEX_FILE = "index.html"
ASSETS_FOLDER = "assets"


def mount_web(app: FastAPI, web_dist: Path, page_paths: tuple[str, ...]) -> None:
    index = web_dist / INDEX_FILE

    async def page() -> Response:
        if not index.is_file():
            return error_response(503, "web_not_built", "The web interface has not been built.")
        return FileResponse(index)

    for path in page_paths:
        app.add_api_route(path, page, methods=["GET"], include_in_schema=False)
    app.mount(f"/{ASSETS_FOLDER}", StaticFiles(directory=web_dist / ASSETS_FOLDER, check_dir=False))
