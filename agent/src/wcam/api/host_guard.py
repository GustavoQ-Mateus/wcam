from collections.abc import Iterable

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from wcam.api.errors import error_response


class HostGuard:
    def __init__(self, app: ASGIApp, allowed_hosts: Iterable[str]) -> None:
        self._app = app
        self._allowed_hosts = frozenset(host.lower() for host in allowed_hosts)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or Headers(scope=scope).get("host", "").lower() in self._allowed_hosts:
            await self._app(scope, receive, send)
            return
        response = error_response(400, "invalid_host", "The Host header is not allowed.")
        await response(scope, receive, send)
