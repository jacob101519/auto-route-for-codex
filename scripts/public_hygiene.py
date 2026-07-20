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
EMAIL_PATTERN = re.compile(
    r"(?<![A-Za-z0-9._%+-])"
    r"[A-Za-z0-9._%+-]+@(?:localhost|"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)"
    r"(?![A-Za-z0-9._%+-])",
    re.IGNORECASE,
)
GITHUB_NOREPLY_PATTERN = re.compile(
    r"^(?:noreply@github\.com|(?:[0-9]+\+)?"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?(?:\[bot\])?"
    r"@users\.noreply\.github\.com)$",
    re.IGNORECASE,
)
EXAMPLE_EMAIL_PATTERN = re.compile(
    r"^[^@\s]+@(?:(?:[^@\s.]+\.)*example\.(?:com|net|org)|example|"
    r"(?:[^@\s.]+\.)*(?:test|invalid|localhost))$",
    re.IGNORECASE,
)
PUBLIC_SSH_MACHINE_ACCOUNTS = frozenset({
    "git" + "@bitbucket.org",
    "git" + "@github.com",
    "git" + "@gitlab.com",
    "git" + "@ssh.github.com",
})
PUBLIC_SERVICE_EMAILS = frozenset({
    "support" + "@github.com",
})
MACOS_HOME_PATTERN = re.compile(
    r"(?<![A-Za-z0-9.\]])/" + r"Users" + r"/[A-Za-z0-9._-]+"
    r"(?:/|(?=$)|(?=[\s\"'`),;:\]}]))",
    re.IGNORECASE,
)
LINUX_HOME_PATTERN = re.compile(
    r"(?<![A-Za-z0-9.\]])/" + r"home" + r"/[A-Za-z0-9._-]+"
    r"(?:/|(?=$)|(?=[\s\"'`),;:\]}]))"
)
WINDOWS_HOME_PATTERN = re.compile(
    r"\b[A-Za-z]:[\\/]" + r"Users" + r"[\\/][^\\/\s]+"
    r"(?:[\\/]|(?=$)|(?=[\s\"'`),;:\]}]))",
    re.IGNORECASE,
)
URL_USERINFO_PATTERN = re.compile(
    r"\b[a-z][a-z0-9+.-]*://[^/@\s:]+:[^/@\s]+@",
    re.IGNORECASE,
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


def is_allowed_public_email(value: str) -> bool:
    return bool(
        GITHUB_NOREPLY_PATTERN.fullmatch(value)
        or EXAMPLE_EMAIL_PATTERN.fullmatch(value)
    )


def is_allowed_public_text_email(value: str) -> bool:
    return bool(
        is_allowed_public_email(value)
        or value.casefold() in PUBLIC_SERVICE_EMAILS
    )


def find_private_identifier(text: str) -> str | None:
    if MACOS_HOME_PATTERN.search(text):
        return "macos_home_path"
    if LINUX_HOME_PATTERN.search(text):
        return "linux_home_path"
    if WINDOWS_HOME_PATTERN.search(text):
        return "windows_home_path"
    if URL_USERINFO_PATTERN.search(text):
        return "url_userinfo"
    for match in EMAIL_PATTERN.finditer(text):
        email = match.group(0)
        if (
            email.casefold() in PUBLIC_SSH_MACHINE_ACCOUNTS
            and text[match.end():match.end() + 1] == ":"
        ):
            continue
        if not is_allowed_public_text_email(email):
            return "private_email"
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
        "/" + "Users/example",
        "/" + "home/example/private",
        "/" + "home/example",
        "C:" + "\\Users\\example\\private",
        "C:" + "\\Users\\example",
        "https://private-user:private-pass" + "@example.com/path",
        "private.person" + "@gmail.com",
        "private.person" + "@example.xn--p1ai",
        "git" + "@github.com",
        "019f0000" + "-abcd-7def-8abc-0123456789ab",
        "codex-" + "local-tools",
    )
    if any(find_private_identifier(value) is None for value in private_values):
        raise ValueError("private_identifier_scanner_self_test_failed")
    public_values = (
        "259367310+jacob101519" + "@users.noreply.github.com",
        "noreply" + "@github.com",
        "support" + "@github.com",
        "maintainer" + "@example.com",
        "private.person" + "@localhost",
        "private.person" + "@sample.test",
        "private.person" + "@mail.example.com",
        "private.person" + "@bar.invalid",
        "git" + "@github.com:jacob101519/example.git",
        "git" + "@ssh.github.com:443/jacob101519/example.git",
        "https://example.com/home/alice",
        "https://example.com./home/alice",
        "https://[::1]/Users/alice",
        "auto-route-for-codex" + "@jacob101519",
    )
    if any(find_private_identifier(value) is not None for value in public_values):
        raise ValueError("public_email_allowlist_self_test_failed")
