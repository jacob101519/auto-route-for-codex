#!/usr/bin/env python3
"""Verify the public repository without network access or external writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

from public_hygiene import (
    PACKAGE_ALLOWLIST,
    assert_scanner_self_test,
    find_private_identifier,
    find_secret,
    is_allowed_public_email,
)


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.0-alpha.2"
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
    ".gitignore",
    ".agents/plugins/marketplace.json",
    ".codex-plugin/plugin.json",
    ".github/CODEOWNERS",
    ".github/dependabot.yml",
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
    ".github/requirements-ci.in",
    ".github/requirements-ci.txt",
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
    "CHANGELOG.md",
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "NOTICE",
    "PRIVACY.md",
    "README.md",
    "ROADMAP.md",
    "SECURITY.md",
    "SUPPORT.md",
    "assets/icon.svg",
    "docs/i18n/README.md",
    "scripts/build_release.py",
    "scripts/public_hygiene.py",
    "scripts/tests/test_release_pipeline.py",
    "scripts/verify_public_repo.py",
    "skills/auto-route-for-codex/SKILL.md",
    "skills/auto-route-for-codex/agents/openai.yaml",
    "skills/auto-route-for-codex/schemas/router-input.schema.json",
    "skills/auto-route-for-codex/schemas/router-output.schema.json",
    "skills/auto-route-for-codex/schemas/transfer-receipt.schema.json",
    "skills/auto-route-for-codex/schemas/transfer-reservation.schema.json",
    "skills/auto-route-for-codex/scripts/route_task.py",
    "skills/auto-route-for-codex/scripts/read_current_setting.py",
    "skills/auto-route-for-codex/scripts/transfer_state.py",
    "skills/auto-route-for-codex/scripts/validate_contracts.py",
    "skills/auto-route-for-codex/tests/fixtures/cases.json",
    "skills/auto-route-for-codex/tests/test_route_task.py",
    "skills/auto-route-for-codex/tests/test_read_current_setting.py",
    "skills/auto-route-for-codex/tests/test_transfer_state.py",
    *(source for source, _ in TRANSLATIONS),
    *(translation for _, translation in TRANSLATIONS),
}
MARKDOWN_LINK = re.compile(r"!?\[[^]]*]\(([^)]+)\)")
GITHUB_NOREPLY_IDENTITY = re.compile(
    r"^(?:[0-9]+\+)?(?P<handle>"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?(?:\[bot\])?"
    r")@users\.noreply\.github\.com$",
    re.IGNORECASE,
)
SAFE_IDENTITY_HANDLE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,62}[A-Za-z0-9])?$")
IGNORED_PARTS = {".git", "__pycache__"}


def fail(reason: str) -> None:
    raise SystemExit(f"public repository verification failed: {reason}")


def run_git(arguments: list[str], input_data: bytes | None = None) -> bytes:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            input=input_data,
            check=False,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        fail(f"git_command_unavailable:{arguments[0]}")
    if result.returncode != 0:
        fail(f"git_command_failed:{arguments[0]}")
    return result.stdout


def read_json(relative: str) -> object:
    try:
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid_json:{relative}:{exc.__class__.__name__}")


def privacy_issue_in_bytes(data: bytes) -> tuple[str, str] | None:
    if b"\x00" in data:
        return "encoding", "nul_byte"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "encoding", "non_utf8"
    private_kind = find_private_identifier(text)
    if private_kind:
        return "private_identifier", private_kind
    secret_kind = find_secret(text)
    if secret_kind:
        return "secret", secret_kind
    return None


def git_identity_is_public(name: str, email: str) -> bool:
    if not is_allowed_public_email(email):
        return False
    if email.casefold() == "noreply@github.com":
        return name == "GitHub"
    match = GITHUB_NOREPLY_IDENTITY.fullmatch(email)
    if match:
        return name.casefold() == match.group("handle").casefold()
    local_part = email.partition("@")[0]
    return bool(SAFE_IDENTITY_HANDLE.fullmatch(name) and name.casefold() == local_part.casefold())


def observed_files() -> dict[str, Path]:
    observed: dict[str, Path] = {}
    for path in sorted(ROOT.rglob("*")):
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
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        if path.is_file():
            observed[relative.as_posix()] = path
    missing = sorted(REQUIRED_FILES - set(observed))
    if missing:
        fail("missing_required_files:" + ",".join(missing))
    package_observed = {
        relative
        for relative in observed
        if relative in {"LICENSE", "NOTICE"}
        or relative.startswith((".codex-plugin/", "assets/", "skills/"))
    }
    missing_package = sorted(PACKAGE_ALLOWLIST - package_observed)
    unexpected_package = sorted(package_observed - PACKAGE_ALLOWLIST)
    if missing_package:
        fail("missing_package_file:" + ",".join(missing_package))
    if unexpected_package:
        fail("unexpected_package_file:" + ",".join(unexpected_package))
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
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## [{VERSION}] - 2026-07-20" not in changelog:
        fail("changelog_release_date")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    if f"version: {VERSION}" not in citation or "date-released: 2026-07-20" not in citation:
        fail("citation_release_metadata")
    dependabot = yaml.safe_load(
        (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    )
    if dependabot != {
        "version": 2,
        "updates": [
            {
                "package-ecosystem": "pip",
                "directory": "/.github",
                "schedule": {"interval": "weekly"},
                "groups": {"python-ci": {"patterns": ["*"]}},
            },
            {
                "package-ecosystem": "github-actions",
                "directory": "/",
                "schedule": {"interval": "weekly"},
                "groups": {"actions": {"patterns": ["*"]}},
            },
        ],
    }:
        fail("dependabot_configuration")
    issue_templates = (
        ".github/ISSUE_TEMPLATE/bug_report_en.yml",
        ".github/ISSUE_TEMPLATE/bug_report_zh-CN.yml",
        ".github/ISSUE_TEMPLATE/routing_mismatch_en.yml",
        ".github/ISSUE_TEMPLATE/routing_mismatch_zh-CN.yml",
    )
    for relative in issue_templates:
        template = (ROOT / relative).read_text(encoding="utf-8")
        if VERSION not in template or "0.5.0-alpha.1" in template:
            fail(f"issue_template_version:{relative}")
    workflow_expectations = {
        ".github/workflows/ci.yml": (
            "actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd",
            "actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405",
            "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
        ),
        ".github/workflows/release.yml": (
            "actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd",
            "actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405",
            "actions/attest@f7c74d28b9d84cb8768d0b8ca14a4bac6ef463e6",
            "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
            "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c",
            "actions/github-script@3a2844b7e9c422d3c10d287c895573f7108da1b3",
        ),
    }
    workflow_documents: dict[str, dict[object, object]] = {}
    for relative, pinned_actions in workflow_expectations.items():
        workflow = (ROOT / relative).read_text(encoding="utf-8")
        try:
            workflow_document = yaml.safe_load(workflow)
        except yaml.YAMLError:
            fail(f"workflow_yaml:{relative}")
        if not isinstance(workflow_document, dict):
            fail(f"workflow_document:{relative}")
        workflow_documents[relative] = workflow_document
        observed_actions: list[str] = []
        visited: set[int] = set()

        def collect_uses(value: object) -> None:
            if isinstance(value, (dict, list)):
                identity = id(value)
                if identity in visited:
                    return
                visited.add(identity)
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == "uses":
                        if not isinstance(child, str):
                            fail(f"workflow_action_set_or_pin:{relative}")
                        observed_actions.append(child)
                    collect_uses(child)
            elif isinstance(value, list):
                for child in value:
                    collect_uses(child)

        collect_uses(workflow_document)
        if tuple(observed_actions) != pinned_actions:
            fail(f"workflow_action_set_or_pin:{relative}")

    def workflow_trigger(document: dict[object, object]) -> object:
        # PyYAML follows YAML 1.1 and parses the GitHub Actions `on` key as True.
        return document.get("on", document.get(True))

    def named_steps(job: dict[object, object], reason: str) -> dict[str, dict[object, object]]:
        raw_steps = job.get("steps")
        if not isinstance(raw_steps, list):
            fail(reason)
        result: dict[str, dict[object, object]] = {}
        for step in raw_steps:
            if not isinstance(step, dict) or not isinstance(step.get("name"), str):
                fail(reason)
            name = step["name"]
            if name in result:
                fail(reason)
            result[name] = step
        return result

    def require_run(
        steps: dict[str, dict[object, object]],
        name: str,
        expected: str,
        reason: str,
    ) -> None:
        step = steps.get(name)
        if not isinstance(step, dict) or step.get("run") != expected:
            fail(reason)

    def require_step_layout(
        steps: dict[str, dict[object, object]],
        expected: tuple[tuple[str, frozenset[str]], ...],
        reason: str,
    ) -> None:
        if tuple(steps) != tuple(name for name, _ in expected):
            fail(reason)
        for name, keys in expected:
            if set(steps[name]) != keys:
                fail(reason)

    def require_sha256(
        value: object,
        expected: str,
        reason: str,
    ) -> None:
        if not isinstance(value, str):
            fail(reason)
        if hashlib.sha256(value.encode("utf-8")).hexdigest() != expected:
            fail(reason)

    def secret_references(value: object) -> list[str]:
        if isinstance(value, str):
            if "secrets." in value or "secrets[" in value:
                return [value]
            return []
        if isinstance(value, dict):
            result: list[str] = []
            for key, child in value.items():
                result.extend(secret_references(key))
                result.extend(secret_references(child))
            return result
        if isinstance(value, list):
            result = []
            for child in value:
                result.extend(secret_references(child))
            return result
        return []

    if secret_references(workflow_documents[".github/workflows/ci.yml"]):
        fail("workflow_secret_reference:.github/workflows/ci.yml")
    if secret_references(workflow_documents[".github/workflows/release.yml"]) != [
        "${{ secrets.RELEASE_SETTINGS_READ_TOKEN }}",
    ]:
        fail("workflow_secret_reference:.github/workflows/release.yml")

    ci_relative = ".github/workflows/ci.yml"
    ci_document = workflow_documents[ci_relative]
    if set(ci_document) != {"name", True, "permissions", "jobs"}:
        fail("ci_security_controls")
    if workflow_trigger(ci_document) != {
        "push": {"branches": ["main"]},
        "pull_request": None,
        "workflow_dispatch": None,
    }:
        fail("ci_triggers")
    if ci_document.get("permissions") != {"contents": "read"}:
        fail("ci_permissions")
    ci_jobs = ci_document.get("jobs")
    if not isinstance(ci_jobs, dict) or set(ci_jobs) != {"verify"}:
        fail("ci_security_controls")
    ci_job = ci_jobs.get("verify")
    if not isinstance(ci_job, dict):
        fail("ci_security_controls")
    if (
        set(ci_job) != {"runs-on", "timeout-minutes", "env", "steps"}
        or
        ci_job.get("runs-on") != "ubuntu-24.04"
        or ci_job.get("timeout-minutes") != 15
        or ci_job.get("env") != {"PYTHONDONTWRITEBYTECODE": "1"}
        or "permissions" in ci_job
    ):
        fail("ci_security_controls")
    ci_steps = named_steps(ci_job, "ci_security_controls")
    require_step_layout(
        ci_steps,
        (
            ("Check out repository", frozenset({"name", "uses", "with"})),
            ("Set up Python", frozenset({"name", "uses", "with"})),
            ("Install validator dependencies", frozenset({"name", "run"})),
            ("Fetch pinned official validators", frozenset({"name", "run"})),
            ("Run official Skill validator", frozenset({"name", "run"})),
            ("Run official Plugin validator", frozenset({"name", "run"})),
            ("Verify public repository", frozenset({"name", "run"})),
            ("Run release-pipeline security tests", frozenset({"name", "run"})),
            ("Run router unit tests", frozenset({"name", "run"})),
            ("Validate router contracts", frozenset({"name", "run"})),
            ("Build deterministic release artifacts", frozenset({"name", "run"})),
            ("Upload release candidates", frozenset({"name", "uses", "with"})),
        ),
        "ci_security_controls",
    )
    ci_checkout = ci_steps.get("Check out repository")
    if not isinstance(ci_checkout, dict) or ci_checkout.get("with") != {
        "persist-credentials": False,
        "fetch-depth": 0,
    }:
        fail("ci_security_controls")
    ci_python = ci_steps.get("Set up Python")
    if not isinstance(ci_python, dict) or ci_python.get("with") != {
        "python-version": "3.12",
    }:
        fail("ci_security_controls")
    require_run(
        ci_steps,
        "Install validator dependencies",
        "python3 -m pip install --disable-pip-version-check --only-binary=:all: "
        "--require-hashes -r .github/requirements-ci.txt",
        "ci_security_controls",
    )
    require_sha256(
        ci_steps["Fetch pinned official validators"].get("run"),
        "38f8393943699e8e17ec24560fd59a6996f619ae0bec972b77fdb73903d27e44",
        "ci_security_controls",
    )
    ci_exact_runs = {
        "Run official Skill validator": (
            "python3 /tmp/openai-quick-validate.py skills/auto-route-for-codex"
        ),
        "Run official Plugin validator": "python3 /tmp/openai-validate-plugin.py .",
        "Verify public repository": (
            "python3 scripts/verify_public_repo.py --require-git-history"
        ),
        "Run release-pipeline security tests": (
            "python3 -m unittest discover -s scripts/tests -v"
        ),
        "Run router unit tests": (
            "python3 -m unittest discover -s skills/auto-route-for-codex/tests -v"
        ),
        "Validate router contracts": (
            "python3 skills/auto-route-for-codex/scripts/validate_contracts.py"
        ),
        "Build deterministic release artifacts": (
            "python3 scripts/build_release.py --output-dir dist"
        ),
    }
    for name, command in ci_exact_runs.items():
        require_run(ci_steps, name, command, "ci_security_controls")
    ci_upload = ci_steps.get("Upload release candidates")
    if not isinstance(ci_upload, dict) or ci_upload.get("with") != {
        "name": "auto-route-for-codex-${{ github.sha }}",
        "path": f"dist/auto-route-for-codex-{VERSION}.zip\ndist/SHA256SUMS\n",
        "if-no-files-found": "error",
    }:
        fail("ci_security_controls")

    release_relative = ".github/workflows/release.yml"
    release_document = workflow_documents[release_relative]
    if set(release_document) != {"name", True, "concurrency", "jobs"}:
        fail("release_workflow_security_controls")
    if workflow_trigger(release_document) != {"push": {"tags": ["v*"]}}:
        fail("release_triggers")
    if "permissions" in release_document:
        fail("release_workflow_permissions")
    release_jobs = release_document.get("jobs")
    if not isinstance(release_jobs, dict) or set(release_jobs) != {"build", "publish"}:
        fail("release_workflow_jobs")
    build_job = release_jobs.get("build")
    publish_job = release_jobs.get("publish")
    if not isinstance(build_job, dict) or not isinstance(publish_job, dict):
        fail("release_workflow_jobs")
    if build_job.get("permissions") != {
        "contents": "read",
        "id-token": "write",
        "attestations": "write",
    }:
        fail("release_build_permissions")
    if publish_job.get("permissions") != {
        "actions": "read",
        "contents": "write",
    }:
        fail("release_publish_permissions")
    if (
        set(build_job) != {"runs-on", "timeout-minutes", "permissions", "env", "steps"}
        or set(publish_job) != {"needs", "runs-on", "timeout-minutes", "permissions", "steps"}
        or
        build_job.get("runs-on") != "ubuntu-24.04"
        or build_job.get("timeout-minutes") != 20
        or build_job.get("env") != {"PYTHONDONTWRITEBYTECODE": "1"}
        or publish_job.get("needs") != "build"
        or publish_job.get("runs-on") != "ubuntu-24.04"
        or publish_job.get("timeout-minutes") != 10
    ):
        fail("release_workflow_security_controls")
    build_steps = named_steps(build_job, "release_workflow_security_controls")
    publish_steps = named_steps(publish_job, "release_workflow_security_controls")
    require_step_layout(
        build_steps,
        (
            ("Check out the tagged source", frozenset({"name", "uses", "with"})),
            ("Verify the tagged commit is in main history", frozenset({"name", "run"})),
            ("Set up Python", frozenset({"name", "uses", "with"})),
            ("Install hash-locked verification dependencies", frozenset({"name", "run"})),
            ("Verify repository and complete reachable history", frozenset({"name", "run"})),
            ("Run release-pipeline security tests", frozenset({"name", "run"})),
            ("Run router unit tests", frozenset({"name", "run"})),
            ("Validate router contracts", frozenset({"name", "run"})),
            ("Build the release twice and compare bytes", frozenset({"name", "env", "run"})),
            ("Attest release payload", frozenset({"name", "uses", "with"})),
            ("Upload the verified release payload", frozenset({"name", "uses", "with"})),
        ),
        "release_workflow_security_controls",
    )
    require_step_layout(
        publish_steps,
        (
            ("Download the verified release payload", frozenset({"name", "uses", "with"})),
            ("Validate the bounded release payload", frozenset({"name", "env", "run"})),
            ("Publish exactly one immutable release", frozenset({"name", "uses", "env", "with"})),
        ),
        "release_workflow_security_controls",
    )
    release_checkout = build_steps.get("Check out the tagged source")
    if not isinstance(release_checkout, dict) or release_checkout.get("with") != {
        "persist-credentials": False,
        "fetch-depth": 0,
        "fetch-tags": True,
    }:
        fail("release_workflow_security_controls")
    release_python = build_steps.get("Set up Python")
    if not isinstance(release_python, dict) or release_python.get("with") != {
        "python-version": "3.12",
    }:
        fail("release_workflow_security_controls")
    release_ancestry = build_steps.get("Verify the tagged commit is in main history")
    if not isinstance(release_ancestry, dict):
        fail("release_workflow_security_controls")
    require_sha256(
        release_ancestry.get("run"),
        "313762f8e951cb8f13b19101e5e5a8ed1a0157023060cb6231891a57d4d0ff0d",
        "release_workflow_security_controls",
    )
    require_run(
        build_steps,
        "Install hash-locked verification dependencies",
        "python3 -m pip install --disable-pip-version-check --only-binary=:all: "
        "--require-hashes -r .github/requirements-ci.txt",
        "release_workflow_security_controls",
    )
    require_run(
        build_steps,
        "Verify repository and complete reachable history",
        "python3 scripts/verify_public_repo.py --require-git-history",
        "release_workflow_security_controls",
    )
    release_exact_runs = {
        "Run release-pipeline security tests": (
            "python3 -m unittest discover -s scripts/tests -v"
        ),
        "Run router unit tests": (
            "python3 -m unittest discover -s skills/auto-route-for-codex/tests -v"
        ),
        "Validate router contracts": (
            "python3 skills/auto-route-for-codex/scripts/validate_contracts.py"
        ),
    }
    for name, command in release_exact_runs.items():
        require_run(build_steps, name, command, "release_workflow_security_controls")
    release_build = build_steps.get("Build the release twice and compare bytes")
    if not isinstance(release_build, dict) or release_build.get("env") != {
        "RELEASE_TAG": "${{ github.ref_name }}",
    }:
        fail("release_workflow_security_controls")
    require_sha256(
        release_build.get("run"),
        "04000be01f9814a92112d6d78bb131a3d3d2c8294f56f695e970f41ee6991984",
        "release_workflow_security_controls",
    )
    release_attest = build_steps.get("Attest release payload")
    if not isinstance(release_attest, dict) or release_attest.get("with") != {
        "subject-path": (
            "${{ runner.temp }}/release-a/*.zip\n"
            "${{ runner.temp }}/release-a/SHA256SUMS\n"
        ),
    }:
        fail("release_workflow_security_controls")
    release_upload = build_steps.get("Upload the verified release payload")
    if not isinstance(release_upload, dict) or release_upload.get("with") != {
        "name": "release-${{ github.run_id }}-${{ github.run_attempt }}",
        "path": (
            "${{ runner.temp }}/release-a/*.zip\n"
            "${{ runner.temp }}/release-a/SHA256SUMS\n"
        ),
        "if-no-files-found": "error",
        "retention-days": 1,
        "compression-level": 0,
        "include-hidden-files": False,
    }:
        fail("release_workflow_security_controls")
    release_download = publish_steps.get("Download the verified release payload")
    if not isinstance(release_download, dict) or release_download.get("with") != {
        "name": "release-${{ github.run_id }}-${{ github.run_attempt }}",
        "path": "${{ runner.temp }}/release",
        "digest-mismatch": "error",
    }:
        fail("release_workflow_security_controls")
    release_validate = publish_steps.get("Validate the bounded release payload")
    if not isinstance(release_validate, dict) or release_validate.get("env") != {
        "RELEASE_TAG": "${{ github.ref_name }}",
    }:
        fail("release_workflow_security_controls")
    require_sha256(
        release_validate.get("run"),
        "6fac5466f9b7064231269ee82d966e8bcb36f08e828777dfb3713702cbd0387f",
        "release_workflow_security_controls",
    )
    release_publish = publish_steps.get("Publish exactly one immutable release")
    if (
        not isinstance(release_publish, dict)
        or release_publish.get("env") != {
            "RELEASE_TAG": "${{ github.ref_name }}",
            "TAG_COMMIT": "${{ github.sha }}",
            "ASSET_DIR": "${{ runner.temp }}/release",
            "RELEASE_SETTINGS_READ_TOKEN": "${{ secrets.RELEASE_SETTINGS_READ_TOKEN }}",
        }
        or not isinstance(release_publish.get("with"), dict)
        or release_publish["with"].get("retries") != 3
    ):
        fail("release_workflow_security_controls")
    require_sha256(
        release_publish["with"].get("script"),
        "ccf7a1635f89580945d01ea05f93dc9e9fb0372a72bbc7c257b28d1796a915c8",
        "release_workflow_security_controls",
    )


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
            "source_revision": "docs-v0.5.0-alpha.2",
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
        "codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.5.0-alpha.2",
        "codex plugin add auto-route-for-codex@jacob101519",
        "$auto-route-for-codex",
        "v0.5.0-alpha.2",
        "fork_created",
        "navigation_confirmed",
        "source_archive_confirmed",
        "pending_reservation",
        "reservation_lease",
        "--reservation-lease",
        "$CODEX_HOME/state/auto-route-for-codex",
        "AUTO_ROUTE_STATE_HOME",
        "host_capabilities.source_task_context=true",
        "CODEX_THREAD_ID",
        "source_binding_sha256",
        "fsync",
        "recommendation-only",
        ".codex-plugin/plugin.json",
        ".agents/plugins/marketplace.json",
        "skills/auto-route-for-codex/",
        "docs/i18n/zh-CN/",
        "scripts/verify_public_repo.py",
        "scripts/build_release.py",
        "SHA256SUMS",
    )
    forbidden_text = (
        "never forks, creates, navigates, archives, or replays a task",
        "public edition is deliberately recommendation-only",
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
        folded = text.casefold()
        for forbidden in forbidden_text:
            if forbidden in folded:
                fail(f"obsolete_recommendation_only_claim:{current}")


def verify_transfer_disclosure() -> None:
    disclosure_files = (
        "README.md",
        "PRIVACY.md",
        "docs/architecture.md",
        "docs/privacy-and-data-flow.md",
        "skills/auto-route-for-codex/SKILL.md",
    )
    required = (
        "ephemeral coordination nonce",
        "private local CLI",
        "not a credential",
        "unsupported internals",
        "stale evidence",
        "host_capabilities.source_task_context=true",
        "CODEX_THREAD_ID",
        "source_binding_sha256",
        "raw source identifier",
    )
    for relative in disclosure_files:
        text = (ROOT / relative).read_text(encoding="utf-8")
        if any(token not in text for token in required):
            fail(f"incomplete_transfer_disclosure:{relative}")
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    forbidden = (
        "raw `reservation_lease` into the plugin package, repository, logs, telemetry, or user-facing output",
        "raw `reservation_lease` in package, repository, telemetry, logs, or user-facing output",
    )
    if any(value in skill for value in forbidden):
        fail("obsolete_lease_nonvisibility_claim")


def verify_privacy(files: dict[str, Path]) -> int:
    scanned = 0
    for relative, path in files.items():
        private_kind = find_private_identifier("/" + relative)
        if private_kind:
            fail(f"private_path:{relative}:{private_kind}")
        secret_kind = find_secret(relative)
        if secret_kind:
            fail(f"secret_path:{relative}:{secret_kind}")
        issue = privacy_issue_in_bytes(path.read_bytes())
        if issue:
            category, kind = issue
            if category == "encoding":
                fail(f"non_utf8_source:{relative}:{kind}")
            fail(f"{category}:{relative}:{kind}")
        scanned += 1
    return scanned


def verify_git_history(required: bool) -> dict[str, int | bool]:
    if not (ROOT / ".git").exists():
        if required:
            fail("git_history_required")
        return {
            "available": False,
            "commits_scanned": 0,
            "tags_scanned": 0,
            "objects_scanned": 0,
            "blobs_scanned": 0,
            "paths_scanned": 0,
        }
    if run_git(["rev-parse", "--is-inside-work-tree"]).strip() != b"true":
        fail("git_worktree_required")
    if run_git(["rev-parse", "--is-shallow-repository"]).strip() != b"false":
        fail("git_history_shallow")

    commit_count = 0
    try:
        raw_commits = run_git([
            "log",
            "--all",
            "--format=%H%x00%an%x00%ae%x00%cn%x00%ce%x00%B%x1e",
        ]).decode("utf-8")
    except UnicodeDecodeError:
        fail("git_commit_metadata_non_utf8")
    for record in raw_commits.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        fields = record.split("\x00", 5)
        if len(fields) != 6:
            fail("git_commit_metadata_format")
        commit_id, author_name, author_email, committer_name, committer_email, message = fields
        for role, name, email in (
            ("author", author_name, author_email),
            ("committer", committer_name, committer_email),
        ):
            if not git_identity_is_public(name, email):
                private_kind = find_private_identifier(email) or "identity_not_public"
                fail(f"git_commit_{role}:{commit_id}:{private_kind}")
        private_kind = find_private_identifier(message)
        if private_kind:
            fail(f"git_commit_message:{commit_id}:{private_kind}")
        secret_kind = find_secret(message)
        if secret_kind:
            fail(f"git_commit_message:{commit_id}:{secret_kind}")
        commit_count += 1

    tag_count = 0
    try:
        raw_tags = run_git([
            "for-each-ref",
            "refs/tags",
            "--format=%(refname)%00%(taggername)%00%(taggeremail)%00%(contents)%1e",
        ]).decode("utf-8")
    except UnicodeDecodeError:
        fail("git_tag_metadata_non_utf8")
    for record in raw_tags.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        fields = record.split("\x00", 3)
        if len(fields) != 4:
            fail("git_tag_metadata_format")
        refname, tagger_name, raw_email, message = fields
        email = raw_email.strip().strip("<>")
        if email or tagger_name:
            if not git_identity_is_public(tagger_name, email):
                private_kind = find_private_identifier(email) or "identity_not_public"
                fail(f"git_tag_tagger:{refname}:{private_kind}")
        private_kind = find_private_identifier(message)
        if private_kind:
            fail(f"git_tag_message:{refname}:{private_kind}")
        secret_kind = find_secret(message)
        if secret_kind:
            fail(f"git_tag_message:{refname}:{secret_kind}")
        tag_count += 1

    historical_paths: set[bytes] = set()
    tree_ids = set(run_git(["log", "--all", "--format=%T"]).splitlines())
    for raw_tree_id in tree_ids:
        try:
            tree_id = raw_tree_id.decode("ascii")
        except UnicodeDecodeError:
            fail("git_tree_id_format")
        raw_tree = run_git(["ls-tree", "-r", "-z", "--full-tree", tree_id])
        for record in raw_tree.split(b"\x00"):
            if not record:
                continue
            _, separator, raw_path = record.partition(b"\t")
            if not separator or not raw_path:
                fail("git_tree_path_format")
            historical_paths.add(raw_path)
    for raw_path in historical_paths:
        issue = privacy_issue_in_bytes(b"/" + raw_path)
        if issue:
            category, kind = issue
            fail(f"git_tree_path_{category}:{kind}")

    object_ids: set[str] = set()
    raw_objects = run_git(["rev-list", "--objects", "--all", "--no-object-names"])
    for raw_object_id in raw_objects.splitlines():
        try:
            object_id = raw_object_id.decode("ascii")
        except UnicodeDecodeError:
            fail("git_object_id_format")
        if not re.fullmatch(r"[0-9a-f]{40,64}", object_id):
            fail("git_object_id_format")
        object_ids.add(object_id)
    batch_input = "".join(f"{object_id}\n" for object_id in object_ids).encode("ascii")
    raw_types = run_git(
        ["cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        input_data=batch_input,
    ).decode("ascii")
    blob_count = 0
    for line in raw_types.splitlines():
        fields = line.split()
        if len(fields) != 3:
            fail("git_object_metadata_format")
        object_id, object_type, raw_size = fields
        if object_type != "blob":
            continue
        if int(raw_size) > 5 * 1024 * 1024:
            fail(f"git_blob_too_large:{object_id}")
        issue = privacy_issue_in_bytes(run_git(["cat-file", "blob", object_id]))
        if issue:
            category, kind = issue
            fail(f"git_blob_{category}:{object_id}:{kind}")
        blob_count += 1

    return {
        "available": True,
        "commits_scanned": commit_count,
        "tags_scanned": tag_count,
        "objects_scanned": len(object_ids),
        "blobs_scanned": blob_count,
        "paths_scanned": len(historical_paths),
    }


def verify_package_ascii(files: dict[str, Path]) -> int:
    package_roots = (".codex-plugin/", "assets/", "skills/")
    package_files = {
        "LICENSE",
        "NOTICE",
    }
    checked = 0
    for relative, path in files.items():
        if relative not in package_files and not relative.startswith(package_roots):
            continue
        try:
            path.read_bytes().decode("ascii")
        except UnicodeDecodeError:
            fail(f"non_ascii_package_file:{relative}")
        checked += 1
    return checked


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-git-history", action="store_true")
    args = parser.parse_args()
    try:
        assert_scanner_self_test()
    except ValueError as exc:
        fail(str(exc))
    files = observed_files()
    verify_manifests()
    verify_translations()
    verify_language_navigation()
    verify_transfer_disclosure()
    scanned = verify_privacy(files)
    history = verify_git_history(args.require_git_history)
    package_ascii = verify_package_ascii(files)
    links = verify_markdown_links(files)
    summary = {
        "status": "pass",
        "version": VERSION,
        "files": len(files),
        "privacy_scanned": scanned,
        "git_history": history,
        "package_ascii_files": package_ascii,
        "translation_pairs": len(TRANSLATIONS),
        "readme_locales": len(README_VARIANTS),
        "local_links_checked": links,
        "license_sha256": verify_license(),
    }
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
