# Session 9: Phase 5 — Local Install and Systemd Autostart

**Date:** 2026-05-05
**Phase:** Phase 5 complete
**Branch:** master

---

## Goals

- Install engine to `~/.local/` (no root required)
- Get engine working end-to-end in GNOME with IBus

## What Was Done

### Local install target (Makefile)

Added `install` target to `ibus-engine/Makefile`. Installs to `$(PREFIX)` = `~/.local/` by default:
- Binary → `~/.local/lib/ibus-gcin/ibus-engine-gcin`
- Data tables → `~/.local/share/gcin/` (copied from `TABLES ?= /tmp/gcin-tables`)
- Component XML → `~/.local/share/ibus/component/gcin.xml` (exec path rewritten via `sed`)
- Systemd service → `~/.config/systemd/user/ibus-engine-gcin.service` (enabled + started)

Workflow after any code change: `make install && systemctl --user restart ibus-engine-gcin`

### Three bugs fixed during install testing

**Bug 1: `pho_load()` ignores `TableDir`, checks `GCIN_TABLE_DIR` env var**

`pho-util.cpp:pho_load()` branches on `!getenv("GCIN_TABLE_DIR")` to decide whether
to use the user-local `~/.gcin/pho.tab2` or the system table. Setting `TableDir`
programmatically is not enough. Fix: `gcin_core_init()` now also calls
`setenv("GCIN_TABLE_DIR", table_dir, 1)`.

**Bug 2: `gcin_core_init()` was called after `ibus_bus_request_name()`**

Table loading blocks the event loop. When IBus daemon sends "CreateEngine" during
table load, the engine doesn't respond and the daemon times out. Fix: moved
`gcin_core_init()` to run before `ibus_bus_new()`, so tables are loaded before
connecting to IBus.

**Bug 3: GNOME Shell doesn't auto-spawn user-local IBus engines**

GNOME Shell's IBus integration only auto-spawns engines from `/usr/share/ibus/component/`.
Engines installed to `~/.local/share/ibus/component/` appear in `ibus list-engine`
but are never exec'd by GNOME. Fix: systemd user service starts the engine at login.
IBus finds the already-running process when the user switches engines.

### Systemd user service

`ibus-engine/ibus-engine-gcin.service` added to source tree. `make install` deploys
it to `~/.config/systemd/user/` and runs `systemctl --user enable --now`. The service
restarts on failure (RestartSec=5) and starts after `graphical-session.target`.

## Key Findings

- `~/.local/share/ibus/component/` works for listing but not for GNOME auto-spawn
- `pho_load()` in `pho-util.cpp` checks `getenv("GCIN_TABLE_DIR")` not `TableDir`
- `gcin_core_init()` must complete before connecting to IBus (move before `ibus_bus_new()`)
- Systemd user service is the clean solution: no root required, auto-restarts, starts at login

## Status at End of Session

- Engine installs cleanly to `~/.local/` with `make install`
- Engine auto-starts at login via systemd user service
- Switching to gcin Cangjie in GNOME works end-to-end
- Zhuyin switching also works (engine handles both)
- 9/9 unit tests pass

## Next Steps

- End-to-end typing test: Cangjie `ko` → 大人, Zhuyin `ju4` → 住
- Then project is feature-complete for Phase 1

---

**Files Changed:**
- `gcin-core/gcin_stubs.cpp` — `gcin_core_init()` calls `setenv("GCIN_TABLE_DIR", ...)` + moved before IBus connect
- `ibus-engine/gcin_engine.c` — `gcin_core_init()` moved before `ibus_bus_new()`; added `<stdio.h>`
- `ibus-engine/Makefile` — added `install` target with systemd service support
- `ibus-engine/ibus-engine-gcin.service` — new: systemd user service template
