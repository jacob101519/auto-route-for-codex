#!/usr/bin/env python3
"""Build a deterministic plugin ZIP and SHA256SUMS file."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.4.0-alpha.1"
ARCHIVE_NAME = f"auto-route-for-codex-{VERSION}.zip"
CHECKSUM_NAME = "SHA256SUMS"
INCLUDE_ROOTS = (
    Path(".codex-plugin"),
    Path("assets"),
    Path("skills"),
)
INCLUDE_FILES = (
    Path("LICENSE"),
    Path("NOTICE"),
    Path("README.md"),
)
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
FORBIDDEN_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
FORBIDDEN_SUFFIXES = {".pyc", ".log", ".sqlite", ".sqlite3", ".db", ".pid", ".lock", ".sock"}


def fail(reason: str) -> None:
    raise SystemExit(f"release build failed: {reason}")


def assert_release_hygiene() -> None:
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if ".git" in relative.parts or "dist" in relative.parts:
            continue
        if path.is_symlink():
            fail(f"symlink:{relative.as_posix()}")
        if any(part in FORBIDDEN_PARTS for part in relative.parts):
            fail(f"runtime_state:{relative.as_posix()}")
        if path.is_file() and path.suffix.lower() in FORBIDDEN_SUFFIXES:
            fail(f"runtime_state:{relative.as_posix()}")


def source_files() -> list[Path]:
    paths: list[Path] = []
    for root in INCLUDE_ROOTS:
        absolute = ROOT / root
        if not absolute.is_dir() or absolute.is_symlink():
            fail(f"unsafe_or_missing_root:{root.as_posix()}")
        for path in absolute.rglob("*"):
            if path.is_symlink():
                fail(f"symlink:{path.relative_to(ROOT).as_posix()}")
            if path.is_file():
                paths.append(path)
    for relative in INCLUDE_FILES:
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            fail(f"unsafe_or_missing_file:{relative.as_posix()}")
        paths.append(path)
    return sorted(paths, key=lambda item: item.relative_to(ROOT).as_posix())


def verify_version() -> None:
    try:
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"plugin_manifest:{exc.__class__.__name__}")
    if manifest.get("name") != "auto-route-for-codex" or manifest.get("version") != VERSION:
        fail("version_mismatch")


def write_zip(destination: Path, sources: list[Path]) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in sources:
            relative = source.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(relative, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def atomic_replace(source: Path, destination: Path) -> None:
    os.replace(source, destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    verify_version()
    assert_release_hygiene()
    sources = source_files()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / ARCHIVE_NAME
    checksum_path = output_dir / CHECKSUM_NAME
    with tempfile.TemporaryDirectory(prefix="auto-route-release-", dir=output_dir) as temporary:
        temporary_dir = Path(temporary)
        staged_archive = temporary_dir / ARCHIVE_NAME
        staged_checksum = temporary_dir / CHECKSUM_NAME
        write_zip(staged_archive, sources)
        digest = hashlib.sha256(staged_archive.read_bytes()).hexdigest()
        staged_checksum.write_text(f"{digest}  {ARCHIVE_NAME}\n", encoding="ascii")
        atomic_replace(staged_archive, archive_path)
        atomic_replace(staged_checksum, checksum_path)
    result = {
        "status": "pass",
        "version": VERSION,
        "source_files": len(sources),
        "artifacts": [
            {"name": ARCHIVE_NAME, "sha256": digest},
            {"name": CHECKSUM_NAME, "sha256": hashlib.sha256(checksum_path.read_bytes()).hexdigest()},
        ],
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
