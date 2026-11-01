from datetime import timedelta

import pytest

from tests.fakes import FakeClock
from wcam.pairing.attempts import BLOCK_DURATION, AttemptLimiter
from wcam.pairing.errors import PairingTokenExpiredError, PairingTokenInvalidError, PairingWindowClosedError
from wcam.pairing.tokens import PAIRING_WINDOW, PairingWindow, hash_token

PHONE_IP = "192.168.0.23"


def test_pairing_token_is_stored_only_as_hash() -> None:
    window = PairingWindow()

    ticket = window.open()

    stored = repr(vars(window))
    assert ticket.token not in stored
    assert repr(hash_token(ticket.token)) in stored


def test_pairing_token_can_be_used_once() -> None:
    window = PairingWindow()
    ticket = window.open()

    window.consume(ticket.token)

    with pytest.raises(PairingTokenInvalidError):
        window.consume(ticket.token)


def test_consumed_token_closes_the_window() -> None:
    window = PairingWindow()

    window.consume(window.open().token)

    assert window.expires_at is None


def test_expired_pairing_token_is_rejected_as_expired() -> None:
    clock = FakeClock()
    window = PairingWindow(clock)
    ticket = window.open()

    clock.advance(PAIRING_WINDOW)

    with pytest.raises(PairingTokenExpiredError):
        window.consume(ticket.token)


def test_replaced_pairing_token_is_rejected_as_invalid() -> None:
    window = PairingWindow()
    first = window.open()
    window.open()

    with pytest.raises(PairingTokenInvalidError):
        window.consume(first.token)


def test_session_without_open_window_is_rejected_as_window_closed() -> None:
    window = PairingWindow()

    with pytest.raises(PairingWindowClosedError):
        window.consume("unknown-token")


def test_unknown_token_with_open_window_is_rejected_as_invalid() -> None:
    window = PairingWindow()
    window.open()

    with pytest.raises(PairingTokenInvalidError):
        window.consume("unknown-token")


def test_five_failures_block_the_ip_for_ten_minutes() -> None:
    clock = FakeClock()
    limiter = AttemptLimiter(clock)
    for _ in range(5):
        limiter.record_failure(PHONE_IP)

    blocked_now = limiter.is_blocked(PHONE_IP)
    clock.advance(BLOCK_DURATION - timedelta(seconds=1))
    blocked_almost_ten_minutes_later = limiter.is_blocked(PHONE_IP)
    clock.advance(timedelta(seconds=1))

    assert blocked_now
    assert blocked_almost_ten_minutes_later
    assert not limiter.is_blocked(PHONE_IP)


def test_failures_spread_beyond_a_minute_do_not_block() -> None:
    clock = FakeClock()
    limiter = AttemptLimiter(clock)

    for _ in range(5):
        limiter.record_failure(PHONE_IP)
        clock.advance(timedelta(seconds=15))

    assert not limiter.is_blocked(PHONE_IP)
