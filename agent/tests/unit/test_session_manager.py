import asyncio

import pytest

from tests.fakes import AGENT_FINGERPRINT, OFFER_SDP, PHONE_FINGERPRINT, FakeClock, FakePeerFactory
from wcam.pairing.confirmation_code import confirmation_code
from wcam.pairing.errors import PairingTokenInvalidError, PairingWindowClosedError
from wcam.sessions.errors import (
    InvalidOfferError,
    NoActiveSessionError,
    NoSessionAwaitingConfirmationError,
    SessionAlreadyActiveError,
    TooManyAttemptsError,
)
from wcam.sessions.manager import (
    CONFIRMATION_TIMEOUT_SECONDS,
    EndReason,
    SessionManager,
    SessionRequest,
    SessionState,
)

PHONE_IP = "192.168.0.23"
SHORT_TIMEOUT = 0.01


def session_request(token: str, offer_sdp: str = OFFER_SDP) -> SessionRequest:
    return SessionRequest(token, offer_sdp, PHONE_IP, "Android · Chrome")


async def connected_manager(
    factory: FakePeerFactory,
    confirmation_timeout: float = CONFIRMATION_TIMEOUT_SECONDS,
) -> SessionManager:
    manager = SessionManager(factory, FakeClock(), confirmation_timeout)
    await manager.create_session(session_request(manager.open_pairing().token))
    factory.last.events.on_connected()
    return manager


async def test_session_starts_connecting_without_code() -> None:
    manager = SessionManager(FakePeerFactory())

    await manager.create_session(session_request(manager.open_pairing().token))

    session = manager.status().session
    assert session is not None
    assert (session.state, session.confirmation_code) == (SessionState.CONNECTING, None)


async def test_connected_session_awaits_confirmation_with_contract_code() -> None:
    factory = FakePeerFactory()
    manager = SessionManager(factory)
    offer = await manager.create_session(session_request(manager.open_pairing().token))

    factory.last.events.on_connected()

    session = manager.status().session
    assert session is not None
    assert session.state is SessionState.AWAITING_CONFIRMATION
    assert session.confirmation_code == confirmation_code(
        offer.confirmation_nonce, PHONE_FINGERPRINT, AGENT_FINGERPRINT
    )
    assert factory.last.sent == [
        {"type": "session_state", "state": "awaiting_confirmation"},
        {"type": "quality_preset", "preset": "balanced"},
    ]


async def test_confirm_opens_gate_and_goes_live() -> None:
    factory = FakePeerFactory()
    manager = await connected_manager(factory)

    manager.confirm()

    session = manager.status().session
    assert session is not None
    assert session.state is SessionState.LIVE
    assert factory.last.gate_open
    assert factory.last.sent[-1] == {"type": "session_state", "state": "live"}


async def test_confirm_without_awaiting_session_is_rejected() -> None:
    manager = SessionManager(FakePeerFactory())

    with pytest.raises(NoSessionAwaitingConfirmationError):
        manager.confirm()


async def test_second_session_is_rejected_while_one_is_active() -> None:
    manager = SessionManager(FakePeerFactory())
    await manager.create_session(session_request(manager.open_pairing().token))

    with pytest.raises(SessionAlreadyActiveError):
        await manager.create_session(session_request("another-token"))


async def test_pairing_cannot_open_while_session_is_active() -> None:
    manager = SessionManager(FakePeerFactory())
    await manager.create_session(session_request(manager.open_pairing().token))

    with pytest.raises(SessionAlreadyActiveError):
        manager.open_pairing()


async def test_awaiting_confirmation_times_out_after_two_minutes() -> None:
    factory = FakePeerFactory()
    manager = await connected_manager(factory, confirmation_timeout=SHORT_TIMEOUT)

    await asyncio.sleep(SHORT_TIMEOUT * 5)

    status = manager.status()
    assert CONFIRMATION_TIMEOUT_SECONDS == 120
    assert status.session is None
    assert status.last_ended is not None
    assert status.last_ended.reason is EndReason.CONFIRMATION_TIMEOUT
    assert factory.last.closed


async def test_confirmed_session_does_not_time_out() -> None:
    manager = await connected_manager(FakePeerFactory(), confirmation_timeout=SHORT_TIMEOUT)

    manager.confirm()
    await asyncio.sleep(SHORT_TIMEOUT * 5)

    assert manager.status().session is not None


async def test_reject_ends_session_and_requires_new_pairing() -> None:
    factory = FakePeerFactory()
    manager = SessionManager(factory)
    token = manager.open_pairing().token
    await manager.create_session(session_request(token))
    factory.last.events.on_connected()

    await manager.reject()

    status = manager.status()
    assert status.session is None
    assert status.last_ended is not None
    assert status.last_ended.reason is EndReason.REJECTED
    assert factory.last.sent[-1] == {"type": "session_state", "state": "ended", "reason": "rejected"}
    assert factory.last.closed
    with pytest.raises(PairingTokenInvalidError):
        await manager.create_session(session_request(token))


async def test_disconnect_ends_session_by_pc() -> None:
    manager = await connected_manager(FakePeerFactory())

    await manager.disconnect()

    last_ended = manager.status().last_ended
    assert last_ended is not None
    assert last_ended.reason is EndReason.DISCONNECTED_BY_PC


async def test_disconnect_without_session_is_rejected() -> None:
    manager = SessionManager(FakePeerFactory())

    with pytest.raises(NoActiveSessionError):
        await manager.disconnect()


async def test_lost_connection_ends_session_with_its_reason() -> None:
    factory = FakePeerFactory()
    manager = await connected_manager(factory)

    factory.last.events.on_lost(EndReason.DISCONNECTED_BY_PHONE)
    await asyncio.sleep(0)

    last_ended = manager.status().last_ended
    assert manager.status().session is None
    assert last_ended is not None
    assert last_ended.reason is EndReason.DISCONNECTED_BY_PHONE


async def test_invalid_offer_does_not_consume_token() -> None:
    manager = SessionManager(FakePeerFactory())
    token = manager.open_pairing().token

    with pytest.raises(InvalidOfferError):
        await manager.create_session(session_request(token, offer_sdp="not an sdp"))

    await manager.create_session(session_request(token))


async def test_blocked_ip_is_rejected_even_with_valid_token() -> None:
    manager = SessionManager(FakePeerFactory())
    for _ in range(5):
        with pytest.raises(PairingWindowClosedError):
            await manager.create_session(session_request("guess"))
    token = manager.open_pairing().token

    with pytest.raises(TooManyAttemptsError):
        await manager.create_session(session_request(token))


async def test_busy_rejection_does_not_count_as_failure() -> None:
    manager = SessionManager(FakePeerFactory())
    await manager.create_session(session_request(manager.open_pairing().token))
    for _ in range(5):
        with pytest.raises(SessionAlreadyActiveError):
            await manager.create_session(session_request("guess"))
    await manager.disconnect()

    await manager.create_session(session_request(manager.open_pairing().token))
