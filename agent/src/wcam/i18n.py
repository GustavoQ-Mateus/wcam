import ctypes
import json
import os
import sys
from pathlib import Path
from typing import Literal

type Language = Literal["en", "pt-BR"]

LOCALE_NAME_MAX_LENGTH = 85
LANGUAGE_VARIABLES = ("LC_ALL", "LC_MESSAGES", "LANG")


class Messages:
    def __init__(self, catalog: dict[str, str]) -> None:
        self._catalog = catalog

    def text(self, key: str, **values: str) -> str:
        return self._catalog[key].format(**values)


def resolve_language(tag: str) -> Language:
    return "pt-BR" if tag.lower().startswith("pt") else "en"


def system_language_tag() -> str:
    if sys.platform == "win32":
        buffer = ctypes.create_unicode_buffer(LOCALE_NAME_MAX_LENGTH)
        ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer, LOCALE_NAME_MAX_LENGTH)
        return buffer.value
    return next((os.environ[name] for name in LANGUAGE_VARIABLES if os.environ.get(name)), "")


def load_messages(locales_dir: Path, language: Language) -> Messages:
    catalog: dict[str, str] = json.loads((locales_dir / f"{language}.json").read_text(encoding="utf-8"))
    return Messages(catalog)
