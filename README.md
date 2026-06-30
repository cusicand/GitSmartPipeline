# GitSmartPipeline (`gsp`)

A Python CLI for streamlined git workflows — stage, commit, version bump, changelog, tag, push, and release in one command.

## Installation

```bash
conda activate gmc_env   # or: micromamba activate gmc_env
pip install -e "/home/cusicand/05_Devs/GitSmartPipeline/[rich]"

# Verify
gsp --help
gsp --version
```

---

## Commands overview

| Command | What it does |
|---------|-------------|
| `status` | Show version, branch, and pending changes |
| `check` | Pre-release validation: clean tree, version parseable, optional tests |
| `stage` | `git add` files by path or glob |
| `commit` | Commit staged files with a prefixed message |
| `push` | Push commits and/or tags to a remote |
| `bump` | Increment `__version__` in `__init__.py` and commit |
| `tag` | Create an annotated git tag |
| `changelog` | Generate or update `CHANGELOG.md` from commit history |
| `release` | Create a GitHub release via `gh` CLI |
| `ship` | Run all of the above in one command |

---

## Command reference

### `gsp status`

Shows the current state of the repo. No changes are made.

```bash
gsp status [--repo PATH] [--version-file PATH]
```

```
──────────────── gsp status ────────────────
ℹ Branch  : main
ℹ Version : 0.1.0
ℹ Staged  : 0 file(s)
ℹ Modified: 2 file(s)
  geomulticorr/core/pair.py
  geomulticorr/core/session.py
```

---

### `gsp check`

Pre-release validation. Prints a `✓`/`✗` summary and exits with an error if
any check fails. Run this before `ship` when you want to be sure everything is
in order.

```bash
gsp check [--run-tests CMD] [--repo PATH] [--version-file PATH]
```

Checks performed (in order):

1. **Clean working tree** — no uncommitted modifications
2. **No staged changes** — nothing waiting to be committed
3. **Version parseable** — `__version__` found and valid in the version file
4. **Version vs latest tag** — warns if the version already matches a tag (forgot to bump?)
5. **Tests pass** (optional) — runs the command given in `--run-tests`

```bash
# Basic check
gsp check

# With test gate
gsp check --run-tests "pytest tests/ -q"
```

```
────────────── gsp check ──────────────
✓ Working tree is clean
✓ No staged changes
✓ Version 0.1.1 is parseable
✓ Version 0.1.1 differs from latest tag v0.1.0 (ready to release)
✓ Tests passed (pytest tests/ -q)
──────────── ready to release ──────────
```

If the working tree has changes:

```
✗ Working tree has 3 uncommitted change(s)
   M geomulticorr/core/pair.py
   M geomulticorr/core/session.py
   M geomulticorr/inversion/tio_inversion.py
```

---

### `gsp stage`

Runs `git add` on files matching a glob pattern. Does nothing else.

```bash
gsp stage -f GLOB [-f GLOB ...] [--repo PATH]
```

```bash
# Stage a single file
gsp stage -f geomulticorr/core/pair.py

# Stage all .py files in a directory
gsp stage -f "geomulticorr/core/*.py"

# Stage multiple patterns at once
gsp stage -f geomulticorr/core/pair.py -f geomulticorr/core/session.py
```

---

### `gsp commit`

Commits whatever is already staged with a standardized prefixed message.
Fails with a clear error if nothing is staged.

```bash
gsp commit -p PREFIX -m "message body" [--repo PATH]
```

Valid prefixes: `update` · `fix` · `add` · `remove` · `docs` · `test`

The resulting commit message is `"{prefix}: {message body}"`.

```bash
gsp commit -p fix -m "memory leak in pair correlation"
# → commit: "fix: memory leak in pair correlation"

gsp commit -p add -m "TopoCorrection filter"
# → commit: "add: TopoCorrection filter"

gsp commit -p docs -m "add usage examples to README"
# → commit: "docs: add usage examples to README"
```

---

### `gsp push`

Pushes commits (and optionally tags) to a remote.

