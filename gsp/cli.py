"""
gsp — GitSmartPipeline CLI entry point.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from . import __version__
from . import console as con
from .discovery import VersionFileNotFoundError, find_version_file
from .git_ops import (
    GitError,
    commit,
    create_tag,
    get_changed_files,
    get_current_branch,
    get_repo_root,
    push,
    push_tags,
    stage_files,
    tag_exists,
)
from .changelog_ops import (
    format_changelog_section,
    get_commits_since_tag,
    get_last_tag,
    suggest_bump,
    update_changelog,
)
from .release_ops import create_github_release, gh_available
from .version_ops import (
    bump_version,
    format_tag,
    format_version,
    read_version,
    write_version,
)

VALID_PREFIXES = ("update", "fix", "add", "remove", "docs", "test")


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(__version__, prog_name="gsp")
def main() -> None:
    """GitSmartPipeline — streamlined git workflow for Python projects."""


# ---------------------------------------------------------------------------
# gsp stage
# ---------------------------------------------------------------------------

@main.command("stage")
@click.option("-f", "--file", "patterns", multiple=True, required=True,
              metavar="GLOB", help="File path or glob pattern to stage (repeatable).")
@click.option("--repo", default=".", show_default=True,
              type=click.Path(exists=True, file_okay=False),
              help="Repository root (defaults to current directory).")
def stage_cmd(patterns: tuple[str, ...], repo: str) -> None:
    """Stage files matching the given glob patterns."""
    cwd = get_repo_root(Path(repo))
    try:
        staged = stage_files(list(patterns), cwd)
    except GitError as exc:
        con.error(str(exc))
        raise SystemExit(1) from exc
    for f in staged:
        con.success(f"Staged: {f}")


# ---------------------------------------------------------------------------
# gsp commit
# ---------------------------------------------------------------------------

@main.command("commit")
@click.option("-p", "--prefix", type=click.Choice(VALID_PREFIXES), required=True,
              help="Conventional commit prefix.")
@click.option("-m", "--message", required=True, help="Commit message body.")
@click.option("--repo", default=".", show_default=True,
              type=click.Path(exists=True, file_okay=False))
def commit_cmd(prefix: str, message: str, repo: str) -> None:
    """Commit all staged changes with a prefixed message."""
    cwd = get_repo_root(Path(repo))
    full_msg = f"{prefix}: {message}"
    try:
        sha = commit(full_msg, cwd)
    except GitError as exc:
        con.error(str(exc))
        raise SystemExit(1) from exc
    con.success(f"Committed {sha} — {full_msg}")


# ---------------------------------------------------------------------------
# gsp push
# ---------------------------------------------------------------------------

@main.command("push")
@click.option("--remote", default="origin", show_default=True)
@click.option("--branch", default=None, help="Branch to push (defaults to current).")
@click.option("--tags", "with_tags", is_flag=True, default=False,
              help="Also push tags.")
@click.option("--repo", default=".", show_default=True,
              type=click.Path(exists=True, file_okay=False))
def push_cmd(remote: str, branch: Optional[str], with_tags: bool, repo: str) -> None:
    """Push commits (and optionally tags) to a remote."""
    cwd = get_repo_root(Path(repo))
    try:
        push(cwd, remote=remote, branch=branch)
        con.success(f"Pushed to {remote}/{branch or get_current_branch(cwd)}")
        if with_tags:
            push_tags(cwd, remote=remote)
            con.success(f"Pushed tags to {remote}")
    except GitError as exc:
        con.error(str(exc))
        raise SystemExit(1) from exc


# ---------------------------------------------------------------------------
# gsp bump
# ---------------------------------------------------------------------------

@main.command("bump")
@click.option("--part", type=click.Choice(["patch", "minor", "major"]), required=True,
              help="Version component to increment.")
@click.option("--version-file", default=None, type=click.Path(),
              help="Path to the file containing __version__. Auto-detected if omitted.")
@click.option("--repo", default=".", show_default=True,
              type=click.Path(exists=True, file_okay=False))
def bump_cmd(part: str, version_file: Optional[str], repo: str) -> None:
    """Bump __version__ in the package's __init__.py and commit the change."""
    cwd = get_repo_root(Path(repo))
    vf = _resolve_version_file(version_file, cwd)
    old = read_version(vf)
    new = bump_version(old, part)  # type: ignore[arg-type]
    write_version(vf, new)
    stage_files([str(vf)], cwd)
    msg = f"bump: {format_version(old)} → {format_version(new)}"
    sha = commit(msg, cwd)
    con.success(f"Version bumped {format_version(old)} → {format_version(new)} ({sha})")


