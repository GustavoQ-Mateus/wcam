from pathlib import Path

import httpx
from fastapi import HTTPException

from tests.conftest import LAN, console_app, console_client, phone_app, phone_client, services
from wcam import __version__
from wcam.app import create_servers
from wcam.config import Settings
from wcam.network.certificates import load_or_create_certificate


async def test_console_health_reports_console_surface(settings: Settings) -> None:
    async with console_client(console_app(settings)) as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__, "surface": "console"}


async def test_phone_health_reports_phone_surface(settings: Settings) -> None:
    async with phone_client(phone_app(settings)) as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["surface"] == "phone"


async def test_request_from_same_subnet_is_accepted(settings: Settings) -> None:
    async with phone_client(phone_app(settings), client_ip="192.168.0.200") as client:
        response = await client.get("/cam")

    assert response.status_code == 200


async def test_request_from_other_subnet_is_rejected_with_not_same_network(settings: Settings) -> None:
    async with phone_client(phone_app(settings), client_ip="10.8.0.4") as client:
        response = await client.get("/cam")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_same_network"


async def test_unknown_host_header_is_rejected_with_invalid_host(settings: Settings) -> None:
    async with console_client(console_app(settings)) as client:
        response = await client.get("/api/health", headers={"Host": "attacker.example:8080"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_host"


async def test_extra_allowed_host_is_accepted(tmp_path: Path, web_dist: Path) -> None:
    settings = Settings(data_dir=tmp_path, web_dist=web_dist, extra_allowed_hosts=["agent:8080"])

    async with console_client(console_app(settings)) as client:
        response = await client.get("/api/health", headers={"Host": "agent:8080"})

    assert response.status_code == 200


async def test_phone_server_does_not_serve_console_page(settings: Settings) -> None:
    async with phone_client(phone_app(settings)) as client:
        response = await client.get("/")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_console_server_serves_the_developer_page(settings: Settings) -> None:
    async with console_client(console_app(settings)) as client:
        page = await client.get("/dev")
        root = await client.get("/")

    assert page.status_code == 200
    assert page.text == root.text


async def test_phone_server_does_not_serve_the_developer_page(settings: Settings) -> None:
    async with phone_client(phone_app(settings)) as client:
        response = await client.get("/dev")

    assert response.status_code == 404


async def test_console_server_does_not_serve_phone_page(settings: Settings) -> None:
    async with console_client(console_app(settings)) as client:
        response = await client.get("/cam")

    assert response.status_code == 404


async def test_missing_web_build_returns_web_not_built(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, web_dist=tmp_path / "missing")

    async with console_client(console_app(settings)) as client:
        response = await client.get("/")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "web_not_built"


async def test_unhandled_error_returns_internal_error_without_details(settings: Settings) -> None:
    app = console_app(settings)

    @app.get("/api/explode")
    async def explode() -> None:
        raise RuntimeError("secret detail")

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8080") as client:
        response = await client.get("/api/explode")

    assert response.status_code == 500
    assert response.json() == {"error": {"code": "internal_error", "message": "Something went wrong in the agent."}}
    assert "secret" not in response.text


def test_servers_ignore_forwarded_client_address(settings: Settings) -> None:
    certificate = load_or_create_certificate(settings.data_dir, LAN.ip)

    servers = create_servers(settings, LAN, certificate, services())

    assert [server.config.proxy_headers for server in servers] == [False, False]


async def test_client_error_outside_table_returns_invalid_request(settings: Settings) -> None:
    response = await request_route_raising(settings, 418)

    assert response.status_code == 418
    assert response.json()["error"]["code"] == "invalid_request"


async def test_server_error_outside_table_returns_internal_error(settings: Settings) -> None:
    response = await request_route_raising(settings, 502)

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "internal_error"


async def request_route_raising(settings: Settings, status_code: int) -> httpx.Response:
    app = console_app(settings)

    @app.get("/api/fail")
    async def fail() -> None:
        raise HTTPException(status_code)

    async with console_client(app) as client:
        return await client.get("/api/fail")
