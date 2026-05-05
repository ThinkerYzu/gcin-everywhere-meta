# Session 11: GitHub Setup and Top-Level Makefile

**Date:** 2026-05-05
**Phase:** Post-Phase-1 housekeeping
**Branch:** master

---

## Goals

- Publish repos to GitHub
- Simplify the build workflow with a top-level Makefile

## What Was Done

### GitHub repos created

- **ThinkerYzu/gcin** — fork of `pkg-ime/gcin`; local modifications (GCIN_CORE_BUILD
  guards) pushed to it; submodule URL in gcin-everywhere updated to point to this fork
- **ThinkerYzu/gcin-everywhere** — new repo; local master pushed; tracking set to
  `origin/master`

### Top-level Makefile (`Makefile`)

Added to the repo root. Orchestrates the full pipeline via sub-makes:

| Target | What it does |
|--------|-------------|
| `make all` | Build `libgcin-core.a` + `ibus-engine-gcin` |
| `make tables` | Build table tools (gcin2tab, phoa2d, tsa2d32, kbmcv) and compile data tables to `./tables/` |
| `make test` | `make tables` + run 9 unit tests |
| `make install` | `make tables` + deploy to `~/.local/` via `ibus-engine/Makefile install` |
| `make clean` | Remove all build artifacts and `tables/` directory |

Full install workflow from a fresh clone is now:
```bash
git clone --recurse-submodules https://github.com/ThinkerYzu/gcin-everywhere.git
cd gcin-everywhere
make test && make install
```

### .gitignore

Added `.gitignore` to exclude build artifacts:
`tables/`, table tool binaries in `gcin/`, object files and library in `gcin-core/`,
and `ibus-engine/ibus-engine-gcin`.

### README simplified

The verbose manual build steps in the README were replaced with the two-command flow:
```bash
make test
make install
```

## Status at End of Session

- Both repos live on GitHub under ThinkerYzu
- `make test` runs cleanly (9/9 pass) from the repo root
- `make install` handles the complete deployment
- README accurately reflects the current build process

---

**Files Changed (source repo):**
- `Makefile` — new: top-level build orchestration
- `.gitignore` — new: excludes build artifacts
- `README.md` — simplified build and install sections
- `.gitmodules` — gcin submodule URL updated to ThinkerYzu/gcin
