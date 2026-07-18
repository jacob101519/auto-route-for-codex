#!/usr/bin/env python3
"""Verify the public repository without network access or external writes."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.4.0-alpha.1"
SKILL_ROOT = ROOT / "skills" / "auto-route-for-codex"
README_VARIANTS = (
    ("English", "README.md"),
    ("Português (Brasil)", "README.pt-BR.md"),
    ("简体中文", "README.zh-CN.md"),
    ("繁體中文", "README.zh-TW.md"),
    ("日本語", "README.ja.md"),
    ("한국어", "README.ko.md"),
    ("Türkçe", "README.tr.md"),
    ("Русский", "README.ru.md"),
    ("Tiếng Việt", "README.vi.md"),
    ("ไทย", "README.th.md"),
    ("Deutsch", "README.de.md"),
    ("Español", "README.es.md"),
)
TRANSLATIONS = tuple(
    ("README.md", translation)
    for _, translation in README_VARIANTS
    if translation != "README.md"
) + (
    ("docs/architecture.md", "docs/i18n/zh-CN/architecture.md"),
    ("docs/compatibility.md", "docs/i18n/zh-CN/compatibility.md"),
    ("docs/configuration.md", "docs/i18n/zh-CN/configuration.md"),
    ("docs/faq.md", "docs/i18n/zh-CN/faq.md"),
    ("docs/installation.md", "docs/i18n/zh-CN/installation.md"),
    ("docs/privacy-and-data-flow.md", "docs/i18n/zh-CN/privacy-and-data-flow.md"),
    ("docs/routing-policy.md", "docs/i18n/zh-CN/routing-policy.md"),
    ("docs/troubleshooting.md", "docs/i18n/zh-CN/troubleshooting.md"),
)
REQUIRED_FILES = {
    ".agents/plugins/marketplace.json",
    ".codex-plugin/plugin.json",
    ".github/CODEOWNERS",
    ".github/ISSUE_TEMPLATE/bug_report_en.yml",
    ".github/ISSUE_TEMPLATE/bug_report_zh-CN.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/documentation_en.yml",
    ".github/ISSUE_TEMPLATE/documentation_zh-CN.yml",
    ".github/ISSUE_TEMPLATE/feature_request_en.yml",
    ".github/ISSUE_TEMPLATE/feature_request_zh-CN.yml",
    ".github/ISSUE_TEMPLATE/routing_mismatch_en.yml",
    ".github/ISSUE_TEMPLATE/routing_mismatch_zh-CN.yml",
    ".github/PULL_REQUEST_TEMPLATE/en.md",
    ".github/PULL_REQUEST_TEMPLATE/zh-CN.md",
    ".github/workflows/ci.yml",
    "CHANGELOG.md",
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "NOTICE",
    "PRIVACY.md",
    "README.md",
    "README.zh-CN.md",
    "ROADMAP.md",
    "SECURITY.md",
    "SUPPORT.md",
    "assets/icon.svg",
    "docs/i18n/README.md",
    "scripts/build_release.py",
    "scripts/verify_public_repo.py",
    "skills/auto-route-for-codex/SKILL.md",
    "skills/auto-route-for-codex/agents/openai.yaml",
    "skills/auto-route-for-codex/schemas/router-input.schema.json",
    "skills/auto-route-for-codex/schemas/router-output.schema.json",
    "skills/auto-route-for-codex/scripts/route_task.py",
    "skills/auto-route-for-codex/scripts/validate_contracts.py",
    "skills/auto-route-for-codex/tests/fixtures/cases.json",
    "skills/auto-route-for-codex/tests/test_route_task.py",
    *(source for source, _ in TRANSLATIONS),
    *(translation for _, translation in TRANSLATIONS),
}
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
SECRET_PATTERNS = (
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,})\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"(?i)\bAuthorization\s*:\s*(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(
        r"(?i)\b(?:password|passphrase|api[_-]?key|access[_-]?key|secret[_-]?key)\b"
        r"\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{12,}"
    ),
)
MARKDOWN_LINK = re.compile(r"!?\[[^]]*]\(([^)]+)\)")
IGNORED_PARTS = {".git", "__pycache__", "dist"}
PRIVATE_HOME_MARKER = "/" + "Users" + "/"
LOCAL_MARKETPLACE_MARKER = "codex-" + "local-tools"


def fail(reason: str) -> None:
    raise SystemExit(f"public repository verification failed: {reason}")


def read_json(relative: str) -> object:
    try:
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid_json:{relative}:{exc.__class__.__name__}")


def observed_files() -> dict[str, Path]:
    observed: dict[str, Path] = {}
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        if path.is_symlink():
            fail(f"symlink:{relative.as_posix()}")
        if path.is_file():
            observed[relative.as_posix()] = path
    missing = sorted(REQUIRED_FILES - set(observed))
    if missing:
        fail("missing_required_files:" + ",".join(missing))
    return observed


def verify_manifests() -> None:
    manifest = read_json(".codex-plugin/plugin.json")
    if not isinstance(manifest, dict):
        fail("plugin_manifest_type")
    if manifest.get("name") != "auto-route-for-codex":
        fail("plugin_name")
    if manifest.get("version") != VERSION or manifest.get("license") != "Apache-2.0":
        fail("plugin_version_or_license")
    if manifest.get("skills") != "./skills/":
        fail("plugin_skill_root")
    interface = manifest.get("interface")
    if not isinstance(interface, dict) or interface.get("displayName") != "Auto Route for Codex":
        fail("plugin_display_name")
    marketplace = read_json(".agents/plugins/marketplace.json")
    expected = {
        "name": "jacob101519",
        "interface": {"displayName": "Jacob Open Source Plugins"},
        "plugins": [{
            "name": "auto-route-for-codex",
            "source": {"source": "local", "path": "."},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Productivity",
        }],
    }
    if marketplace != expected:
        fail("marketplace_manifest")
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---\nname: auto-route-for-codex\n"):
        fail("skill_frontmatter")
    openai_yaml = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    if 'display_name: "Auto Route for Codex"' not in openai_yaml:
        fail("skill_display_name")
    if "allow_implicit_invocation: false" not in openai_yaml:
        fail("implicit_invocation_policy")


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip()] = value.strip()
    return fields


def verify_translations() -> None:
    for source, translation in TRANSLATIONS:
        source_path = ROOT / source
        translation_path = ROOT / translation
        if not source_path.is_file() or not translation_path.is_file():
            fail(f"translation_pair:{source}")
        fields = frontmatter(translation_path.read_text(encoding="utf-8"))
        expected = {
            "translation_of": source,
            "source_revision": "docs-v0.4.0-alpha.1",
            "last_synced_version": VERSION,
        }
        if fields != expected:
            fail(f"translation_metadata:{translation}")


def verify_language_navigation() -> None:
    source_text = (ROOT / "README.md").read_text(encoding="utf-8")
    source_sections = source_text.count("\n## ")
    source_fences = source_text.count("```")
    source_bullets = sum(line.startswith("- ") for line in source_text.splitlines())
    source_table_rows = sum(line.startswith("| ") for line in source_text.splitlines())
    source_links = len(MARKDOWN_LINK.findall(source_text))
    required_tokens = (
        "codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.4.0-alpha.1",
        "codex plugin add auto-route-for-codex@jacob101519",
        "$auto-route-for-codex",
        "v0.4.0-alpha.1",
        "stay + none|efficiency + none + keep",
        ".codex-plugin/plugin.json",
        ".agents/plugins/marketplace.json",
        "skills/auto-route-for-codex/",
        "docs/i18n/zh-CN/",
        "scripts/verify_public_repo.py",
        "scripts/build_release.py",
        "SHA256SUMS",
    )
    for _, current in README_VARIANTS:
        text = (ROOT / current).read_text(encoding="utf-8")
        header = "\n".join(text.splitlines()[:20])
        if " | " not in header:
            fail(f"language_navigation_missing:{current}")
        positions = []
        for label, target in README_VARIANTS:
            if label not in header:
                fail(f"language_label_missing:{current}:{target}")
            positions.append(header.index(label))
            if target != current and f"]({target})" not in header:
                fail(f"language_link_missing:{current}:{target}")
        if positions != sorted(positions):
            fail(f"language_order:{current}")
        if f"]({current})" in header:
            fail(f"current_language_linked:{current}")
        if (
            text.count("\n## ") != source_sections
            or text.count("```") != source_fences
            or sum(line.startswith("- ") for line in text.splitlines()) != source_bullets
            or sum(line.startswith("| ") for line in text.splitlines()) != source_table_rows
            or len(MARKDOWN_LINK.findall(text)) != source_links
        ):
            fail(f"readme_structure:{current}")
        for token in required_tokens:
            if token not in text:
                fail(f"readme_required_token:{current}:{token}")


def verify_privacy(files: dict[str, Path]) -> int:
    scanned = 0
    for relative, path in files.items():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            fail(f"non_utf8_source:{relative}")
        if PRIVATE_HOME_MARKER in text or LOCAL_MARKETPLACE_MARKER in text or UUID_PATTERN.search(text):
            fail(f"private_identifier:{relative}")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            fail(f"secret_value:{relative}")
        scanned += 1
    return scanned


def verify_markdown_links(files: dict[str, Path]) -> int:
    checked = 0
    for relative, path in files.items():
        if path.suffix.lower() != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().strip("<>").split(maxsplit=1)[0]
            if not target or target.startswith("#") or "://" in target or target.startswith("mailto:"):
                continue
            target = target.split("#", 1)[0]
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                fail(f"link_escapes_root:{relative}:{target}")
            if not resolved.exists():
                fail(f"broken_link:{relative}:{target}")
            checked += 1
    return checked


def verify_license() -> str:
    license_data = (ROOT / "LICENSE").read_bytes()
    if b"Apache License" not in license_data or b"Version 2.0, January 2004" not in license_data:
        fail("apache_license")
    return hashlib.sha256(license_data).hexdigest()


def main() -> int:
    files = observed_files()
    verify_manifests()
    verify_translations()
    verify_language_navigation()
    scanned = verify_privacy(files)
    links = verify_markdown_links(files)
    summary = {
        "status": "pass",
        "version": VERSION,
        "files": len(files),
        "privacy_scanned": scanned,
        "translation_pairs": len(TRANSLATIONS),
        "readme_locales": len(README_VARIANTS),
        "local_links_checked": links,
        "license_sha256": verify_license(),
    }
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
