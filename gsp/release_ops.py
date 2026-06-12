"""
GitHub release creation via the `gh` CLI.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def gh_available() -> bool:
    """Return True if `gh` is on PATH and authenticated."""
    if shutil.which("gh") is None:
        return False
    result = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def create_github_release(
    tag: str,
    title: str | None,
    notes: str | None,
    cwd: Path,
) -> str:
    """
    Create a GitHub release for the given tag.
    Returns the URL of the created release.
    Uses --generate-notes if notes is None.
    """
    cmd = ["gh", "release", "create", tag]

    if title:
        cmd += ["--title", title]
    else:
        cmd += ["--title", tag]

    if notes:
        cmd += ["--notes", notes]
    else:
        cmd.append("--generate-notes")

    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()
