from ipaddress import IPv4Network

from starlette.types import ASGIApp, Receive, Scope, Send

from wcam.api.errors import error_response
from wcam.network.lan import is_in_network


class SubnetGuard:
    def __init__(self, app: ASGIApp, network: IPv4Network) -> None:
        self._app = app
        self._network = network

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        client = scope.get("client")
        if scope["type"] != "http" or (client is not None and is_in_network(client[0], self._network)):
            await self._app(scope, receive, send)
            return
        response = error_response(403, "not_same_network", "The request does not come from the local network.")
        await response(scope, receive, send)