# ---------------------------------------------------------------------------
# gsp tag
# ---------------------------------------------------------------------------

@main.command("tag")
@click.option("--name", default=None,
              help="Tag name (defaults to v<current version>).")
@click.option("--message", default=None,
              help="Tag annotation message.")
@click.option("--version-file", default=None, type=click.Path())
@click.option("--repo", default=".", show_default=True,
              type=click.Path(exists=True, file_okay=False))
def tag_cmd(name: Optional[str], message: Optional[str], version_file: Optional[str], repo: str) -> None:
    """Create an annotated git tag (defaults to current version)."""
    cwd = get_repo_root(Path(repo))
    if name is None:
        vf = _resolve_version_file(version_file, cwd)
        name = format_tag(read_version(vf))
    if tag_exists(name, cwd):
        con.warn(f"Tag {name} already exists — skipped")
        return
    create_tag(name, message or f"Release {name}", cwd)
    con.success(f"Tag created: {name}")


# ---------------------------------------------------------------------------
# gsp release
# ---------------------------------------------------------------------------

@main.command("release")
@click.option("--tag", default=None,
              help="Tag to release (defaults to current version tag).")
@click.option("--title", default=None, help="Release title.")
@click.option("--notes", default=None, help="Release notes (auto-generated if omitted).")
@click.option("--version-file", default=None, type=click.Path())
@click.option("--repo", default=".", show_default=True,
              type=click.Path(exists=True, file_okay=False))
def release_cmd(
    tag: Optional[str],
    title: Optional[str],
    notes: Optional[str],
    version_file: Optional[str],
    repo: str,
) -> None:
    """Create a GitHub release via the gh CLI."""
    cwd = get_repo_root(Path(repo))
    if tag is None:
        vf = _resolve_version_file(version_file, cwd)
        tag = format_tag(read_version(vf))
    if not gh_available():
        con.error("`gh` CLI not found or not authenticated. Run `gh auth login`.")
        raise SystemExit(1)
    url = create_github_release(tag, title, notes, cwd)
    con.success(f"Release published: {url}")


# ---------------------------------------------------------------------------
# gsp status
# ---------------------------------------------------------------------------

@main.command("status")
@click.option("--version-file", default=None, type=click.Path())
@click.option("--repo", default=".", show_default=True,
              type=click.Path(exists=True, file_okay=False))
def status_cmd(version_file: Optional[str], repo: str) -> None:
    """Show current version, branch, and pending changes."""
    cwd = get_repo_root(Path(repo))
    branch = get_current_branch(cwd)
    try:
        vf = _resolve_version_file(version_file, cwd)
        ver = format_version(read_version(vf))
    except (VersionFileNotFoundError, ValueError):
        ver = "(not found)"
    changed = get_changed_files(cwd)
    staged = get_changed_files(cwd, staged=True)
    con.rule("gsp status")
    con.info(f"Branch  : {branch}")
    con.info(f"Version : {ver}")
    con.info(f"Staged  : {len(staged)} file(s)")
    con.info(f"Modified: {len(changed)} file(s)")
    if changed:
        for f in changed:
            click.echo(f"  {f}")


# ---------------------------------------------------------------------------
# gsp check
# ---------------------------------------------------------------------------

@main.command("check")
@click.option("--run-tests", default=None, metavar="CMD",
              help="Shell command to run tests (e.g. 'pytest tests/ -q').")
@click.option("--version-file", default=None, type=click.Path())
@click.option("--repo", default=".", show_default=True,
              type=click.Path(exists=True, file_okay=False))
