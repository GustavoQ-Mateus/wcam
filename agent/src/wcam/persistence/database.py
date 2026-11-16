import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path

DATABASE_FILE = "wcam.sqlite3"
MIGRATIONS_PACKAGE = "wcam.persistence.migrations"
MIGRATION_SUFFIX = ".sql"
IN_MEMORY = ":memory:"


def open_database(data_dir: Path | None) -> sqlite3.Connection:
    if data_dir is not None:
        data_dir.mkdir(parents=True, exist_ok=True)
    location = IN_MEMORY if data_dir is None else str(data_dir / DATABASE_FILE)
    connection = sqlite3.connect(location, check_same_thread=False, autocommit=True)
    connection.execute("pragma foreign_keys = on")
    migrate(connection)
    return connection


def migrate(connection: sqlite3.Connection) -> None:
    applied = connection.execute("pragma user_version").fetchone()[0]
    for number, script in migrations():
        if number <= applied:
            continue
        connection.executescript("".join(["begin;", script, f"pragma user_version = {number};", "commit;"]))


def migrations() -> list[tuple[int, str]]:
    folder = resources.files(MIGRATIONS_PACKAGE)
    scripts = [entry for entry in folder.iterdir() if entry.name.endswith(MIGRATION_SUFFIX)]
    return sorted((int(entry.name.split("_", 1)[0]), entry.read_text(encoding="utf-8")) for entry in scripts)


@contextmanager
def transaction(connection: sqlite3.Connection) -> Generator[sqlite3.Connection]:
    connection.execute("begin")
    try:
        yield connection
    except BaseException:
        connection.execute("rollback")
        raise
    connection.execute("commit")
