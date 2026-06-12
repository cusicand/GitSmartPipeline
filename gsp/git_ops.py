"""
Git operations via subprocess. Raises GitError on non-zero exit codes.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(Exception):
    def __init__(self, cmd: str, returncode: int, stderr: str) -> None:
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"git command failed (exit {returncode}): {cmd}\n{stderr}")


def run_git(
    args: list[str],
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess:
    cmd = ["git"] + args
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise GitError(
            cmd=" ".join(cmd),
            returncode=result.returncode,
            stderr=result.stderr.strip(),
        )
    return result


def get_repo_root(cwd: Path) -> Path:
    result = run_git(["rev-parse", "--show-toplevel"], cwd=cwd)
    return Path(result.stdout.strip())


def get_current_branch(cwd: Path) -> str:
    result = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    return result.stdout.strip()


def get_changed_files(cwd: Path, staged: bool = False) -> list[str]:
    args = ["diff", "--name-only"]
    if staged:
        args.append("--cached")
    result = run_git(args, cwd=cwd)
    return [f for f in result.stdout.splitlines() if f]


def stage_files(patterns: list[str], cwd: Path) -> list[str]:
    """
    Expand glob patterns relative to cwd and git-add matched files.
    Returns the list of paths that were staged.
    Raises GitError if any git add fails.
    """
    staged: list[str] = []
    root = Path(cwd)

    for pattern in patterns:
        path_obj = Path(pattern)

        # Absolute paths: use directly without globbing (Python 3.12+ disallows
        # absolute patterns in Path.glob).
        if path_obj.is_absolute():
            if path_obj.exists():
                rel = str(path_obj.relative_to(root))
                run_git(["add", rel], cwd=root)
                staged.append(rel)
            else:
                raise GitError(
                    cmd=f"git add {pattern}",
                    returncode=1,
                    stderr=f"File not found: {pattern}",
                )
            continue

        try:
            matches = sorted(root.glob(pattern))
        except (ValueError, NotImplementedError):
            matches = []

        if not matches:
            # Try as a literal relative path before giving up
            literal = root / pattern
            if literal.exists():
                matches = [literal]
            else:
                raise GitError(
                    cmd=f"git add {pattern}",
                    returncode=1,
                    stderr=f"No files matched pattern: {pattern}",
                )
        for path in matches:
            rel = str(path.relative_to(root))
            run_git(["add", rel], cwd=root)
            staged.append(rel)

    return staged


def commit(message: str, cwd: Path) -> str:
    """Stage a commit and return the short SHA."""
    run_git(["commit", "-m", message], cwd=cwd)
    result = run_git(["rev-parse", "--short", "HEAD"], cwd=cwd)
    return result.stdout.strip()


def push(cwd: Path, remote: str = "origin", branch: str | None = None) -> None:
    if branch is None:
        branch = get_current_branch(cwd)
    run_git(["push", remote, branch], cwd=cwd)


def push_tags(cwd: Path, remote: str = "origin") -> None:
    run_git(["push", remote, "--tags"], cwd=cwd)


def create_tag(tag_name: str, message: str, cwd: Path) -> None:
    run_git(["tag", "-a", tag_name, "-m", message], cwd=cwd)


def tag_exists(tag_name: str, cwd: Path) -> bool:
    result = run_git(["tag", "-l", tag_name], cwd=cwd)
    return bool(result.stdout.strip())