```bash
gsp push [--remote REMOTE] [--branch BRANCH] [--tags] [--all-tags] [--repo PATH]
```

`--tags` pushes **only the current version's tag** (e.g. `vX.Y.Z`), so it never
errors on tags already present on the remote. Use `--all-tags` for the old
`git push --tags` behaviour (every local tag), which may report harmless
rejections for tags the remote already has.

```bash
# Push current branch to origin
gsp push

# Push the current version's tag (e.g. v0.1.0) — recommended
gsp push --tags

# Push every local tag (legacy behaviour)
gsp push --all-tags

# Push to a different remote
gsp push --remote upstream
```

---

### `gsp bump`

Bumps `__version__` in the package's `__init__.py`, stages that file, and
commits it — all in one step. The version file is auto-detected from
`[tool.hatch.version] path` in `pyproject.toml`.

```bash
gsp bump --part {patch|minor|major} [--version-file PATH] [--repo PATH]
```

| Part | Before | After |
|------|--------|-------|
| `patch` | `0.1.0` | `0.1.1` |
| `minor` | `0.1.0` | `0.2.0` |
| `major` | `0.1.0` | `1.0.0` |

```bash
gsp bump --part patch
# Writes 0.1.1 to geomulticorr/__init__.py
# Stages it
# Commits: "bump: 0.1.0 → 0.1.1"
```

---

### `gsp tag`

Creates an annotated git tag. Defaults to `v{current_version}`.
Silently skips with a warning if the tag already exists.

```bash
gsp tag [--name TAG] [--message MSG] [--version-file PATH] [--repo PATH]
```

```bash
# Tag at the current version (e.g., v0.1.1)
gsp tag

# Custom name and annotation
gsp tag --name v0.2.0-beta --message "Beta release"
```

---

### `gsp changelog`

Generates a new section in `CHANGELOG.md` from all commits since the last git
tag. Commits are grouped by their prefix (`add:`, `fix:`, `update:`, etc.) into
readable categories. Creates the file if it does not exist.

```bash
gsp changelog [--version VER] [--output PATH] [--dry-run] [--repo PATH]
```

```bash
# Preview without writing anything
gsp changelog --dry-run

# Write (or update) CHANGELOG.md
gsp changelog

# Specify a version string for the section header
gsp changelog --version 0.2.0
```

Example output section:

```markdown
## [0.2.0] — 2026-06-12

### Features
- add TopoCorrection filter (abc1234)
- add AlongTrackDestriping to pipeline (def5678)

### Bug Fixes
- fix divide-by-zero on flat terrain in TopoCorrection (ghi9012)

### Improvements
- update sensor_filter in get_pairs() (jkl3456)

### Documentation
- add docstrings to CorrectionPipeline (mno7890)
```

Prefix → category mapping:

| Prefix | Category |
|--------|----------|
| `add` | Features |
| `fix` | Bug Fixes |
| `update` | Improvements |
| `remove` | Removed |
| `docs` | Documentation |
| `test` | Testing |

---

### `gsp release`

Creates a GitHub release via the `gh` CLI for a given tag.
Requires `gh auth login` to have been run once.
If `--notes` is omitted, GitHub auto-generates notes from commit messages.

```bash
gsp release [--tag TAG] [--title TITLE] [--notes TEXT] [--repo PATH]
```

```bash
# Release using the current version tag, auto-generated notes
gsp release

# With custom release notes
gsp release --tag v0.1.1 --notes "Fixed outlier filter and added TopoCorrection"
```

---

### `gsp ship` — the main command

Orchestrates all steps in a fixed order:

```
1. stage        →  git add your files
2. commit       →  git commit "prefix: message"
3. bump         →  write new version + optionally update CHANGELOG.md
                   git commit "bump: x.y.z → a.b.c"
4. tag          →  git tag -a vA.B.C
5. push         →  git push origin main  +  git push origin vA.B.C
6. release      →  gh release create vA.B.C
```

Steps 3–6 only run if `--bump` or `--auto-bump` is specified.