def check_cmd(run_tests: Optional[str], version_file: Optional[str], repo: str) -> None:
    """Pre-release validation: clean tree, version parseable, optional test gate."""
    import subprocess as _sp

    cwd = get_repo_root(Path(repo))
    con.rule("gsp check")
    failed = False

    # 1. Clean working tree
    result = _sp.run(["git", "status", "--porcelain"], cwd=str(cwd),
                     capture_output=True, text=True)
    unstaged = [l for l in result.stdout.splitlines() if l and not l.startswith("??")]
    if unstaged:
        con.error(f"Working tree has {len(unstaged)} uncommitted change(s)")
        for line in unstaged[:5]:
            click.echo(f"  {line}")
        failed = True
    else:
        con.success("Working tree is clean")

    # 2. No staged changes
    staged = get_changed_files(cwd, staged=True)
    if staged:
        con.error(f"{len(staged)} file(s) staged but not yet committed")
        failed = True
    else:
        con.success("No staged changes")

    # 3. Version parseable
    try:
        vf = _resolve_version_file(version_file, cwd)
        ver = format_version(read_version(vf))
        con.success(f"Version {ver} is parseable")
    except (SystemExit, ValueError) as exc:
        con.error(f"Could not read version: {exc}")
        failed = True
        ver = None

    # 4. Version vs latest tag (warning only)
    last_tag = get_last_tag(cwd)
    if ver and last_tag:
        tag_ver = last_tag.lstrip("v")
        if ver == tag_ver:
            con.warn(f"Version {ver} matches the latest tag {last_tag} — did you forget to bump?")
        else:
            con.success(f"Version {ver} differs from latest tag {last_tag} (ready to release)")
    elif ver and not last_tag:
        con.success(f"Version {ver} — no existing tags (first release)")

    # 5. Optional test run
    if run_tests:
        con.info(f"Running tests: {run_tests}")
        test_result = _sp.run(run_tests, shell=True, cwd=str(cwd))
        if test_result.returncode != 0:
            con.error(f"Tests failed (exit {test_result.returncode})")
            failed = True
        else:
            con.success(f"Tests passed ({run_tests})")

    con.rule("failed — fix the issues above" if failed else "ready to release")
    if failed:
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# gsp changelog
# ---------------------------------------------------------------------------

@main.command("changelog")
@click.option("--version", default=None,
              help="Version string for the section header (defaults to current __version__).")
@click.option("--output", default=None, type=click.Path(),
              help="Path to CHANGELOG.md (defaults to repo root).")
@click.option("--version-file", default=None, type=click.Path())
@click.option("--repo", default=".", show_default=True,
              type=click.Path(exists=True, file_okay=False))
@click.option("--dry-run", is_flag=True, default=False,
              help="Print the section that would be written without modifying any file.")
def changelog_cmd(
    version: Optional[str],
    output: Optional[str],
    version_file: Optional[str],
    repo: str,
    dry_run: bool,
) -> None:
    """Generate or update CHANGELOG.md from commits since the last tag."""
    cwd = get_repo_root(Path(repo))

    if version is None:
        vf = _resolve_version_file(version_file, cwd)
        version = format_version(read_version(vf))

    changelog_path = Path(output) if output else cwd / "CHANGELOG.md"

    last_tag = get_last_tag(cwd)
    commits = get_commits_since_tag(last_tag, cwd)

    if not commits:
        con.warn(f"No commits found since {last_tag or 'the beginning'} — nothing to write")
        return

    section = format_changelog_section(version, commits)
    con.rule(f"Changelog section for {version}")
    click.echo(section)

    if not dry_run:
        update_changelog(changelog_path, section)
        con.success(f"Written to {changelog_path}")
    else:
        con.dry_run(f"update_changelog({changelog_path})")


# ---------------------------------------------------------------------------
# gsp ship  (main workflow)
# ---------------------------------------------------------------------------

@main.command("ship")
@click.option("-f", "--file", "patterns", multiple=True, metavar="GLOB",
              help="File path or glob to stage. Can be repeated.")
@click.option("-m", "--message", required=True, help="Commit message body.")
@click.option("--bump", "bump_part",
              type=click.Choice(["patch", "minor", "major"]), default=None,
              help="Version component to bump after committing.")
@click.option("--auto-bump", is_flag=True, default=False,
              help="Auto-determine bump level (patch/minor) from commits since last tag.")
