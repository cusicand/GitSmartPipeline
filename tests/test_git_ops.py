from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from gsp.git_ops import (
    GitError,
    commit,
    create_tag,
    get_changed_files,
    get_current_branch,
    get_repo_root,
    stage_files,
    tag_exists,
)


class TestGetRepoRoot:
    def test_returns_root(self, tmp_git_repo: Path) -> None:
        assert get_repo_root(tmp_git_repo) == tmp_git_repo

    def test_from_subdir(self, tmp_git_repo: Path) -> None:
        subdir = tmp_git_repo / "mypackage"
        assert get_repo_root(subdir) == tmp_git_repo


class TestGetCurrentBranch:
    def test_returns_branch_name(self, tmp_git_repo: Path) -> None:
        branch = get_current_branch(tmp_git_repo)
        assert branch in ("main", "master")


class TestStageFiles:
    def test_stage_existing_file(self, tmp_git_repo: Path) -> None:
        f = tmp_git_repo / "new.py"
        f.write_text("x = 1\n")
        staged = stage_files(["new.py"], tmp_git_repo)
        assert "new.py" in staged

    def test_stage_glob_pattern(self, tmp_git_repo: Path) -> None:
        (tmp_git_repo / "a.py").write_text("a=1\n")
        (tmp_git_repo / "b.py").write_text("b=2\n")
        staged = stage_files(["*.py"], tmp_git_repo)
        assert len(staged) >= 2

    def test_stage_raises_on_missing_pattern(self, tmp_git_repo: Path) -> None:
        with pytest.raises(GitError, match="No files matched"):
            stage_files(["nonexistent_*.xyz"], tmp_git_repo)

    def test_stage_nested_file(self, tmp_git_repo: Path) -> None:
        (tmp_git_repo / "mypackage" / "new_module.py").write_text("pass\n")
        staged = stage_files(["mypackage/new_module.py"], tmp_git_repo)
        assert any("new_module.py" in s for s in staged)


class TestCommit:
    def test_commit_creates_sha(self, tmp_git_repo: Path) -> None:
        (tmp_git_repo / "foo.txt").write_text("hello\n")
        stage_files(["foo.txt"], tmp_git_repo)
        sha = commit("test: add foo.txt", tmp_git_repo)
        assert len(sha) == 7

    def test_commit_raises_if_nothing_staged(self, tmp_git_repo: Path) -> None:
        with pytest.raises(GitError):
            commit("empty commit", tmp_git_repo)

    def test_commit_message_is_exact(self, tmp_git_repo: Path) -> None:
        (tmp_git_repo / "bar.txt").write_text("bar\n")
        stage_files(["bar.txt"], tmp_git_repo)
        commit("fix: exact message", tmp_git_repo)
        log = subprocess.run(
            ["git", "log", "--format=%s", "-1"],
            cwd=tmp_git_repo, capture_output=True, text=True
        ).stdout.strip()
        assert log == "fix: exact message"


class TestGetChangedFiles:
    def test_returns_empty_when_clean(self, tmp_git_repo: Path) -> None:
        assert get_changed_files(tmp_git_repo) == []

    def test_detects_modification(self, tmp_git_repo: Path) -> None:
        (tmp_git_repo / "mypackage" / "__init__.py").write_text('__version__ = "9.9.9"\n')
        changed = get_changed_files(tmp_git_repo)
        assert any("__init__.py" in f for f in changed)


class TestCreateTag:
    def test_creates_annotated_tag(self, tmp_git_repo: Path) -> None:
        create_tag("v9.9.9", "Test release", tmp_git_repo)
        assert tag_exists("v9.9.9", tmp_git_repo)

    def test_tag_exists_false_for_missing(self, tmp_git_repo: Path) -> None:
        assert not tag_exists("v0.0.0-nonexistent", tmp_git_repo)
