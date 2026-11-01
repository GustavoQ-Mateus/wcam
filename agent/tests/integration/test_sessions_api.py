import httpx

from tests.conftest import console_app, console_client, phone_app, phone_client
from tests.fakes import OFFER_SDP, FakePeerFactory
from wcam.config import Settings
from wcam.sessions.manager import SessionManager

ANDROID_CHROME = "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/141.0.0.0 Mobile Safari/537.36"


async def open_pairing(manager: SessionManager, settings: Settings) -> str:
    async with console_client(console_app(settings, manager)) as console:
        response = await console.post("/api/pairing")
    return response.json()["url"].split("#t=")[1]


async def post_session(manager: SessionManager, settings: Settings, token: str) -> httpx.Response:
    async with phone_client(phone_app(settings, manager)) as phone:
        return await phone.post(
            "/api/sessions",
            json={"token": token, "sdp": OFFER_SDP},
            headers={"User-Agent": ANDROID_CHROME},
        )


async def test_pairing_returns_url_with_token_in_fragment_and_qr(settings: Settings) -> None:
    async with console_client(console_app(settings)) as console:
        response = await console.post("/api/pairing")

    body = response.json()
    assert response.status_code == 201
    assert body["url"].startswith("https://192.168.0.10:8443/cam#t=")
    assert body["qrSvg"].startswith("<svg")
    assert body["expiresAt"].endswith("Z")


async def test_status_without_pairing_or_session_is_all_null(settings: Settings) -> None:
    async with console_client(console_app(settings)) as console:
        response = await console.get("/api/status")

    assert response.json() == {"pairing": None, "session": None, "lastEnded": None}


async def test_session_is_created_and_shown_in_status(settings: Settings) -> None:
    manager = SessionManager(FakePeerFactory())
    token = await open_pairing(manager, settings)

    created = await post_session(manager, settings, token)
    async with console_client(console_app(settings, manager)) as console:
        status = (await console.get("/api/status")).json()

    assert created.status_code == 201
    assert set(created.json()) == {"sessionId", "sdp", "confirmationNonce"}
    assert len(created.json()["confirmationNonce"]) == 32
    assert status["pairing"] is None
    assert status["session"]["id"] == created.json()["sessionId"]
    assert status["session"]["state"] == "connecting"
    assert status["session"]["deviceName"] == "Android · Chrome"
    assert status["session"]["remoteIp"] == "192.168.0.23"
    assert status["session"]["video"] is None


async def test_reused_token_is_rejected_as_invalid(settings: Settings) -> None:
    manager = SessionManager(FakePeerFactory())
    token = await open_pairing(manager, settings)
    await post_session(manager, settings, token)
    await manager.disconnect()

    response = await post_session(manager, settings, token)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "pairing_token_invalid"


async def test_session_while_one_is_active_is_rejected_as_busy(settings: Settings) -> None:
    manager = SessionManager(FakePeerFactory())
    token = await open_pairing(manager, settings)
    await post_session(manager, settings, token)

    response = await post_session(manager, settings, token)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "session_already_active"


async def test_session_without_pairing_is_rejected_as_window_closed(settings: Settings) -> None:
    response = await post_session(SessionManager(FakePeerFactory()), settings, "unknown")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "pairing_window_closed"


async def test_confirm_without_session_is_rejected(settings: Settings) -> None:
    async with console_client(console_app(settings)) as console:
        response = await console.post("/api/sessions/current/confirm")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "no_session_awaiting_confirmation"


async def test_disconnect_without_session_is_rejected(settings: Settings) -> None:
    async with console_client(console_app(settings)) as console:
        response = await console.delete("/api/sessions/current")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "no_active_session"


async def test_closed_pairing_reports_null_in_status(settings: Settings) -> None:
    manager = SessionManager(FakePeerFactory())
    await open_pairing(manager, settings)

    async with console_client(console_app(settings, manager)) as console:
        closed = await console.delete("/api/pairing")
        status = (await console.get("/api/status")).json()

    assert closed.status_code == 204
    assert status["pairing"] is None


async def test_session_body_without_sdp_is_invalid_request(settings: Settings) -> None:
    async with phone_client(phone_app(settings)) as phone:
        response = await phone.post("/api/sessions", json={"token": "x"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
