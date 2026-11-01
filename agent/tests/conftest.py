from ipaddress import IPv4Address, IPv4Network
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from wcam.config import Settings
from wcam.network.lan import LanInterface

LAN = LanInterface(IPv4Address("192.168.0.10"), IPv4Network("192.168.0.0/24"))
PHONE_IN_LAN = "192.168.0.23"
CLIENT_PORT = 50000


@pytest.fixture
def web_dist(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>WCam</title>", encoding="utf-8")
    return dist


@pytest.fixture
def settings(tmp_path: Path, web_dist: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", web_dist=web_dist)


def console_client(app: FastAPI) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", CLIENT_PORT))
    return httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8080")


def phone_client(app: FastAPI, client_ip: str = PHONE_IN_LAN) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, client=(client_ip, CLIENT_PORT))
    return httpx.AsyncClient(transport=transport, base_url=f"https://{LAN.ip}:8443")
