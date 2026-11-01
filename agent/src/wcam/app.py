import asyncio
import contextlib
import signal
from collections.abc import Generator, Sequence
from types import FrameType

import uvicorn
from fastapi import FastAPI

from wcam import __version__
from wcam.api.console_routes import create_console_router
from wcam.api.errors import install_error_handlers
from wcam.api.host_guard import HostGuard
from wcam.api.phone_routes import create_phone_router
from wcam.api.static import mount_web
from wcam.api.subnet_guard import SubnetGuard
from wcam.config import Settings
from wcam.network.certificates import TlsCertificate
from wcam.network.lan import LanInterface

CONSOLE_PAGES = ("/",)
PHONE_PAGES = ("/cam",)
STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM)
SERVER_LOG_LEVEL = "warning"


class SupervisedServer(uvicorn.Server):
    @contextlib.contextmanager
    def capture_signals(self) -> Generator[None]:
        yield


def console_allowed_hosts(settings: Settings) -> list[str]:
    port = settings.console_port
    return [f"127.0.0.1:{port}", f"localhost:{port}", *settings.extra_allowed_hosts]


def phone_allowed_hosts(settings: Settings, lan: LanInterface) -> list[str]:
    return [f"{lan.ip}:{settings.phone_port}", *settings.extra_allowed_hosts]


def create_console_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="WCam console", version=__version__)
    install_error_handlers(app)
    app.include_router(create_console_router())
    mount_web(app, settings.web_dist, CONSOLE_PAGES)
    app.add_middleware(HostGuard, allowed_hosts=console_allowed_hosts(settings))
    return app


def create_phone_app(settings: Settings, lan: LanInterface) -> FastAPI:
    app = FastAPI(title="WCam phone", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)
    install_error_handlers(app)
    app.include_router(create_phone_router())
    mount_web(app, settings.web_dist, PHONE_PAGES)
    app.add_middleware(HostGuard, allowed_hosts=phone_allowed_hosts(settings, lan))
    app.add_middleware(SubnetGuard, network=lan.network)
    return app


def create_servers(settings: Settings, lan: LanInterface, certificate: TlsCertificate) -> list[uvicorn.Server]:
    console = uvicorn.Config(
        create_console_app(settings),
        host=settings.console_bind,
        port=settings.console_port,
        log_level=SERVER_LOG_LEVEL,
        proxy_headers=False,
    )
    phone = uvicorn.Config(
        create_phone_app(settings, lan),
        host=str(lan.ip),
        port=settings.phone_port,
        ssl_certfile=certificate.certificate_path,
        ssl_keyfile=certificate.key_path,
        log_level=SERVER_LOG_LEVEL,
        proxy_headers=False,
    )
    return [SupervisedServer(console), SupervisedServer(phone)]


async def serve(servers: Sequence[uvicorn.Server]) -> None:
    def stop(signal_number: int, frame: FrameType | None) -> None:
        for server in servers:
            server.should_exit = True

    previous_handlers = {stop_signal: signal.signal(stop_signal, stop) for stop_signal in STOP_SIGNALS}
    try:
        await asyncio.gather(*(server.serve() for server in servers))
    finally:
        for stop_signal, handler in previous_handlers.items():
            signal.signal(stop_signal, handler)