```bash
gsp ship -f FILE [-f FILE ...] -m "message" [OPTIONS]
```

| Flag | Default | Effect |
|------|---------|--------|
| `--bump {patch,minor,major}` | — | Bump version manually (activates steps 3–6) |
| `--auto-bump` | off | Auto-determine `patch`/`minor` from commit history |
| `--update-changelog` | off | Include a `CHANGELOG.md` update in the bump commit |
| `--prefix {update,fix,...}` | `fix` | Conventional commit prefix |
| `--no-push` | off | Skip push **and** release |
| `--no-tag` | off | Skip tag and release |
| `--no-release` | off | Skip GitHub release only |
| `--remote` | `origin` | Push target |
| `--dry-run` | off | Print all steps, make no changes |

**`--auto-bump`** analyzes every commit since the last tag:
- Any `add:` commit → `minor`
- All other prefixes → `patch`

**`--update-changelog`** collects commits since the last tag, formats them into
a `CHANGELOG.md` section, and stages the file alongside the version bump.
When `--update-changelog` is active, the generated changelog section is also
used as the body of the GitHub release.

---

## Daily use examples

### Check what has changed

```bash
cd /home/cusicand/05_Devs/GeoMultiCorr
gsp status
```

### Verify the repo is ready before releasing

```bash
gsp check
# or with a test gate:
gsp check --run-tests "pytest tests/ -q"
```

### Fix a bug in a single file

```bash
gsp ship -f geomulticorr/core/pair.py \
         -m "fix memory leak in pair correlation"
# → stages pair.py
# → commit: "fix: fix memory leak in pair correlation"
# → no version bump, no tag, no release
```

### Fix a bug in multiple files

```bash
gsp ship -f geomulticorr/core/pair.py \
         -f geomulticorr/core/session.py \
         -m "fix session not closing on error"
```

### Add a new feature

```bash
gsp ship -f geomulticorr/corrections/corrections.py \
         -f geomulticorr/corrections/masks.py \
         -m "add SlopeMask to correction pipeline" \
         --prefix add
```

### Update documentation

```bash
gsp ship -f geomulticorr/core/pair.py \
         -m "add docstrings to pair correlation methods" \
         --prefix docs
```

### Add a new module (new file)

```bash
gsp ship -f geomulticorr/corrections/topo_correction.py \
         -m "add TopoCorrection filter class" \
         --prefix add
```

### Stage all modified Python files at once

```bash
gsp ship -f "geomulticorr/**/*.py" \
         -m "update sensor filter across pipeline" \
         --prefix update
```

### Commit without pushing (e.g., working offline)

```bash
gsp ship -f geomulticorr/inversion/tio_inversion.py \
         -m "refactor inversion matrix assembly" \
         --prefix update \
         --no-push
```

### Preview everything before running (dry run)

Always a good habit before a release:

```bash
gsp ship -f geomulticorr/corrections/corrections.py \
         -m "add AlongTrackDestriping to pipeline" \
         --auto-bump --update-changelog \
         --dry-run
```

```
ℹ Auto-bump: minor (from 12 commit(s) since v0.1.0)
─────────────── dry-run preview ───────────────
[1/4] Staging 1 pattern(s): geomulticorr/corrections/corrections.py
(dry-run) git add geomulticorr/corrections/corrections.py
[2/4] Commit: 'fix: add AlongTrackDestriping to pipeline'
(dry-run) git commit -m 'fix: add AlongTrackDestriping to pipeline'
[3/4] bump: 0.1.0 → 0.2.0 + CHANGELOG.md
(dry-run) write 0.2.0 to geomulticorr/__init__.py
(dry-run) update CHANGELOG.md with commits since last tag
(dry-run) git commit -m 'bump: 0.1.0 → 0.2.0'
[4/4] Tag: v0.2.0
(dry-run) git tag -a v0.2.0
───────────────── dry-run complete ─────────────────
ℹ Version : 0.1.0 → 0.2.0
ℹ No changes were made.
```

---

## Release workflows

### Patch release — one file changed

A small bug fix that is ready to ship:

```bash
gsp ship -f geomulticorr/core/pair.py \
         -m "fix outlier filter edge case on masked arrays" \
         --bump patch
```

Commits produced:
```
fix: fix outlier filter edge case on masked arrays
bump: 0.1.0 → 0.1.1
```
Then tags `v0.1.1`, pushes, and opens a GitHub release.

---

### Patch release with automatic changelog

Same as above, but also generates `CHANGELOG.md` and uses it as the release body:

```bash
gsp ship -f geomulticorr/core/pair.py \
         -m "fix outlier filter edge case on masked arrays" \
         --bump patch --update-changelog
```

---

### Minor release — let gsp decide the bump level

During development you commit normally (no bump, no release):

```bash
# Day 1 — add a new filter
gsp ship -f geomulticorr/corrections/corrections.py \
         -m "add TopoCorrection filter" \
         --prefix add

# Day 2 — fix a bug in it
gsp ship -f geomulticorr/corrections/corrections.py \
         -m "fix TopoCorrection divide-by-zero on flat terrain"

# Day 3 — update the notebook
gsp ship -f notebooks/GMC_Corrections.ipynb \
         -m "add TopoCorrection example to corrections notebook" \
         --prefix docs
```

When everything is ready, let `gsp` decide the bump level automatically:

```bash
gsp ship -f geomulticorr/corrections/corrections.py \
         -m "finalize TopoCorrection and destriping pipeline" \
         --auto-bump --update-changelog
# ℹ Auto-bump: minor (because "add:" commits were found since last tag)
# → bumps 0.1.x → 0.2.0, updates CHANGELOG.md, tags v0.2.0, pushes, releases
```

---

### Minor release — manual bump level

```bash
gsp ship -f geomulticorr/corrections/corrections.py \
         -m "finalize TopoCorrection and destriping pipeline" \
         --bump minor --update-changelog
```

---

### Major release — breaking API change

```bash
gsp ship -f geomulticorr/core/session.py \
         -f geomulticorr/core/pair.py \
         -f geomulticorr/core/pzone.py \
         -m "rename open_session to open_gmc_session across API" \
         --prefix update \
         --bump major --update-changelog
```

Bumps `0.x.y → 1.0.0`.

---

### Release with no new file changes

All changes are already committed; you just want to bump, update changelog,
tag, push, and release:

```bash
# Step 1: generate changelog preview
gsp changelog --dry-run

# Step 2: bump version, write CHANGELOG.md, commit, tag, push, release
gsp bump --part minor
gsp changelog
gsp tag
gsp push --tags
gsp release --notes "Release 0.2.0 — adds TopoCorrection and destriping filters"
```

---

### Release without publishing to GitHub

Tag and push locally, but skip the GitHub release page:

```bash
gsp ship -f geomulticorr/core/pair.py \
         -m "fix raster alignment in pair extraction" \
         --bump patch --no-release
```

---

### Full recommended release workflow

```bash
# 1. Check everything is clean and tests pass
gsp check --run-tests "pytest tests/ -q"

# 2. Preview what gsp would do
gsp ship -f geomulticorr/core/pair.py \
         -m "add destriping pipeline" \
         --auto-bump --update-changelog --dry-run

# 3. Ship it
gsp ship -f geomulticorr/core/pair.py \
         -m "add destriping pipeline" \
         --auto-bump --update-changelog
```

---

## Commit prefix guide

| Prefix | When to use | Auto-bump effect | Example message |
|--------|-------------|-----------------|-----------------|
| `add` | New file, class, or feature | `minor` | `add TopoCorrection filter` |
| `fix` | Bug fix | `patch` | `fix outlier filter on masked arrays` |
| `update` | Change to existing code | `patch` | `update sensor_filter in get_pairs()` |
| `remove` | Delete code or files | `patch` | `remove deprecated draw_polygon_manually` |
| `docs` | Documentation only | `patch` | `add docstrings to CorrectionPipeline` |
| `test` | Tests only | `patch` | `add unit tests for version_ops` |
