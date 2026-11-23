from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

AGENT = Path(SPECPATH).parent
REPOSITORY = AGENT.parent

analysis = Analysis(
    [str(AGENT / "packaging" / "wcam_entry.py")],
    pathex=[str(AGENT / "src")],
    datas=[
        (str(REPOSITORY / "web" / "dist"), "web/dist"),
        (str(REPOSITORY / "locales"), "locales"),
        *collect_data_files("wcam"),
        *copy_metadata("wcam"),
    ],
    hiddenimports=[*collect_submodules("uvicorn"), *collect_submodules("wcam")],
)
python_archive = PYZ(analysis.pure)
executable = EXE(
    python_archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="wcam",
    console=True,
)
COLLECT(executable, analysis.binaries, analysis.datas, name="wcam")
