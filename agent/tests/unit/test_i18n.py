from wcam.config import Settings
from wcam.i18n import load_messages, resolve_language


def test_portuguese_tags_resolve_to_pt_br() -> None:
    assert [resolve_language(tag) for tag in ("pt-BR", "pt_PT", "PT")] == ["pt-BR", "pt-BR", "pt-BR"]


def test_other_tags_resolve_to_english() -> None:
    assert [resolve_language(tag) for tag in ("en-US", "es-ES", "")] == ["en", "en", "en"]


def test_messages_fill_placeholders() -> None:
    messages = load_messages(Settings().locales_dir, "pt-BR")

    assert messages.text("terminal.title", version="0.1.0") == "WCam 0.1.0"
