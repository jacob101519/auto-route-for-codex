#!/usr/bin/env python3
"""Build a deterministic plugin ZIP and SHA256SUMS file."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
import zipfile
from pathlib import Path

from public_hygiene import (
    PACKAGE_ALLOWLIST,
    assert_scanner_self_test,
    find_private_identifier,
    find_secret,
)


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.0-alpha.1"
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
)
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
FORBIDDEN_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
FORBIDDEN_SUFFIXES = {".pyc", ".log", ".sqlite", ".sqlite3", ".db", ".pid", ".lock", ".sock"}


def fail(reason: str) -> None:
    raise SystemExit(f"release build failed: {reason}")


def assert_release_hygiene() -> None:
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if path.is_symlink():
            fail(f"symlink:{relative.as_posix()}")
        if relative.name == "snapshot-manifest.json":
            fail(f"private_export_manifest_must_not_be_published:{relative.as_posix()}")
        if relative.parts and relative.parts[0] == "dist":
            dist_root = ROOT / "dist"
            if dist_root.is_symlink() or not dist_root.is_dir():
                fail("unsafe_ignored_path:dist")
            continue
        if relative.parts and relative.parts[0] == ".git":
            continue
        if any(part in FORBIDDEN_PARTS for part in relative.parts):
            fail(f"runtime_state:{relative.as_posix()}")
        if path.is_file() and path.suffix.lower() in FORBIDDEN_SUFFIXES:
            fail(f"runtime_state:{relative.as_posix()}")


def secure_output_dir(raw_value: str) -> Path:
    supplied = Path(os.path.abspath(Path(raw_value).expanduser()))
    system_aliases = (
        (Path("/var"), Path("/private/var")),
        (Path("/tmp"), Path("/private/tmp")),
    )
    candidate = supplied
    for alias, target in system_aliases:
        try:
            relative = supplied.relative_to(alias)
        except ValueError:
            continue
        try:
            alias_info = alias.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(alias_info.st_mode):
            if (
                alias_info.st_uid != 0
                or alias.resolve(strict=True) != target
                or target.resolve(strict=True) != target
                or not target.is_dir()
            ):
                fail(f"unsafe_system_alias:{alias}")
            candidate = target / relative
        break

    def reject_symlink_components() -> None:
        current = Path(candidate.anchor)
        for part in candidate.parts[1:]:
            current /= part
            try:
                info = current.lstat()
            except FileNotFoundError:
                break
            if stat.S_ISLNK(info.st_mode):
                fail(f"symlink_output_dir:{current}")
            if current != candidate and not stat.S_ISDIR(info.st_mode):
                fail(f"unsafe_output_parent:{current}")

    reject_symlink_components()
    parent = candidate.parent
    try:
        parent_info = parent.lstat()
    except FileNotFoundError:
        fail("output_parent_missing")
    trusted_shared_temp = (
        parent == Path("/private/tmp")
        and parent_info.st_uid == 0
        and bool(parent_info.st_mode & stat.S_ISVTX)
        and bool(parent_info.st_mode & stat.S_IWUSR)
    )
    if (
        not stat.S_ISDIR(parent_info.st_mode)
        or stat.S_ISLNK(parent_info.st_mode)
        or (
            not trusted_shared_temp
            and (
                parent_info.st_uid != os.getuid()
                or parent_info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            )
        )
    ):
        fail("unsafe_output_parent")
    try:
        os.mkdir(candidate, mode=0o700)
    except FileExistsError:
        pass
    except OSError:
        fail("output_dir_create_failed")
    reject_symlink_components()
    try:
        info = candidate.lstat()
    except FileNotFoundError:
        fail("missing_output_dir")
    if (
        not stat.S_ISDIR(info.st_mode)
        or stat.S_ISLNK(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        fail("unsafe_output_dir")
    resolved = candidate.resolve(strict=True)
    if resolved != candidate:
        fail("output_dir_resolution_mismatch")
    return candidate


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
    observed = {path.relative_to(ROOT).as_posix() for path in paths}
    missing = sorted(PACKAGE_ALLOWLIST - observed)
    unexpected = sorted(observed - PACKAGE_ALLOWLIST)
    if missing:
        fail("missing_package_file:" + ",".join(missing))
    if unexpected:
        fail("unexpected_package_file:" + ",".join(unexpected))
    result = sorted(paths, key=lambda item: item.relative_to(ROOT).as_posix())
    for path in result:
        try:
            text = path.read_bytes().decode("ascii")
        except UnicodeDecodeError:
            fail(f"non_ascii_package_file:{path.relative_to(ROOT).as_posix()}")
        secret_kind = find_secret(text)
        if secret_kind:
            fail(f"secret_value:{path.relative_to(ROOT).as_posix()}:{secret_kind}")
        private_kind = find_private_identifier(text)
        if private_kind:
            fail(f"private_identifier:{path.relative_to(ROOT).as_posix()}:{private_kind}")
    return result


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
            executable = (
                relative.startswith("skills/auto-route-for-codex/scripts/")
                and source.suffix == ".py"
            )
            permissions = 0o755 if executable else 0o644
            info.external_attr = (stat.S_IFREG | permissions) << 16
            archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def atomic_replace(source: Path, destination: Path) -> None:
    os.replace(source, destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    try:
        assert_scanner_self_test()
    except ValueError as exc:
        fail(str(exc))
    verify_version()
    assert_release_hygiene()
    sources = source_files()
    output_dir = secure_output_dir(args.output_dir)
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
