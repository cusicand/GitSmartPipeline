"""
Read, bump, and write __version__ = "x.y.z" in a Python source file.
Pure string/regex operations — no subprocess.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

VERSION_PATTERN = re.compile(
    r'(__version__\s*=\s*["\'])(\d+)\.(\d+)\.(\d+)(["\'])',
    re.MULTILINE,
)

VersionTuple = tuple[int, int, int]


def read_version(version_file: Path) -> VersionTuple:
    text = version_file.read_text(encoding="utf-8")
    match = VERSION_PATTERN.search(text)
    if not match:
        raise ValueError(
            f"No __version__ = 'x.y.z' pattern found in {version_file}"
        )
    return int(match.group(2)), int(match.group(3)), int(match.group(4))


def bump_version(
    current: VersionTuple,
    part: Literal["patch", "minor", "major"],
) -> VersionTuple:
    major, minor, patch = current
    if part == "major":
        return (major + 1, 0, 0)
    if part == "minor":
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)


def write_version(version_file: Path, new_version: VersionTuple) -> str:
    """
    Replace the __version__ line in-place. Returns the new version string.
    """
    text = version_file.read_text(encoding="utf-8")
    ver_str = format_version(new_version)

    def replacer(m: re.Match) -> str:
        return f"{m.group(1)}{ver_str}{m.group(5)}"

    new_text, count = VERSION_PATTERN.subn(replacer, text)
    if count == 0:
        raise ValueError(f"No __version__ pattern found in {version_file}")
    version_file.write_text(new_text, encoding="utf-8")
    return ver_str


def format_version(v: VersionTuple) -> str:
    return f"{v[0]}.{v[1]}.{v[2]}"


def format_tag(v: VersionTuple) -> str:
    return f"v{v[0]}.{v[1]}.{v[2]}"
