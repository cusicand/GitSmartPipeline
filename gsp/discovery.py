"""
Locate the Python file that contains __version__ = "x.y.z" in a project.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

_VERSION_RE = re.compile(r"^\s*__version__\s*=", re.MULTILINE)

_SKIP_DIRS = {
    ".git", "__pycache__", ".tox", "venv", ".venv",
    "build", "dist", ".pytest_cache", "node_modules",
}


class VersionFileNotFoundError(Exception):
    pass


def find_version_file(repo_root: Path) -> Path:
    """
    Auto-detect the file containing __version__ in repo_root.

    Search order:
    1. pyproject.toml → [tool.hatch.version] path (or similar)
    2. Grep all __init__.py files for __version__
    """
    root = Path(repo_root).resolve()

    # Strategy 1: parse pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        path = _read_pyproject_version_path(pyproject, root)
        if path is not None and path.exists():
            return path

    # Strategy 2: grep __init__.py files
    candidates = sorted(
        root.rglob("__init__.py"),
        key=lambda p: len(p.parts),
    )
    for candidate in candidates:
        if any(part in _SKIP_DIRS for part in candidate.parts):
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except OSError:
            continue
        if _VERSION_RE.search(text):
            return candidate

    raise VersionFileNotFoundError(
        f"No __version__ found under {root}. "
        "Use --version-file to specify the path explicitly."
    )


def _read_pyproject_version_path(pyproject: Path, root: Path) -> Path | None:
    try:
        with pyproject.open("rb") as fh:
            data = tomllib.load(fh)
    except Exception:
        return None

    # hatchling: [tool.hatch.version] path = "pkg/__init__.py"
    hatch_path = data.get("tool", {}).get("hatch", {}).get("version", {}).get("path")
    if hatch_path:
        return (root / hatch_path).resolve()

    # setuptools dynamic: [tool.setuptools.dynamic] version = {attr = "pkg.__version__"}
    setuptools_dynamic = data.get("tool", {}).get("setuptools", {}).get("dynamic", {})
    version_attr = setuptools_dynamic.get("version", {})
    if isinstance(version_attr, dict):
        attr = version_attr.get("attr", "")
        if attr:
            # "pkg.__version__" -> "pkg/__init__.py"
            parts = attr.split(".")
            if parts[-1] == "__version__":
                return (root / Path(*parts[:-1]) / "__init__.py").resolve()

    # flit: [tool.flit.module] name = "pkg"
    flit_name = data.get("tool", {}).get("flit", {}).get("module", {}).get("name")
    if flit_name:
        return (root / flit_name / "__init__.py").resolve()

    return None
