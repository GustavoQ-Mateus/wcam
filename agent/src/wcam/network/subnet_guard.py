from ipaddress import IPv4Network, IPv6Address, ip_address

from starlette.types import ASGIApp, Receive, Scope, Send

from wcam.api.errors import error_response


class SubnetGuard:
    def __init__(self, app: ASGIApp, network: IPv4Network) -> None:
        self._app = app
        self._network = network

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or self._is_inside(scope.get("client")):
            await self._app(scope, receive, send)
            return
        response = error_response(403, "not_same_network", "The request does not come from the local network.")
        await response(scope, receive, send)

    def _is_inside(self, client: tuple[str, int] | None) -> bool:
        if client is None:
            return False
        try:
            address = ip_address(client[0])
        except ValueError:
            return False
        if isinstance(address, IPv6Address):
            mapped = address.ipv4_mapped
            return mapped is not None and mapped in self._network
        return address in self._network
