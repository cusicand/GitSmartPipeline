"""Shared fixtures for gsp tests."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> Path:
    """
    Real git repo in tmp_path with one initial commit.
    Contains mypackage/__init__.py with __version__ = "0.1.0"
    and a matching pyproject.toml (hatchling).
    """
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)

    pkg = tmp_path / "mypackage"
    pkg.mkdir()
    (pkg / "__init__.py").write_text('__version__ = "0.1.0"\n', encoding="utf-8")

    (tmp_path / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n'
        '[tool.hatch.version]\npath = "mypackage/__init__.py"\n',
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# Test project\n", encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True)
    return tmp_path


@pytest.fixture
def fake_init_py(tmp_path: Path) -> Path:
    """Standalone __init__.py with __version__ for version_ops tests."""
    f = tmp_path / "__init__.py"
    f.write_text(
        "# header comment\n"
        "__version__ = \"1.2.3\"\n"
        "# footer comment\n",
        encoding="utf-8",
    )
    return f
