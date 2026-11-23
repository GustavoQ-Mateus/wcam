import sys
from pathlib import Path

import pytest

from wcam.config import BUNDLE_ATTRIBUTE, REPOSITORY_ROOT, Settings


def test_packaged_agent_finds_the_pages_and_texts_in_its_own_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, BUNDLE_ATTRIBUTE, str(tmp_path), raising=False)

    settings = Settings()

    assert settings.web_dist == tmp_path / "web" / "dist"
    assert settings.locales_dir == tmp_path / "locales"


def test_agent_from_the_repository_finds_the_pages_and_texts_in_the_repository() -> None:
    settings = Settings()

    assert settings.web_dist == REPOSITORY_ROOT / "web" / "dist"
    assert settings.locales_dir == REPOSITORY_ROOT / "locales"
