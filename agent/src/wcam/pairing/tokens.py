import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from wcam.clock import Clock, utc_now
from wcam.pairing.errors import PairingTokenExpiredError, PairingTokenInvalidError, PairingWindowClosedError

PAIRING_WINDOW = timedelta(seconds=120)
TOKEN_BYTES = 16


@dataclass(frozen=True, slots=True)
class PairingTicket:
    token: str
    expires_at: datetime


class PairingWindow:
    def __init__(self, clock: Clock = utc_now) -> None:
        self._clock = clock
        self._active_hash: bytes | None = None
        self._expires_at: datetime | None = None
        self._retired_hash: bytes | None = None
        self._retired_as_expired = False

    @property
    def expires_at(self) -> datetime | None:
        self._expire_if_due()
        return self._expires_at

    def open(self) -> PairingTicket:
        self._expire_if_due()
        self._retire(as_expired=False)
        token = secrets.token_urlsafe(TOKEN_BYTES)
        self._active_hash = hash_token(token)
        self._expires_at = self._clock() + PAIRING_WINDOW
        return PairingTicket(token, self._expires_at)

    def close(self) -> None:
        self._active_hash = None
        self._expires_at = None

    def consume(self, token: str) -> None:
        self._expire_if_due()
        token_hash = hash_token(token)
        if self._active_hash is not None and hmac.compare_digest(token_hash, self._active_hash):
            self._retire(as_expired=False)
            return
        if self._retired_hash is not None and hmac.compare_digest(token_hash, self._retired_hash):
            raise PairingTokenExpiredError if self._retired_as_expired else PairingTokenInvalidError
        if self._active_hash is None:
            raise PairingWindowClosedError
        raise PairingTokenInvalidError

    def _expire_if_due(self) -> None:
        if self._expires_at is not None and self._clock() >= self._expires_at:
            self._retire(as_expired=True)

    def _retire(self, *, as_expired: bool) -> None:
        if self._active_hash is None:
            return
        self._retired_hash = self._active_hash
        self._retired_as_expired = as_expired
        self.close()


def hash_token(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()
