from __future__ import annotations

from pathlib import Path

import pytest

from gsp.version_ops import (
    bump_version,
    format_tag,
    format_version,
    read_version,
    write_version,
)


class TestReadVersion:
    def test_reads_semver(self, fake_init_py: Path) -> None:
        assert read_version(fake_init_py) == (1, 2, 3)

    def test_raises_if_no_version(self, tmp_path: Path) -> None:
        f = tmp_path / "nover.py"
        f.write_text("# nothing here\n")
        with pytest.raises(ValueError, match="No __version__"):
            read_version(f)

    def test_double_quotes(self, tmp_path: Path) -> None:
        f = tmp_path / "pkg.py"
        f.write_text('__version__ = "2.0.0"\n')
        assert read_version(f) == (2, 0, 0)

    def test_single_quotes(self, tmp_path: Path) -> None:
        f = tmp_path / "pkg.py"
        f.write_text("__version__ = '3.4.5'\n")
        assert read_version(f) == (3, 4, 5)


class TestBumpVersion:
    def test_patch(self) -> None:
        assert bump_version((1, 2, 3), "patch") == (1, 2, 4)

    def test_minor_resets_patch(self) -> None:
        assert bump_version((1, 2, 3), "minor") == (1, 3, 0)

    def test_major_resets_minor_and_patch(self) -> None:
        assert bump_version((1, 2, 3), "major") == (2, 0, 0)

    def test_patch_from_zero(self) -> None:
        assert bump_version((0, 0, 0), "patch") == (0, 0, 1)


class TestWriteVersion:
    def test_updates_version(self, fake_init_py: Path) -> None:
        write_version(fake_init_py, (2, 0, 0))
        assert read_version(fake_init_py) == (2, 0, 0)

    def test_preserves_surrounding_content(self, fake_init_py: Path) -> None:
        write_version(fake_init_py, (9, 9, 9))
        text = fake_init_py.read_text()
        assert "# header comment" in text
        assert "# footer comment" in text

    def test_roundtrip(self, fake_init_py: Path) -> None:
        old = read_version(fake_init_py)
        new = bump_version(old, "minor")
        write_version(fake_init_py, new)
        assert read_version(fake_init_py) == new

    def test_raises_if_no_pattern(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.py"
        f.write_text("# nothing\n")
        with pytest.raises(ValueError, match="No __version__"):
            write_version(f, (1, 0, 0))


class TestFormatHelpers:
    def test_format_version(self) -> None:
        assert format_version((1, 2, 3)) == "1.2.3"

    def test_format_tag(self) -> None:
        assert format_tag((1, 2, 3)) == "v1.2.3"
