# Session 18: Phase 11 — GNOME Panel Indicator for gcin-everywhere

**Date:** 2026-06-22
**Phase:** Phase 11 — GNOME Shell extension showing the active method
**Branch:** master

---

## Goals

- Give the user a visible indicator of which input method `gcin-everywhere` is
  currently in (it was impossible to tell — the panel only ever showed 全).
- Detect the environment and show the indicator **only** when the unified switcher
  engine is the active source.

## The problem

`gcin-everywhere` is a **single** IBus engine that switches method internally. GNOME
Shell's built-in top-bar input indicator renders only an engine's **static `symbol` from
its component XML** (全 for gcin-everywhere) and **ignores live `IBusProperty` symbol
updates**. So the `ibus_engine_update_property()` calls the engine already makes (flipping
倉→注→速…) are a no-op *on GNOME* — they work on KDE / the standalone `ibus-ui-gtk3` panel,
but not GNOME Shell. Result: the user could not tell the active method.

Considered and rejected: a notification-on-switch toast (user: "too annoying"); an
SNI/AppIndicator tray icon (also needs a GNOME extension to render on stock GNOME, so a
native panel indicator is strictly simpler).

## What was done — file-fed GNOME Shell extension

Chose a **state-file + GNOME Shell extension** design (no polling, no new C deps,
coexists with the existing IBus property):

### Engine side (`ibus-engine/gcin_engine.c`)

- Added `mode_label()` (readable name per mode, e.g. `注音 Zhuyin`).
- Added `write_state(e, active)`: writes `$XDG_RUNTIME_DIR/gcin-everywhere/state` with
  `"<glyph>\t<label>"` while active, or **empty** when disabled. Gated on `allow_switch`
  (no-op for the 6 single-method engines).
- `update_property()` now also calls `write_state(e, TRUE)` — so the file tracks every
  switch, enable, and focus-in (all already route through `update_property`).
- `gcin_engine_disable()` now calls `write_state(ge, FALSE)` — clears the file when the
  user switches away, so the indicator disappears.

### Extension (`gnome-extension/gcin-everywhere@gcin.dev/`)

- `extension.js` (GNOME 45+ ESM): a `PanelMenu.Button` holding an `St.Label`. A
  `Gio.FileMonitor` on the state **directory** (robust to atomic replacement) fires on
  change; `_refresh()` reads the file and sets the glyph + shows the button, or hides it
  when the file is empty/absent. A non-interactive menu line shows the full method name.
- `metadata.json` (shell-version 45–49), `stylesheet.css` (bold, padded label).

### Build (`Makefile`)

- New `install-extension` target copies the extension to
  `~/.local/share/gnome-shell/extensions/gcin-everywhere@gcin.dev/` (user-local, no sudo);
  `install` now depends on it.

## Verification

- Engine binary rebuilt and confirmed to contain the new code; **state file verified**
  end-to-end via `ibus engine` switching:
  - gcin-everywhere active → `倉\t倉頡 Cangjie`
  - switched to English (`xkb:us::eng`) → file emptied (indicator will hide)
  - back to gcin-everywhere → repopulated
- `extension.js` passes `node --check` (ESM syntax); `metadata.json` valid.

## Key findings

- **GNOME Shell ignores IBus property symbol updates** — confirmed root cause of "only 全
  shows". An external indicator (extension) is the only GNOME-native fix for a
  single-engine switcher; the IBus property still serves KDE / standalone panel.
- **Stale daemon-spawned engine can own the bus name.** After `systemctl restart`, an old
  engine process (started the prior day, exe shown as `(deleted)`, spawned outside
  systemd's cgroup) still held `org.freedesktop.IBus.Gcin`. The new process requested the
  name with flag 0 (no replace) and stayed idle, so the **old code kept serving** and no
  state file appeared. Fix: `kill` the stale PID, `systemctl --user restart`, `ibus
  restart`. (Possible future hardening: request the name with
  `IBUS_BUS_NAME_FLAG_REPLACE_EXISTING | ALLOW_REPLACEMENT`.)
- **Wayland needs logout/login** for GNOME Shell to pick up a newly-installed extension —
  the shell can't be reloaded live on Wayland (Alt+F2 `r` is X11-only).

## Decisions made

- **State file over D-Bus signal** — a tiny file watched via `Gio.FileMonitor` is
  inotify-driven (no polling) and needs zero new D-Bus plumbing in the C engine.
- **Coexist with the IBus property, no environment detection in C** — the engine always
  writes both; whichever the desktop supports renders (GNOME → extension; KDE/standalone →
  property). The extension's mere existence is the "GNOME detection".
- **Visibility tied to engine enable/disable** — file populated on `enable`, emptied on
  `disable`, so the indicator shows **only** while gcin-everywhere is the active source.

## Status at end of session

- Engine half verified working. Extension installed and syntax-valid; **pending the
  user's logout/login** on Wayland + `gnome-extensions enable gcin-everywhere@gcin.dev`
  for live confirmation in the panel.
- No regressions: single-method engines never call `write_state` (gated on `allow_switch`).

## Next steps

- User: log out/in, enable the extension, confirm the glyph appears and updates live.
- Phase 3 (Windows TSF port) remains the next platform milestone.

---

**Files Changed:**
- `ibus-engine/gcin_engine.c` — `mode_label()`, `write_state()`, write on `update_property`, clear on `disable`; `#include <glib/gstdio.h>`
- `gnome-extension/gcin-everywhere@gcin.dev/{extension.js,metadata.json,stylesheet.css}` — new GNOME Shell indicator extension
- `Makefile` — `install-extension` target; `install` depends on it
- `README.md` (source) — corrected the misleading "GNOME panel symbol shows the method" claim; documented the extension + install/enable