@click.option("--update-changelog", is_flag=True, default=False,
              help="Generate/update CHANGELOG.md as part of the bump commit.")
@click.option("--prefix", type=click.Choice(VALID_PREFIXES), default="fix",
              show_default=True, help="Conventional commit prefix.")
@click.option("--remote", default="origin", show_default=True)
@click.option("--no-push", is_flag=True, default=False)
@click.option("--no-tag", is_flag=True, default=False)
@click.option("--no-release", is_flag=True, default=False)
@click.option("--repo", default=".", show_default=True,
              type=click.Path(exists=True, file_okay=False))
@click.option("--version-file", default=None, type=click.Path())
@click.option("--dry-run", is_flag=True, default=False,
              help="Print what would happen without making any changes.")
def ship_cmd(
    patterns: tuple[str, ...],
    message: str,
    bump_part: Optional[str],
    auto_bump: bool,
    update_changelog: bool,
    prefix: str,
    remote: str,
    no_push: bool,
    no_tag: bool,
    no_release: bool,
    repo: str,
    version_file: Optional[str],
    dry_run: bool,
) -> None:
    """
    One-shot workflow: stage → commit → bump version → tag → push → release.

    Use --auto-bump to let gsp determine patch/minor from commit history.
    Use --update-changelog to include a CHANGELOG.md update in the bump commit.

    Examples:

        gsp ship -f geomulticorr/core/pair.py -m "fix outlier edge case" --bump patch

        gsp ship -f geomulticorr/core/pair.py -m "fix outlier edge case" --auto-bump --update-changelog
    """
    cwd = get_repo_root(Path(repo))

    # ── Resolve bump level ────────────────────────────────────────────────
    if auto_bump and bump_part:
        con.error("--auto-bump and --bump are mutually exclusive.")
        raise SystemExit(1)

    if auto_bump:
        last_tag = get_last_tag(cwd)
        commits_so_far = get_commits_since_tag(last_tag, cwd)
        bump_part = suggest_bump(commits_so_far)
        con.info(
            f"Auto-bump: {bump_part} "
            f"(from {len(commits_so_far)} commit(s) since {last_tag or 'the beginning'})"
        )

    do_tag = bump_part is not None and not no_tag
    do_push = not no_push
    # A release requires the tag to have been pushed first.
    do_release = do_tag and do_push and not no_release
    do_changelog = update_changelog and bump_part is not None

    # Determine total steps for progress display
    total = sum([
        bool(patterns),   # stage
        True,             # commit
        bump_part is not None,  # version bump + commit (includes changelog if enabled)
        do_tag,           # tag
        do_push,          # push
        do_release,       # release
    ])
    step_n = 0

    def _step(label: str) -> None:
        nonlocal step_n
        step_n += 1
        con.step(step_n, total, label)

    # ── Validate early ────────────────────────────────────────────────────
    vf: Optional[Path] = None
    if bump_part is not None:
        vf = _resolve_version_file(version_file, cwd)
        old_ver = read_version(vf)
        new_ver = bump_version(old_ver, bump_part)  # type: ignore[arg-type]
        new_ver_str = format_version(new_ver)
        tag_name = format_tag(new_ver)
    else:
        old_ver = new_ver = new_ver_str = tag_name = None  # type: ignore[assignment]

    if do_release and not dry_run and not gh_available():
        con.error("`gh` CLI not found or not authenticated. Run `gh auth login`.")
        con.warn("Use --no-release to skip the GitHub release step.")
        raise SystemExit(1)

    if dry_run:
        con.rule("dry-run preview")

    # ── Step 1: Stage files ───────────────────────────────────────────────
    if patterns:
        _step(f"Staging {len(patterns)} pattern(s): {', '.join(patterns)}")
        if not dry_run:
            try:
                staged = stage_files(list(patterns), cwd)
            except GitError as exc:
                con.error(str(exc))
                raise SystemExit(1) from exc
            for f in staged:
                con.info(f"  staged: {f}")
        else:
            for p in patterns:
                con.dry_run(f"git add {p}")

    # ── Step 2: Commit ────────────────────────────────────────────────────
    full_msg = f"{prefix}: {message}"
    _step(f"Commit: {full_msg!r}")
    if not dry_run:
        try:
            sha = commit(full_msg, cwd)
        except GitError as exc:
            con.error(str(exc))
            raise SystemExit(1) from exc
        con.success(f"Committed {sha}")
    else:
        con.dry_run(f"git commit -m {full_msg!r}")

    # ── Step 3: Bump version (+ optional changelog) ───────────────────────
    changelog_section: Optional[str] = None
    if bump_part is not None:
        bump_label = f"bump: {format_version(old_ver)} → {new_ver_str}"
        if do_changelog:
            bump_label += " + CHANGELOG.md"
        _step(bump_label)

        if not dry_run:
            # Gather commits AFTER the feature commit (HEAD now includes it)
            last_tag = get_last_tag(cwd)
            commits_for_log = get_commits_since_tag(last_tag, cwd)

            write_version(vf, new_ver)
            to_stage = [str(vf)]

            if do_changelog:
                changelog_path = cwd / "CHANGELOG.md"
                changelog_section = format_changelog_section(new_ver_str, commits_for_log)
                update_changelog(changelog_path, changelog_section)
                to_stage.append(str(changelog_path))
                con.info(f"  CHANGELOG.md updated ({len(commits_for_log)} commits)")

            stage_files(to_stage, cwd)
            bump_msg = f"bump: {format_version(old_ver)} → {new_ver_str}"
            try:
                sha = commit(bump_msg, cwd)
            except GitError as exc:
                con.error(str(exc))
                raise SystemExit(1) from exc
            con.success(f"Version {format_version(old_ver)} → {new_ver_str} ({sha})")
        else:
            con.dry_run(f"write {new_ver_str} to {vf}")
            if do_changelog:
                con.dry_run(f"update CHANGELOG.md with commits since last tag")
            con.dry_run(f"git commit -m 'bump: {format_version(old_ver)} → {new_ver_str}'")

    # ── Step 4: Tag ───────────────────────────────────────────────────────
    if do_tag:
        _step(f"Tag: {tag_name}")
        if not dry_run:
            if tag_exists(tag_name, cwd):
                con.warn(f"Tag {tag_name} already exists — skipped")
            else:
                create_tag(tag_name, f"Release {tag_name}", cwd)
                con.success(f"Tag created: {tag_name}")
        else:
            con.dry_run(f"git tag -a {tag_name}")

    # ── Step 5: Push ──────────────────────────────────────────────────────
    if do_push:
        branch = get_current_branch(cwd)
        _step(f"Push {remote}/{branch}" + (" + tags" if do_tag else ""))
        if not dry_run:
            try:
                push(cwd, remote=remote)
                if do_tag:
                    push_tags(cwd, remote=remote)
            except GitError as exc:
                con.error(str(exc))
                raise SystemExit(1) from exc
            con.success(f"Pushed to {remote}/{branch}")
        else:
            con.dry_run(f"git push {remote} {branch}")
            if do_tag:
                con.dry_run(f"git push {remote} --tags")

    # ── Step 6: GitHub release ────────────────────────────────────────────
    if do_release:
        _step(f"GitHub release: {tag_name}")
        # Use changelog section as release notes if available, else fall back to message
        release_notes = changelog_section or message
        if not dry_run:
            try:
                url = create_github_release(tag_name, tag_name, release_notes, cwd)
            except Exception as exc:  # noqa: BLE001
                con.error(f"Release failed: {exc}")
                raise SystemExit(1) from exc
            con.success(f"Release: {url}")
        else:
            con.dry_run(f"gh release create {tag_name} (notes from changelog)")

    # ── Summary ───────────────────────────────────────────────────────────
    con.rule("done" if not dry_run else "dry-run complete")
    if bump_part is not None:
        con.info(f"Version : {format_version(old_ver)} → {new_ver_str}")
    if do_tag and not dry_run:
        con.info(f"Tag     : {tag_name}")
    if dry_run:
        con.info("No changes were made.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_version_file(version_file: Optional[str], repo_root: Path) -> Path:
    if version_file is not None:
        p = Path(version_file)
        return p if p.is_absolute() else (repo_root / p)
    try:
        return find_version_file(repo_root)
    except VersionFileNotFoundError as exc:
        con.error(str(exc))
        raise SystemExit(1) from exc
