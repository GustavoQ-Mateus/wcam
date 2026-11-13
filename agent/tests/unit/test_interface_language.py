import json
import re
from pathlib import Path

import pytest

from wcam.config import Settings

LANGUAGES = ("en", "pt-BR")
FORBIDDEN_TERMS = (
    "agente",
    "agentes",
    "servidor",
    "servidores",
    "sessão",
    "sessões",
    "token",
    "tokens",
    "pareamento",
    "pareamentos",
    "requisição",
    "requisições",
    "interface",
    "interfaces",
    "agent",
    "agents",
    "server",
    "servers",
    "session",
    "sessions",
    "pairing",
    "pairings",
    "request",
    "requests",
)
ALLOWED_PREFIXES = ("dev.",)
ALLOWED_KEYS = ("terminal.fingerprint",)
FORBIDDEN_WORD = re.compile(r"\b(" + "|".join(FORBIDDEN_TERMS) + r")\b", re.IGNORECASE)


def texts(language: str) -> dict[str, str]:
    path = Path(Settings().locales_dir) / f"{language}.json"
    loaded: dict[str, str] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def is_allowed(key: str) -> bool:
    return key.startswith(ALLOWED_PREFIXES) or key in ALLOWED_KEYS


@pytest.mark.parametrize("language", LANGUAGES)
def test_interface_texts_never_use_architecture_terms(language: str) -> None:
    offending = {
        key: match.group(0)
        for key, value in texts(language).items()
        if not is_allowed(key) and (match := FORBIDDEN_WORD.search(value)) is not None
    }

    assert offending == {}


def test_the_check_finds_a_forbidden_term_in_any_case() -> None:
    assert FORBIDDEN_WORD.search("Abra a Sessão de novo") is not None
    assert FORBIDDEN_WORD.search("The Server stopped") is not None
    assert FORBIDDEN_WORD.search("Interfaceamento") is None
