#!/usr/bin/env python3
"""Shared public secret scanning rules for verification and release builds."""

from __future__ import annotations

import re


SECRET_PATTERNS = (
    ("provider_token", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[opsur]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,})\b")),
    (
        "generic_secret_assignment",
        re.compile(
            r"(?i)(?<![A-Za-z0-9_])[\"']?(?:token|cookie|credential|secret)[\"']?"
            r"\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{16,}"
        ),
    ),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("authorization_header", re.compile(r"(?i)\bAuthorization\s*:\s*(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}")),
    (
        "named_secret_assignment",
        re.compile(
            r"(?i)(?<![A-Za-z0-9_])[\"']?"
            r"(?:password|passphrase|api[_-]?key|access[_-]?key|secret[_-]?key)[\"']?"
            r"\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{12,}"
        ),
    ),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
)
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
PACKAGE_ALLOWLIST = frozenset({
    ".codex-plugin/plugin.json",
    "LICENSE",
    "NOTICE",
    "assets/icon.svg",
    "skills/auto-route-for-codex/SKILL.md",
    "skills/auto-route-for-codex/agents/openai.yaml",
    "skills/auto-route-for-codex/schemas/router-input.schema.json",
    "skills/auto-route-for-codex/schemas/router-output.schema.json",
    "skills/auto-route-for-codex/schemas/transfer-receipt.schema.json",
    "skills/auto-route-for-codex/schemas/transfer-reservation.schema.json",
    "skills/auto-route-for-codex/scripts/read_current_setting.py",
    "skills/auto-route-for-codex/scripts/route_task.py",
    "skills/auto-route-for-codex/scripts/transfer_state.py",
    "skills/auto-route-for-codex/scripts/validate_contracts.py",
    "skills/auto-route-for-codex/tests/fixtures/cases.json",
    "skills/auto-route-for-codex/tests/test_read_current_setting.py",
    "skills/auto-route-for-codex/tests/test_route_task.py",
    "skills/auto-route-for-codex/tests/test_transfer_state.py",
})


def find_secret(text: str) -> str | None:
    for name, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return name
    return None


def find_private_identifier(text: str) -> str | None:
    if "/" + "Users" + "/" in text:
        return "macos_home_path"
    if UUID_PATTERN.search(text):
        return "uuid"
    if "codex-" + "local-tools" in text:
        return "local_marketplace"
    return None


def assert_scanner_self_test() -> None:
    synthetic_values = (
        *(prefix + "SyntheticValue1234567890" for prefix in ("gho_", "ghp_", "ghr_", "ghs_", "ghu_")),
        "s" + "k-" + "SyntheticValue1234567890",
        "github" + "_pat_" + "SyntheticValue1234567890",
        "xox" + "b-" + "synthetic-value-1234567890",
        "AK" + "IA" + "ABCDEFGHIJKLMNOP",
        "AI" + "za" + "abcdefghijklmnopqrstuvwxyz1234",
        "to" + "ken=" + "syntheticvalue123456",
        '{"to' + 'ken":"syntheticvalue123456"}',
        '{"api_' + 'key":"syntheticvalue123456"}',
    )
    if any(find_secret(value) is None for value in synthetic_values):
        raise ValueError("secret_scanner_self_test_failed")
    private_values = (
        "/" + "Users/example/private",
        "019f0000" + "-abcd-7def-8abc-0123456789ab",
        "codex-" + "local-tools",
    )
    if any(find_private_identifier(value) is None for value in private_values):
        raise ValueError("private_identifier_scanner_self_test_failed")
