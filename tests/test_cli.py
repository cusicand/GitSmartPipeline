"""CLI tests using click.testing.CliRunner — no real subprocess outside tmp repos."""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from gsp.cli import main


runner = CliRunner()


class TestRootGroup:
    def test_help(self) -> None:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "ship" in result.output

    def test_version(self) -> None:
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "gsp" in result.output


class TestStageCLI:
    def test_requires_file_flag(self) -> None:
        result = runner.invoke(main, ["stage"])
        assert result.exit_code != 0

    def test_stage_help(self) -> None:
        result = runner.invoke(main, ["stage", "--help"])
        assert result.exit_code == 0
        assert "--file" in result.output or "-f" in result.output


class TestBumpCLI:
    def test_bump_patch(self, tmp_git_repo: Path) -> None:
        result = runner.invoke(main, [
            "bump", "--part", "patch", "--repo", str(tmp_git_repo)
        ])
        assert result.exit_code == 0, result.output
        assert "0.1.0" in result.output
        assert "0.1.1" in result.output

    def test_bump_invalid_part(self) -> None:
        result = runner.invoke(main, ["bump", "--part", "mega"])
        assert result.exit_code != 0


class TestShipCLI:
    def test_dry_run_no_side_effects(self, tmp_git_repo: Path) -> None:
        (tmp_git_repo / "mypackage" / "__init__.py").write_text('__version__ = "0.1.0"\n')
        result = runner.invoke(main, [
            "ship",
            "-m", "test dry run",
            "--bump", "patch",
            "--no-push",
            "--no-release",
            "--dry-run",
            "--repo", str(tmp_git_repo),
        ])
        assert result.exit_code == 0, result.output
        assert "dry-run" in result.output.lower()
        # Version file must be unchanged
        from gsp.version_ops import read_version
        assert read_version(tmp_git_repo / "mypackage" / "__init__.py") == (0, 1, 0)

    def test_ship_no_bump_skips_version_steps(self, tmp_git_repo: Path) -> None:
        (tmp_git_repo / "newfile.txt").write_text("hello\n")
        result = runner.invoke(main, [
            "ship",
            "-f", "newfile.txt",
            "-m", "add newfile",
            "--no-push",
            "--no-release",
            "--repo", str(tmp_git_repo),
        ])
        assert result.exit_code == 0, result.output
        # No version bump in output
        assert "bump:" not in result.output.lower() or "0.1" not in result.output

    def test_ship_requires_message(self) -> None:
        result = runner.invoke(main, ["ship", "-f", "foo.py"])
        assert result.exit_code != 0


class TestStatusCLI:
    def test_status_shows_version_and_branch(self, tmp_git_repo: Path) -> None:
        result = runner.invoke(main, ["status", "--repo", str(tmp_git_repo)])
        assert result.exit_code == 0, result.output
        assert "0.1.0" in result.output
        assert any(b in result.output for b in ("main", "master"))


class TestCheckCLI:
    def test_check_clean_repo_passes(self, tmp_git_repo: Path) -> None:
        result = runner.invoke(main, ["check", "--repo", str(tmp_git_repo)])
        assert result.exit_code == 0, result.output
        assert "clean" in result.output.lower()

    def test_check_fails_with_uncommitted_changes(self, tmp_git_repo: Path) -> None:
        (tmp_git_repo / "mypackage" / "__init__.py").write_text('__version__ = "0.1.0"\n# changed\n')
        result = runner.invoke(main, ["check", "--repo", str(tmp_git_repo)])
        assert result.exit_code != 0
        assert "uncommitted" in result.output.lower()

    def test_check_help(self) -> None:
        result = runner.invoke(main, ["check", "--help"])
        assert result.exit_code == 0
        assert "--run-tests" in result.output


class TestChangelogCLI:
    def test_changelog_dry_run(self, tmp_git_repo: Path) -> None:
        result = runner.invoke(main, [
            "changelog", "--dry-run", "--repo", str(tmp_git_repo)
        ])
        assert result.exit_code == 0, result.output
        # Should print a section header
        assert "0.1.0" in result.output

    def test_changelog_creates_file(self, tmp_git_repo: Path) -> None:
        result = runner.invoke(main, [
            "changelog", "--repo", str(tmp_git_repo)
        ])
        assert result.exit_code == 0, result.output
        changelog = tmp_git_repo / "CHANGELOG.md"
        assert changelog.exists()
        assert "# Changelog" in changelog.read_text()

    def test_changelog_custom_version(self, tmp_git_repo: Path) -> None:
        result = runner.invoke(main, [
            "changelog", "--version", "9.9.9", "--dry-run",
            "--repo", str(tmp_git_repo)
        ])
        assert result.exit_code == 0, result.output
        assert "9.9.9" in result.output


class TestShipAutoBump:
    def test_auto_bump_and_bump_mutually_exclusive(self, tmp_git_repo: Path) -> None:
        result = runner.invoke(main, [
            "ship", "-m", "test", "--auto-bump", "--bump", "patch",
            "--repo", str(tmp_git_repo),
        ])
        assert result.exit_code != 0

    def test_auto_bump_dry_run(self, tmp_git_repo: Path) -> None:
        result = runner.invoke(main, [
            "ship", "-m", "test message",
            "--auto-bump",
            "--no-push", "--no-release",
            "--dry-run",
            "--repo", str(tmp_git_repo),
        ])
        assert result.exit_code == 0, result.output
        # Should mention auto-bump decision
        assert "auto-bump" in result.output.lower()

    def test_update_changelog_dry_run(self, tmp_git_repo: Path) -> None:
        (tmp_git_repo / "changes.txt").write_text("change\n")
        result = runner.invoke(main, [
            "ship",
            "-f", "changes.txt",
            "-m", "test changelog",
            "--bump", "patch",
            "--update-changelog",
            "--no-push", "--no-release",
            "--dry-run",
            "--repo", str(tmp_git_repo),
        ])
        assert result.exit_code == 0, result.output
        assert "changelog" in result.output.lower()
