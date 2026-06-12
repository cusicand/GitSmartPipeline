"""
Changelog generation and auto-bump logic from conventional commit history.
Pure Python — no subprocess except for git log reads via git_ops.run_git.
"""
from __future__ import annotations

import re
import subprocess
from datetime import date
from pathlib import Path

CATEGORY_MAP: dict[str, str] = {
    "add":    "Features",
    "fix":    "Bug Fixes",
    "update": "Improvements",
    "remove": "Removed",
    "docs":   "Documentation",
    "test":   "Testing",
}

# Ordering for the output sections
CATEGORY_ORDER = ["Features", "Bug Fixes", "Improvements", "Removed", "Documentation", "Testing"]

PREFIX_TO_BUMP: dict[str, str] = {
    "add":    "minor",
    "fix":    "patch",
    "update": "patch",
    "remove": "patch",
    "docs":   "patch",
    "test":   "patch",
}

_PREFIX_RE = re.compile(
    r"^(" + "|".join(CATEGORY_MAP.keys()) + r"):\s*(.+)$",
    re.IGNORECASE,
)


def get_last_tag(cwd: Path) -> str | None:
    """Return the most recent semver tag (e.g., 'v0.1.0'), or None if no tags exist."""
    result = subprocess.run(
        ["git", "tag", "-l", "--sort=-v:refname", "v*"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    tags = [t.strip() for t in result.stdout.splitlines() if t.strip()]
    return tags[0] if tags else None


def get_commits_since_tag(
    last_tag: str | None,
    cwd: Path,
) -> list[tuple[str, str]]:
    """
    Return [(short_sha, subject), ...] for commits since last_tag.
    If last_tag is None, returns all commits.
    """
    range_arg = f"{last_tag}..HEAD" if last_tag else "HEAD"
    result = subprocess.run(
        ["git", "log", "--pretty=format:%h %s", range_arg],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    commits = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        sha, _, subject = line.partition(" ")
        commits.append((sha, subject))
    return commits


def parse_commit(subject: str) -> tuple[str, str]:
    """
    Parse a commit subject into (prefix, body).

    'fix: memory leak in pair.py' → ('fix', 'memory leak in pair.py')
    'Add something' → ('other', 'Add something')
    """
    m = _PREFIX_RE.match(subject.strip())
    if m:
        return m.group(1).lower(), m.group(2).strip()
    return "other", subject.strip()


def suggest_bump(commits: list[tuple[str, str]]) -> str:
    """
    Analyze commits and suggest 'patch' or 'minor'.
    Any 'add:' commit triggers a minor bump; everything else is patch.
    """
    for _, subject in commits:
        prefix, _ = parse_commit(subject)
        if PREFIX_TO_BUMP.get(prefix) == "minor":
            return "minor"
    return "patch"


def format_changelog_section(
    version: str,
    commits: list[tuple[str, str]],
    date_str: str | None = None,
) -> str:
    """
    Format commits into a markdown changelog section:

    ## [0.1.1] — 2026-06-12

    ### Features
    - add TopoCorrection filter (abc1234)

    ### Bug Fixes
    - fix memory leak in pair correlation (def5678)
    """
    today = date_str or date.today().isoformat()
    lines: list[str] = [f"## [{version}] — {today}", ""]

    groups: dict[str, list[str]] = {cat: [] for cat in CATEGORY_ORDER}
    others: list[str] = []

    for sha, subject in commits:
        prefix, body = parse_commit(subject)
        category = CATEGORY_MAP.get(prefix)
        if category:
            groups[category].append(f"- {body} ({sha})")
        else:
            others.append(f"- {subject} ({sha})")

    for category in CATEGORY_ORDER:
        entries = groups[category]
        if entries:
            lines.append(f"### {category}")
            lines.extend(entries)
            lines.append("")

    if others:
        lines.append("### Other")
        lines.extend(others)
        lines.append("")

    return "\n".join(lines)


def update_changelog(changelog_path: Path, section: str) -> None:
    """
    Prepend `section` into CHANGELOG.md after the top-level heading.
    Creates the file with a heading if it doesn't exist.
    """
    heading = "# Changelog\n\n"

    if changelog_path.exists():
        existing = changelog_path.read_text(encoding="utf-8")
        if existing.startswith("# Changelog"):
            # Insert after the heading line
            rest = existing[len("# Changelog"):].lstrip("\n")
            new_content = f"# Changelog\n\n{section}\n{rest}"
        else:
            new_content = f"{heading}{section}\n{existing}"
    else:
        new_content = f"{heading}{section}\n"

    changelog_path.write_text(new_content, encoding="utf-8")
