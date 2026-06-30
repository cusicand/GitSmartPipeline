"""
Ship orchestration tests using mocks for git_ops / release_ops.
These test the step sequencing and flag logic without any subprocess calls.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

from click.testing import CliRunner

from gsp.cli import main

runner = CliRunner()


def _base_args(tmp_git_repo: Path, extra: list[str] | None = None) -> list[str]:
    # Create a new file so there is something to stage and commit.
    (tmp_git_repo / "changes.txt").write_text("change\n")
    args = [
        "ship",
        "-f", "changes.txt",
        "-m", "test message",
        "--bump", "patch",
        "--repo", str(tmp_git_repo),
    ]
    return args + (extra or [])


@patch("gsp.cli.create_github_release", return_value="https://github.com/r/r/releases/v0.1.1")
@patch("gsp.cli.push_tag")
@patch("gsp.cli.push")
@patch("gsp.cli.create_tag")
@patch("gsp.cli.gh_available", return_value=True)
class TestShipOrchestration:
    def test_full_ship_calls_all_steps(
        self,
        mock_gh: MagicMock,
        mock_tag: MagicMock,
        mock_push: MagicMock,
        mock_push_tag: MagicMock,
        mock_release: MagicMock,
        tmp_git_repo: Path,
    ) -> None:
        result = runner.invoke(main, _base_args(tmp_git_repo))
        assert result.exit_code == 0, result.output
        mock_push.assert_called_once()
        mock_push_tag.assert_called_once()
        mock_tag.assert_called_once()
        mock_release.assert_called_once()

    def test_update_changelog_writes_file(
        self,
        mock_gh: MagicMock,
        mock_tag: MagicMock,
        mock_push: MagicMock,
        mock_push_tag: MagicMock,
        mock_release: MagicMock,
        tmp_git_repo: Path,
    ) -> None:
        # Non-dry-run path: exercises the real update_changelog() call so the
        # flag/function name collision can't regress.
        result = runner.invoke(main, _base_args(tmp_git_repo, ["--update-changelog"]))
        assert result.exit_code == 0, result.output
        assert (tmp_git_repo / "CHANGELOG.md").exists()
        mock_release.assert_called_once()

    def test_no_push_skips_push_and_release(
        self,
        mock_gh: MagicMock,
        mock_tag: MagicMock,
        mock_push: MagicMock,
        mock_push_tag: MagicMock,
        mock_release: MagicMock,
        tmp_git_repo: Path,
    ) -> None:
        result = runner.invoke(main, _base_args(tmp_git_repo, ["--no-push"]))
        assert result.exit_code == 0, result.output
        mock_push.assert_not_called()
        mock_push_tag.assert_not_called()
        mock_release.assert_not_called()

    def test_no_release_flag_skips_gh_only(
        self,
        mock_gh: MagicMock,
        mock_tag: MagicMock,
        mock_push: MagicMock,
        mock_push_tag: MagicMock,
        mock_release: MagicMock,
        tmp_git_repo: Path,
    ) -> None:
        result = runner.invoke(main, _base_args(tmp_git_repo, ["--no-release", "--no-push"]))
        assert result.exit_code == 0, result.output
        mock_release.assert_not_called()
        mock_tag.assert_called_once()

    def test_no_tag_skips_tag_and_release(
        self,
        mock_gh: MagicMock,
        mock_tag: MagicMock,
        mock_push: MagicMock,
        mock_push_tag: MagicMock,
        mock_release: MagicMock,
        tmp_git_repo: Path,
    ) -> None:
        result = runner.invoke(main, _base_args(tmp_git_repo, ["--no-tag", "--no-push"]))
        assert result.exit_code == 0, result.output
        mock_tag.assert_not_called()
        mock_release.assert_not_called()

    def test_dry_run_calls_nothing(
        self,
        mock_gh: MagicMock,
        mock_tag: MagicMock,
        mock_push: MagicMock,
        mock_push_tag: MagicMock,
        mock_release: MagicMock,
        tmp_git_repo: Path,
    ) -> None:
        result = runner.invoke(main, _base_args(tmp_git_repo, ["--dry-run"]))
        assert result.exit_code == 0, result.output
        mock_push.assert_not_called()
        mock_tag.assert_not_called()
        mock_release.assert_not_called()


@patch("gsp.cli.gh_available", return_value=False)
class TestGhNotAvailable:
    def test_ship_fails_when_gh_missing(
        self,
        mock_gh: MagicMock,
        tmp_git_repo: Path,
    ) -> None:
        result = runner.invoke(main, _base_args(tmp_git_repo))
        assert result.exit_code != 0
        assert "gh" in result.output.lower()

    def test_ship_ok_with_no_release(
        self,
        mock_gh: MagicMock,
        tmp_git_repo: Path,
    ) -> None:
        with (
            patch("gsp.cli.push"),
            patch("gsp.cli.push_tag"),
            patch("gsp.cli.create_tag"),
        ):
            result = runner.invoke(main, _base_args(tmp_git_repo, ["--no-release"]))
        assert result.exit_code == 0, result.output
