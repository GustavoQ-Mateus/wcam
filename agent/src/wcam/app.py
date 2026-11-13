import asyncio
import contextlib
import signal
from collections.abc import Callable, Generator, Sequence
from socket import socket
from types import FrameType

import uvicorn
from fastapi import FastAPI

from wcam import __version__
from wcam.api.console_routes import create_console_router
from wcam.api.dev_routes import create_dev_router
from wcam.api.errors import install_error_handlers
from wcam.api.host_guard import HostGuard
from wcam.api.phone_routes import create_phone_router
from wcam.api.static import mount_web
from wcam.api.subnet_guard import SubnetGuard
from wcam.config import Settings
from wcam.network.certificates import TlsCertificate
from wcam.network.lan import LanInterface
from wcam.services import AgentServices

CONSOLE_PAGES = ("/",)
PHONE_PAGES = ("/cam",)
STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM)
SERVER_LOG_LEVEL = "warning"
GRACEFUL_SHUTDOWN_SECONDS = 2


class SupervisedServer(uvicorn.Server):
    def __init__(self, config: uvicorn.Config, before_shutdown: Callable[[], None] = lambda: None) -> None:
        super().__init__(config)
        self._before_shutdown = before_shutdown

    async def shutdown(self, sockets: list[socket] | None = None) -> None:
        self._before_shutdown()
        await super().shutdown(sockets)

    @contextlib.contextmanager
    def capture_signals(self) -> Generator[None]:
        yield


def console_allowed_hosts(settings: Settings) -> list[str]:
    port = settings.console_port
    return [f"127.0.0.1:{port}", f"localhost:{port}", *settings.extra_allowed_hosts]


def phone_allowed_hosts(settings: Settings, lan: LanInterface) -> list[str]:
    return [f"{lan.ip}:{settings.phone_port}", *settings.extra_allowed_hosts]


def phone_page_url(settings: Settings, lan: LanInterface) -> str:
    return f"https://{lan.ip}:{settings.phone_port}/cam"


def create_console_app(settings: Settings, services: AgentServices, phone_url: str) -> FastAPI:
    app = FastAPI(title="WCam console", version=__version__)
    install_error_handlers(app)
    app.include_router(create_console_router(services, phone_url))
    if services.comparisons is not None:
        app.include_router(create_dev_router(services.manager, services.comparisons))
    mount_web(app, settings.web_dist, CONSOLE_PAGES)
    app.add_middleware(HostGuard, allowed_hosts=console_allowed_hosts(settings))
    return app


def create_phone_app(settings: Settings, lan: LanInterface, services: AgentServices) -> FastAPI:
    app = FastAPI(title="WCam phone", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)
    install_error_handlers(app)
    app.include_router(create_phone_router(services.manager))
    mount_web(app, settings.web_dist, PHONE_PAGES)
    app.add_middleware(HostGuard, allowed_hosts=phone_allowed_hosts(settings, lan))
    app.add_middleware(SubnetGuard, network=lan.network)
    return app


def create_servers(
    settings: Settings,
    lan: LanInterface,
    certificate: TlsCertificate,
    services: AgentServices,
) -> list[uvicorn.Server]:
    console = uvicorn.Config(
        create_console_app(settings, services, phone_page_url(settings, lan)),
        host=settings.console_bind,
        port=settings.console_port,
        log_level=SERVER_LOG_LEVEL,
        proxy_headers=False,
        timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_SECONDS,
    )
    phone = uvicorn.Config(
        create_phone_app(settings, lan, services),
        host=str(lan.ip),
        port=settings.phone_port,
        ssl_certfile=certificate.certificate_path,
        ssl_keyfile=certificate.key_path,
        log_level=SERVER_LOG_LEVEL,
        proxy_headers=False,
        timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_SECONDS,
    )
    return [SupervisedServer(console, services.status_changes.close), SupervisedServer(phone)]


async def run(servers: Sequence[uvicorn.Server], services: AgentServices) -> None:
    background = [asyncio.create_task(services.pipeline.run()), asyncio.create_task(services.cpu.run())]
    services.camera.start()
    try:
        await serve(servers)
    finally:
        await services.manager.shutdown()
        if services.comparisons is not None:
            await services.comparisons.close()
        await services.camera.close()
        for task in background:
            task.cancel()
        await asyncio.gather(*background, return_exceptions=True)


async def serve(servers: Sequence[uvicorn.Server]) -> None:
    await asyncio.gather(*(server.serve() for server in servers))


@contextlib.contextmanager
def stop_signals_handled(servers: Sequence[uvicorn.Server]) -> Generator[None]:
    # Installed before asyncio.run, so the runner keeps this handler instead of its own, which would cancel the
    # shutdown on a second Ctrl+C and end with a KeyboardInterrupt traceback.
    def stop(signal_number: int, frame: FrameType | None) -> None:
        for server in servers:
            server.should_exit = True

    previous_handlers = {stop_signal: signal.signal(stop_signal, stop) for stop_signal in STOP_SIGNALS}
    try:
        yield
    finally:
        for stop_signal, handler in previous_handlers.items():
            signal.signal(stop_signal, handler)
