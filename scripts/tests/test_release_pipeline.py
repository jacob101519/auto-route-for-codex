from __future__ import annotations

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
        return subprocess.run(
            [sys.executable, "-B", relative, *arguments],
            cwd=self.root,
            env=self.environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

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
        self.assertIn("ci_action_set_or_pin", verified.stderr + verified.stdout)


if __name__ == "__main__":
    unittest.main()
