from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[2]


class ReleasePipelineSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "repository"
        shutil.copytree(
            SOURCE_ROOT,
            self.root,
            ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "*.pyc"),
        )
        self.environment = dict(os.environ)
        self.environment["PYTHONDONTWRITEBYTECODE"] = "1"

    def run_script(self, relative: str, *arguments: str) -> subprocess.CompletedProcess[str]:
        return self.run_script_in(self.root, relative, *arguments)

    def run_script_in(
        self,
        root: Path,
        relative: str,
        *arguments: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", relative, *arguments],
            cwd=root,
            env=self.environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def git(self, *arguments: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=cwd or self.root,
            env=self.environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def initialize_git(self, email: str | None = None, name: str = "security-fixture") -> None:
        self.git("init", "-b", "main")
        self.git("config", "user.name", name)
        self.git(
            "config",
            "user.email",
            email or ("123456+security-fixture" + "@users.noreply.github.com"),
        )
        self.git("config", "commit.gpgsign", "false")
        self.git("add", ".")
        self.git("commit", "-m", "Create security fixture")
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")

    def release_tag(self) -> str:
        manifest = json.loads(
            (self.root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        return "v" + manifest["version"]

    def test_dist_symlink_is_rejected_before_ignore(self) -> None:
        target = Path(self.temporary.name) / "outside-dist"
        target.mkdir()
        (self.root / "dist").symlink_to(target, target_is_directory=True)

        verified = self.run_script("scripts/verify_public_repo.py")
        built = self.run_script("scripts/build_release.py", "--output-dir", "dist")

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("symlink:dist", verified.stderr + verified.stdout)
        self.assertNotEqual(built.returncode, 0)
        self.assertIn("symlink:dist", built.stderr + built.stdout)
        self.assertEqual(list(target.iterdir()), [])

    def test_symlinked_external_output_directory_is_rejected(self) -> None:
        target = Path(self.temporary.name) / "outside-output"
        target.mkdir()
        link = Path(self.temporary.name) / "output-link"
        link.symlink_to(target, target_is_directory=True)

        built = self.run_script("scripts/build_release.py", "--output-dir", str(link))

        self.assertNotEqual(built.returncode, 0)
        self.assertIn("symlink_output_dir", built.stderr + built.stdout)
        self.assertEqual(list(target.iterdir()), [])

    def test_intermediate_symlinked_output_directory_is_rejected(self) -> None:
        target = Path(self.temporary.name) / "outside-intermediate"
        target.mkdir()
        base = Path(self.temporary.name) / "output-base"
        base.mkdir()
        (base / "link").symlink_to(target, target_is_directory=True)

        built = self.run_script(
            "scripts/build_release.py",
            "--output-dir",
            str(base / "link" / "nested"),
        )

        self.assertNotEqual(built.returncode, 0)
        self.assertIn("symlink_output_dir", built.stderr + built.stdout)
        self.assertEqual(list(target.iterdir()), [])

    def test_private_manifest_filename_is_rejected_at_any_depth(self) -> None:
        (self.root / "docs" / "snapshot-manifest.json").write_text("{}\n", encoding="ascii")

        verified = self.run_script("scripts/verify_public_repo.py")
        built = self.run_script(
            "scripts/build_release.py",
            "--output-dir",
            str(Path(self.temporary.name) / "release"),
        )

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("private_export_manifest_must_not_be_published", verified.stderr + verified.stdout)
        self.assertNotEqual(built.returncode, 0)
        self.assertIn("private_export_manifest_must_not_be_published", built.stderr + built.stdout)

    def test_github_token_family_is_rejected_by_verify_and_build(self) -> None:
        skill = self.root / "skills" / "auto-route-for-codex" / "SKILL.md"
        original = skill.read_text(encoding="ascii")
        for prefix in ("gho_", "ghp_", "ghr_", "ghs_", "ghu_"):
            with self.subTest(prefix=prefix):
                skill.write_text(original + "\n" + prefix + "SyntheticValue1234567890\n", encoding="ascii")
                verified = self.run_script("scripts/verify_public_repo.py")
                built = self.run_script(
                    "scripts/build_release.py",
                    "--output-dir",
                    str(Path(self.temporary.name) / ("release-" + prefix[:3])),
                )
                self.assertNotEqual(verified.returncode, 0)
                self.assertIn("provider_token", verified.stderr + verified.stdout)
                self.assertNotEqual(built.returncode, 0)
                self.assertIn("provider_token", built.stderr + built.stdout)
        skill.write_text(original, encoding="ascii")

    def test_quoted_json_secret_is_rejected_by_verify_and_build(self) -> None:
        skill = self.root / "skills" / "auto-route-for-codex" / "SKILL.md"
        original = skill.read_text(encoding="ascii")
        skill.write_text(
            original + '\n{"to' + 'ken":"syntheticvalue1234567890"}\n',
            encoding="ascii",
        )

        verified = self.run_script("scripts/verify_public_repo.py")
        built = self.run_script(
            "scripts/build_release.py",
            "--output-dir",
            str(Path(self.temporary.name) / "quoted-secret-release"),
        )

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("generic_secret_assignment", verified.stderr + verified.stdout)
        self.assertNotEqual(built.returncode, 0)
        self.assertIn("generic_secret_assignment", built.stderr + built.stdout)

    def test_private_email_is_rejected_by_verify_and_build(self) -> None:
        skill = self.root / "skills" / "auto-route-for-codex" / "SKILL.md"
        original = skill.read_text(encoding="ascii")
        skill.write_text(
            original + "\n" + "private.person" + "@gmail.com\n",
            encoding="ascii",
        )

        verified = self.run_script("scripts/verify_public_repo.py")
        built = self.run_script(
            "scripts/build_release.py",
            "--output-dir",
            str(Path(self.temporary.name) / "private-email-release"),
        )

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("private_email", verified.stderr + verified.stdout)
        self.assertNotEqual(built.returncode, 0)
        self.assertIn("private_email", built.stderr + built.stdout)

    def test_private_current_filename_is_rejected(self) -> None:
        private_path = self.root / ("private.person" + "@gmail.com.txt")
        private_path.write_text("synthetic public content\n", encoding="ascii")

        verified = self.run_script("scripts/verify_public_repo.py")

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("private_path", verified.stderr + verified.stdout)
        self.assertIn("private_email", verified.stderr + verified.stdout)

    def test_private_commit_email_is_rejected(self) -> None:
        self.initialize_git("private.person" + "@gmail.com")

        verified = self.run_script(
            "scripts/verify_public_repo.py",
            "--require-git-history",
        )

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("git_commit_author", verified.stderr + verified.stdout)
        self.assertIn("private_email", verified.stderr + verified.stdout)

    def test_deleted_private_history_blob_is_rejected(self) -> None:
        self.initialize_git()
        retired = self.root / "retired-private-data.txt"
        retired.write_text("private.person" + "@gmail.com\n", encoding="ascii")
        self.git("add", "retired-private-data.txt")
        self.git("commit", "-m", "Add retired test data")
        retired.unlink()
        self.git("add", "retired-private-data.txt")
        self.git("commit", "-m", "Remove retired test data")

        verified = self.run_script(
            "scripts/verify_public_repo.py",
            "--require-git-history",
        )

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("git_blob_private_identifier", verified.stderr + verified.stdout)
        self.assertIn("private_email", verified.stderr + verified.stdout)

    def test_deleted_private_history_filename_is_rejected(self) -> None:
        self.initialize_git()
        retired = self.root / ("private.person" + "@gmail.com.txt")
        retired.write_text("synthetic public content\n", encoding="ascii")
        self.git("add", retired.name)
        self.git("commit", "-m", "Add retired filename fixture")
        retired.unlink()
        self.git("add", retired.name)
        self.git("commit", "-m", "Remove retired filename fixture")

        verified = self.run_script(
            "scripts/verify_public_repo.py",
            "--require-git-history",
        )

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("git_tree_path_private_identifier", verified.stderr + verified.stdout)
        self.assertIn("private_email", verified.stderr + verified.stdout)

    def test_deleted_utf16_history_blob_is_rejected(self) -> None:
        self.initialize_git()
        retired = self.root / "retired-utf16-data.bin"
        retired.write_bytes(("gh" + "p_SyntheticValue1234567890").encode("utf-16-le"))
        self.git("add", retired.name)
        self.git("commit", "-m", "Add retired UTF-16 fixture")
        retired.unlink()
        self.git("add", retired.name)
        self.git("commit", "-m", "Remove retired UTF-16 fixture")

        verified = self.run_script(
            "scripts/verify_public_repo.py",
            "--require-git-history",
        )

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("git_blob_encoding", verified.stderr + verified.stdout)
        self.assertIn("nul_byte", verified.stderr + verified.stdout)

    def test_deleted_non_utf8_history_blob_is_rejected(self) -> None:
        self.initialize_git()
        retired = self.root / "retired-latin1-data.bin"
        retired.write_bytes(b"caf\xe9\n")
        self.git("add", retired.name)
        self.git("commit", "-m", "Add retired non-UTF-8 fixture")
        retired.unlink()
        self.git("add", retired.name)
        self.git("commit", "-m", "Remove retired non-UTF-8 fixture")

        verified = self.run_script(
            "scripts/verify_public_repo.py",
            "--require-git-history",
        )

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("git_blob_encoding", verified.stderr + verified.stdout)
        self.assertIn("non_utf8", verified.stderr + verified.stdout)

    def test_private_commit_display_name_is_rejected(self) -> None:
        self.initialize_git(name="Private Person")

        verified = self.run_script(
            "scripts/verify_public_repo.py",
            "--require-git-history",
        )

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("git_commit_author", verified.stderr + verified.stdout)
        self.assertIn("identity_not_public", verified.stderr + verified.stdout)

    def test_private_annotated_tag_display_name_is_rejected(self) -> None:
        self.initialize_git()
        self.git("config", "user.name", "Private Person")
        self.git("tag", "-a", "v9.9.9-test", "-m", "Synthetic tag")

        verified = self.run_script(
            "scripts/verify_public_repo.py",
            "--require-git-history",
        )

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("git_tag_tagger", verified.stderr + verified.stdout)
        self.assertIn("identity_not_public", verified.stderr + verified.stdout)

    def test_noreply_commit_metadata_is_accepted(self) -> None:
        self.initialize_git()

        verified = self.run_script(
            "scripts/verify_public_repo.py",
            "--require-git-history",
        )

        self.assertEqual(verified.returncode, 0, verified.stderr + verified.stdout)

    def test_shallow_history_is_rejected(self) -> None:
        self.initialize_git()
        shallow = Path(self.temporary.name) / "shallow"
        self.git(
            "clone",
            "--depth=1",
            self.root.as_uri(),
            str(shallow),
            cwd=Path(self.temporary.name),
        )

        verified = self.run_script_in(
            shallow,
            "scripts/verify_public_repo.py",
            "--require-git-history",
        )

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("git_history_shallow", verified.stderr + verified.stdout)

    def test_expected_annotated_tag_at_clean_head_is_accepted(self) -> None:
        self.initialize_git()
        tag = self.release_tag()
        self.git("tag", "-a", tag, "-m", "Release security fixture")

        built = self.run_script(
            "scripts/build_release.py",
            "--output-dir",
            str(Path(self.temporary.name) / "tagged-release"),
            "--expected-tag",
            tag,
        )

        self.assertEqual(built.returncode, 0, built.stderr + built.stdout)

    def test_expected_tag_version_mismatch_is_rejected(self) -> None:
        self.initialize_git()

        built = self.run_script(
            "scripts/build_release.py",
            "--output-dir",
            str(Path(self.temporary.name) / "wrong-version-release"),
            "--expected-tag",
            "v0.0.0",
        )

        self.assertNotEqual(built.returncode, 0)
        self.assertIn("release_tag_version_mismatch", built.stderr + built.stdout)

    def test_lightweight_release_tag_is_rejected(self) -> None:
        self.initialize_git()
        tag = self.release_tag()
        self.git("tag", tag)

        built = self.run_script(
            "scripts/build_release.py",
            "--output-dir",
            str(Path(self.temporary.name) / "lightweight-release"),
            "--expected-tag",
            tag,
        )

        self.assertNotEqual(built.returncode, 0)
        self.assertIn("release_tag_not_annotated", built.stderr + built.stdout)

    def test_release_tag_not_at_head_is_rejected(self) -> None:
        self.initialize_git()
        tag = self.release_tag()
        self.git("tag", "-a", tag, "-m", "Release security fixture")
        readme = self.root / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-m", "Advance past release tag")

        built = self.run_script(
            "scripts/build_release.py",
            "--output-dir",
            str(Path(self.temporary.name) / "stale-tag-release"),
            "--expected-tag",
            tag,
        )

        self.assertNotEqual(built.returncode, 0)
        self.assertIn("release_tag_not_at_head", built.stderr + built.stdout)

    def test_release_tag_outside_main_history_is_rejected(self) -> None:
        self.initialize_git()
        self.git("switch", "-c", "side-release")
        readme = self.root / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8") + "\nSide release fixture.\n",
            encoding="utf-8",
        )
        self.git("add", "README.md")
        self.git("commit", "-m", "Create side release fixture")
        tag = self.release_tag()
        self.git("tag", "-a", tag, "-m", "Release security fixture")

        built = self.run_script(
            "scripts/build_release.py",
            "--output-dir",
            str(Path(self.temporary.name) / "side-release-output"),
            "--expected-tag",
            tag,
        )

        self.assertNotEqual(built.returncode, 0)
        self.assertIn("release_tag_not_on_main", built.stderr + built.stdout)

    def test_dirty_release_worktree_is_rejected(self) -> None:
        self.initialize_git()
        tag = self.release_tag()
        self.git("tag", "-a", tag, "-m", "Release security fixture")
        readme = self.root / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\n", encoding="utf-8")

        built = self.run_script(
            "scripts/build_release.py",
            "--output-dir",
            str(Path(self.temporary.name) / "dirty-release"),
            "--expected-tag",
            tag,
        )

        self.assertNotEqual(built.returncode, 0)
        self.assertIn("release_worktree_dirty", built.stderr + built.stdout)

    def test_shallow_release_repository_is_rejected(self) -> None:
        self.initialize_git()
        tag = self.release_tag()
        self.git("tag", "-a", tag, "-m", "Release security fixture")
        shallow = Path(self.temporary.name) / "shallow-release"
        self.git(
            "clone",
            "--depth=1",
            "--branch",
            tag,
            self.root.as_uri(),
            str(shallow),
            cwd=Path(self.temporary.name),
        )

        built = self.run_script_in(
            shallow,
            "scripts/build_release.py",
            "--output-dir",
            str(Path(self.temporary.name) / "shallow-release-output"),
            "--expected-tag",
            tag,
        )

        self.assertNotEqual(built.returncode, 0)
        self.assertIn("release_repository_shallow", built.stderr + built.stdout)

    def test_action_pin_cannot_be_satisfied_by_a_comment(self) -> None:
        workflow = self.root / ".github" / "workflows" / "ci.yml"
        text = workflow.read_text(encoding="utf-8")
        expected = "actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd"
        replacement = "actions/checkout@" + "0" * 40
        attacked = text.replace(expected, replacement)
        attacked = attacked.replace(
            "    steps:\n",
            "    steps:\n      - uses: attacker/example-action@v1\n",
            1,
        )
        workflow.write_text(attacked + "\n# " + expected + "\n", encoding="utf-8")

        verified = self.run_script("scripts/verify_public_repo.py")

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("workflow_action_set_or_pin", verified.stderr + verified.stdout)

    def test_checkout_credentials_cannot_be_reenabled(self) -> None:
        workflow = self.root / ".github" / "workflows" / "ci.yml"
        text = workflow.read_text(encoding="utf-8")
        workflow.write_text(
            text.replace("persist-credentials: false", "persist-credentials: true", 1)
            + "\n# persist-credentials: false\n",
            encoding="utf-8",
        )

        verified = self.run_script("scripts/verify_public_repo.py")

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("ci_security_controls", verified.stderr + verified.stdout)

    def test_ci_release_artifact_version_cannot_drift(self) -> None:
        workflow = self.root / ".github" / "workflows" / "ci.yml"
        text = workflow.read_text(encoding="utf-8")
        attacked = text.replace(
                "dist/auto-route-for-codex-0.5.0-alpha.2.zip",
                "dist/auto-route-for-codex-0.5.0-alpha.1.zip",
                1,
            )
        workflow.write_text(
            attacked + "\n# dist/auto-route-for-codex-0.5.0-alpha.2.zip\n",
            encoding="utf-8",
        )

        verified = self.run_script("scripts/verify_public_repo.py")

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("ci_security_controls", verified.stderr + verified.stdout)

    def test_ci_top_level_permissions_cannot_expand(self) -> None:
        workflow = self.root / ".github" / "workflows" / "ci.yml"
        text = workflow.read_text(encoding="utf-8")
        workflow.write_text(
            text.replace("permissions:\n  contents: read", "permissions:\n  contents: write", 1),
            encoding="utf-8",
        )

        verified = self.run_script("scripts/verify_public_repo.py")

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("ci_permissions", verified.stderr + verified.stdout)

    def test_dependabot_manifest_directory_cannot_drift(self) -> None:
        configuration = self.root / ".github" / "dependabot.yml"
        text = configuration.read_text(encoding="utf-8")
        configuration.write_text(
            text.replace('directory: "/.github"', 'directory: "/"', 1),
            encoding="utf-8",
        )

        verified = self.run_script("scripts/verify_public_repo.py")

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("dependabot_configuration", verified.stderr + verified.stdout)

    def test_issue_template_version_cannot_drift(self) -> None:
        template = self.root / ".github" / "ISSUE_TEMPLATE" / "bug_report_en.yml"
        text = template.read_text(encoding="utf-8")
        template.write_text(
            text.replace("0.5.0-alpha.2", "0.5.0-alpha.1", 1),
            encoding="utf-8",
        )

        verified = self.run_script("scripts/verify_public_repo.py")

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("issue_template_version", verified.stderr + verified.stdout)

    def test_release_ancestry_gate_cannot_be_satisfied_by_a_comment(self) -> None:
        workflow = self.root / ".github" / "workflows" / "release.yml"
        text = workflow.read_text(encoding="utf-8")
        workflow.write_text(
            text.replace(
                'git merge-base --is-ancestor "$GITHUB_SHA" refs/remotes/origin/main',
                '# git merge-base --is-ancestor "$GITHUB_SHA" refs/remotes/origin/main',
                1,
            ),
            encoding="utf-8",
        )

        verified = self.run_script("scripts/verify_public_repo.py")

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("release_workflow_security_controls", verified.stderr + verified.stdout)

    def test_release_payload_mutation_step_is_rejected(self) -> None:
        workflow = self.root / ".github" / "workflows" / "release.yml"
        text = workflow.read_text(encoding="utf-8")
        injected = (
            "      - name: Mutate the release payload\n"
            "        run: echo synthetic >> \"$RUNNER_TEMP/release/SHA256SUMS\"\n"
        )
        workflow.write_text(
            text.replace(
                "      - name: Publish exactly one immutable release\n",
                injected + "      - name: Publish exactly one immutable release\n",
                1,
            ),
            encoding="utf-8",
        )

        verified = self.run_script("scripts/verify_public_repo.py")

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("release_workflow_security_controls", verified.stderr + verified.stdout)

    def test_validation_step_cannot_continue_on_error(self) -> None:
        workflow = self.root / ".github" / "workflows" / "release.yml"
        text = workflow.read_text(encoding="utf-8")
        workflow.write_text(
            text.replace(
                "      - name: Validate the bounded release payload\n",
                "      - name: Validate the bounded release payload\n"
                "        continue-on-error: true\n",
                1,
            ),
            encoding="utf-8",
        )

        verified = self.run_script("scripts/verify_public_repo.py")

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("release_workflow_security_controls", verified.stderr + verified.stdout)

    def test_unapproved_workflow_secret_reference_is_rejected(self) -> None:
        workflow = self.root / ".github" / "workflows" / "release.yml"
        text = workflow.read_text(encoding="utf-8")
        workflow.write_text(
            text.replace(
                "RELEASE_TAG: ${{ github.ref_name }}",
                "RELEASE_TAG: ${{ github.ref_name }}\n          EXTRA: ${{ secrets.EXTRA }}",
                1,
            ),
            encoding="utf-8",
        )

        verified = self.run_script("scripts/verify_public_repo.py")

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("workflow_secret_reference", verified.stderr + verified.stdout)

    def test_release_build_job_cannot_receive_contents_write(self) -> None:
        workflow = self.root / ".github" / "workflows" / "release.yml"
        text = workflow.read_text(encoding="utf-8")
        workflow.write_text(
            text.replace("contents: read", "contents: write", 1),
            encoding="utf-8",
        )

        verified = self.run_script("scripts/verify_public_repo.py")

        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("release_build_permissions", verified.stderr + verified.stdout)


if __name__ == "__main__":
    unittest.main()
