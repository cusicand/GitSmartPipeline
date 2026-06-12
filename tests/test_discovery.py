from __future__ import annotations

from pathlib import Path

import pytest

from gsp.discovery import VersionFileNotFoundError, find_version_file


class TestFindVersionFile:
    def test_finds_via_hatchling_pyproject(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text('__version__ = "1.0.0"\n')
        (tmp_path / "pyproject.toml").write_text(
            '[tool.hatch.version]\npath = "mypkg/__init__.py"\n'
        )
        result = find_version_file(tmp_path)
        assert result == (tmp_path / "mypkg" / "__init__.py").resolve()

    def test_falls_back_to_grep(self, tmp_path: Path) -> None:
        pkg = tmp_path / "nopyproject"
        pkg.mkdir()
        (pkg / "__init__.py").write_text('__version__ = "2.0.0"\n')
        result = find_version_file(tmp_path)
        assert result == (pkg / "__init__.py").resolve()

    def test_raises_when_nothing_found(self, tmp_path: Path) -> None:
        with pytest.raises(VersionFileNotFoundError, match="No __version__"):
            find_version_file(tmp_path)

    def test_skips_venv_dirs(self, tmp_path: Path) -> None:
        venv_init = tmp_path / ".venv" / "lib" / "mypkg"
        venv_init.mkdir(parents=True)
        (venv_init / "__init__.py").write_text('__version__ = "3.0.0"\n')
        # No real package present → should raise, not return venv path
        with pytest.raises(VersionFileNotFoundError):
            find_version_file(tmp_path)

    def test_hatchling_path_takes_priority(self, tmp_path: Path) -> None:
        real_pkg = tmp_path / "real"
        real_pkg.mkdir()
        (real_pkg / "__init__.py").write_text('__version__ = "0.9.0"\n')

        other_pkg = tmp_path / "other"
        other_pkg.mkdir()
        (other_pkg / "__init__.py").write_text('__version__ = "1.0.0"\n')

        (tmp_path / "pyproject.toml").write_text(
            '[tool.hatch.version]\npath = "real/__init__.py"\n'
        )
        result = find_version_file(tmp_path)
        assert result == (real_pkg / "__init__.py").resolve()
