"""Unit tests for changelog_ops — pure logic, no real git repo needed."""
from __future__ import annotations

from pathlib import Path

import pytest

from gsp.changelog_ops import (
    format_changelog_section,
    parse_commit,
    suggest_bump,
    update_changelog,
)


class TestParseCommit:
    def test_fix_prefix(self) -> None:
        assert parse_commit("fix: memory leak in pair.py") == ("fix", "memory leak in pair.py")

    def test_add_prefix(self) -> None:
        assert parse_commit("add: TopoCorrection filter") == ("add", "TopoCorrection filter")

    def test_update_prefix(self) -> None:
        assert parse_commit("update: sensor_filter in get_pairs()") == (
            "update", "sensor_filter in get_pairs()"
        )

    def test_docs_prefix(self) -> None:
        assert parse_commit("docs: add examples to README") == ("docs", "add examples to README")

    def test_case_insensitive(self) -> None:
        prefix, body = parse_commit("Fix: uppercase Fix prefix")
        assert prefix == "fix"
        assert "uppercase" in body

    def test_unknown_prefix_returns_other(self) -> None:
        prefix, body = parse_commit("Initial commit")
        assert prefix == "other"
        assert body == "Initial commit"

    def test_no_prefix_returns_other(self) -> None:
        prefix, _ = parse_commit("something without colon")
        assert prefix == "other"


class TestSuggestBump:
    def test_add_commit_suggests_minor(self) -> None:
        commits = [("abc", "add: new feature"), ("def", "fix: something")]
        assert suggest_bump(commits) == "minor"

    def test_only_fix_suggests_patch(self) -> None:
        commits = [("abc", "fix: bug"), ("def", "update: refactor")]
        assert suggest_bump(commits) == "patch"

    def test_empty_commits_suggests_patch(self) -> None:
        assert suggest_bump([]) == "patch"

    def test_docs_only_suggests_patch(self) -> None:
        commits = [("abc", "docs: update README")]
        assert suggest_bump(commits) == "patch"

    def test_multiple_add_still_minor(self) -> None:
        commits = [("a", "add: feature A"), ("b", "add: feature B")]
        assert suggest_bump(commits) == "minor"


class TestFormatChangelogSection:
    def _make_commits(self) -> list[tuple[str, str]]:
        return [
            ("abc1234", "add: TopoCorrection filter"),
            ("def5678", "fix: memory leak in pair correlation"),
            ("ghi9012", "update: refactor sensor_filter"),
            ("jkl3456", "docs: add docstrings to CorrectionPipeline"),
            ("mno7890", "Initial commit without prefix"),
        ]

    def test_contains_version_header(self) -> None:
        section = format_changelog_section("0.1.1", self._make_commits(), "2026-01-01")
        assert "## [0.1.1] — 2026-01-01" in section

    def test_features_section_present(self) -> None:
        section = format_changelog_section("0.1.1", self._make_commits())
        assert "### Features" in section
        assert "TopoCorrection filter" in section

    def test_bugfixes_section_present(self) -> None:
        section = format_changelog_section("0.1.1", self._make_commits())
        assert "### Bug Fixes" in section
        assert "memory leak" in section

    def test_improvements_section_present(self) -> None:
        section = format_changelog_section("0.1.1", self._make_commits())
        assert "### Improvements" in section

    def test_sha_included_in_entry(self) -> None:
        section = format_changelog_section("0.1.1", self._make_commits())
        assert "abc1234" in section

    def test_unknown_prefix_goes_to_other(self) -> None:
        section = format_changelog_section("0.1.1", self._make_commits())
        assert "### Other" in section
        assert "Initial commit without prefix" in section

    def test_empty_commits(self) -> None:
        section = format_changelog_section("0.1.1", [])
        assert "## [0.1.1]" in section
        assert "### Features" not in section

    def test_uses_today_by_default(self) -> None:
        from datetime import date
        section = format_changelog_section("0.1.1", [])
        assert date.today().isoformat() in section


class TestUpdateChangelog:
    def test_creates_file_if_missing(self, tmp_path: Path) -> None:
        path = tmp_path / "CHANGELOG.md"
        update_changelog(path, "## [0.1.0] — 2026-01-01\n\n- first release\n")
        assert path.exists()
        assert "# Changelog" in path.read_text()
        assert "## [0.1.0]" in path.read_text()

    def test_prepends_to_existing_file(self, tmp_path: Path) -> None:
        path = tmp_path / "CHANGELOG.md"
        path.write_text("# Changelog\n\n## [0.1.0] — old release\n")
        update_changelog(path, "## [0.1.1] — 2026-06-12\n\n- new entry\n")
        content = path.read_text()
        # New section appears before old section
        assert content.index("## [0.1.1]") < content.index("## [0.1.0]")

    def test_preserves_existing_content(self, tmp_path: Path) -> None:
        path = tmp_path / "CHANGELOG.md"
        path.write_text("# Changelog\n\n## [0.1.0] — old\n\n- old entry\n")
        update_changelog(path, "## [0.1.1] — new\n\n")
        content = path.read_text()
        assert "old entry" in content

    def test_heading_not_duplicated(self, tmp_path: Path) -> None:
        path = tmp_path / "CHANGELOG.md"
        path.write_text("# Changelog\n\n## [0.1.0]\n")
        update_changelog(path, "## [0.1.1]\n")
        content = path.read_text()
        assert content.count("# Changelog") == 1
