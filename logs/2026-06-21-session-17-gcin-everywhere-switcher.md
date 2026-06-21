# Session 17: Phase 10 — Unified Switcher Engine (gcin-everywhere)

**Date:** 2026-06-21
**Phase:** Phase 10 — unified gcin-everywhere switcher engine
**Branch:** master

---

## Goals

- Reproduce gcin's native `Ctrl+Alt+<digit>` input-method switching.
- Expose it as a single new IBus engine, `gcin-everywhere`, that switches between all
  supported methods in place (not Cangjie/Zhuyin/etc. specifically).

## What Was Done

### Studied gcin's native switching mechanism

In `gcin/eve.cpp:1240`, when Ctrl+Alt is held, gcin calls
`gcin_switch_keys_lookup(keysym)` (`gtab-list.cpp:156`) which scans `inmd[]` for the
entry whose `key_ch` (the 2nd column of `gtab.list`) matches the pressed digit, then
`init_in_method(kidx)` switches the active method in-process. The digit assignments in
`gtab.list` are: 1=倉頡, 2=倉五, 3=注音, 8=行列; Quick and SimplexPunc use `-` (no digit).

### Mapped it onto our architecture (no core changes)

Our `gcin_engine.c` already has a mutable `e->mode` + `switch(e->mode)` dispatch, and
the core's per-method feedkey functions already do the `init_gtab()`/`in_method` switch
on first call. So the unified engine simply makes `e->mode` mutable at runtime. All
changes landed in the IBus layer.

### Implemented the gcin-everywhere engine (`ibus-engine/gcin_engine.c`)

- Added struct fields `allow_switch`, `prop`, `props`.
- `digit_to_mode()` maps 1→Cangjie(0), 2→CJ5(4), 3→Zhuyin(1), 4→Quick(2),
  5→SimplexPunc(5), 8→Array(3). (1/2/3/8 mirror gcin; 4/5 are extensions.)
- `process_key_event()`: a Ctrl+Alt+digit handler runs first; on a recognized digit it
  resets composition, hides preedit/lookup, updates `e->mode`, and updates the panel
  property. Unrecognized keys under Ctrl+Alt return FALSE (pass through to the app).
- `gcin_engine_enable()`: name ending in `everywhere` → `allow_switch = TRUE`,
  starts in Cangjie, registers the panel property. Single-method engines unchanged.
- Panel property (`IBusProperty`, type `PROP_TYPE_NORMAL`) shows the active method's
  glyph (倉/注/速/列/五/標) via `ibus_property_set_symbol/_label`; re-registered on
  `focus_in` since IBus clears panel props across focus changes.
- Registered `gcin-everywhere` in the factory; added the `<engine>` block (symbol 全)
  to `component/gcin.xml`.

### Tests

Added a "Method switching" section to `test_feedkey.c` (2 tests, 4 assertions) that
reproduces the engine's switch sequence at the core level — `reset()` then route to a
different method — guarding against stale `init_gtab`/`in_method` state across a switch.
**29/29 pass** (`GCIN_TABLE_DIR=../tables ./test_feedkey`).

### Docs

Updated SPEC.md (FR8 + success criterion), DESIGN.md (decision 8),
IMPLEMENTATION-GUIDE.md (Phase 10).

## Key Findings

- The unified engine needs **zero** gcin-core changes — the core already supports
  per-keypress method switching; only the IBus layer's `e->mode` needed to become
  runtime-mutable.
- IBus clears registered panel properties on focus change, so properties must be
  re-registered in a `focus_in` handler, not only in `enable()`.
- The extracted libibus dev headers (`/tmp/ibus-dev-extract`) from earlier sessions
  were gone; re-fetched with `apt-get download libibus-1.0-dev` + `dpkg-deb -x`
  (IBus 1.5.32). `ibus_property_set_symbol` is available (≥1.5).
- Prebuilt tables live in the repo at `tables/`; tests run against them directly with
  `GCIN_TABLE_DIR=../tables` (no `make tables` rebuild needed here).

## Decisions Made

- **Switching gated to gcin-everywhere only** — the six single-method engines stay fixed
  so their IBus panel label remains accurate. Confirmed with the user.
- **Digit extensions 4=Quick, 5=SimplexPunc** — gcin leaves these on `-`; we assign
  spare digits for convenience while preserving gcin's 1/2/3/8. Confirmed with the user.
- **Panel property for visual feedback** — registers one IBusProperty and updates its
  symbol on each switch so the GNOME panel shows the live method. Confirmed with the user.

## Deployment finding — component XML must be system-wide

After install, `ibus list-engine` showed only `gcin-cangjie` + `gcin-zhuyin` (stale), and
`gcin-everywhere` never appeared. Root cause: **ibus-daemon scans only the system XDG
data dirs (`/usr/share/ibus/component`), not `~/.local/share/ibus/component`** (verified:
973 engines loaded, 0 from `~/.local`). Compounding it, two components shared the name
`org.freedesktop.IBus.Gcin` — a stale 2-engine `/usr/share/ibus/component/gcin.xml`
shadowed the up-to-date 7-engine user file. Earlier sessions only "worked" because that
stale system file existed.

**Fix (confirmed working by the user):**
```
sudo cp ~/.local/share/ibus/component/gcin.xml /usr/share/ibus/component/gcin.xml
ibus write-cache && ibus restart
```
The Makefile `install` target was updated to install the component to `$(COMPDIR)`
(default `/usr/share/ibus/component`, via `sudo`) and run `ibus write-cache`/`ibus
restart`. The binary, tables, and systemd service remain user-local; the system
component just points `<exec>` at the user binary.

## Feature — Ctrl+Space English toggle (replaces desktop source-switching for English)

User reported Ctrl+Space needed **two presses** to switch to/from English, and that it
happened symmetrically (English→gcin too). Since English (xkb `us`) has no engine running,
that ruled out the engine as the cause: it was a desktop-level double-binding of plain
`Ctrl+Space` — GNOME `switch-input-source[-backward]` **and** IBus's legacy
`general.hotkey.trigger` both grabbed it, so they fought (one press toggled the IBus
trigger, the next switched the source).

Resolution (chosen with the user): implement the **gcin-native in-engine English toggle**
instead of relying on desktop source-switching.

- **Engine:** in `gcin-everywhere`, `Ctrl+Space` flips `e->chinese_mode` (Chinese ↔
  English passthrough). `e->mode` is preserved, so toggling back resumes the last method.
  Handler placed before the `if (!chinese_mode) return FALSE` early-return so it can
  re-enable Chinese; `Ctrl+Alt+digit` also sets `chinese_mode = TRUE`. Panel shows 英 in
  English. Single-method engines return FALSE for Ctrl+Space (desktop handles it).
- **Desktop config (required):** mutter checks shortcuts before the engine, so plain
  `Ctrl+Space` was freed — `switch-input-source` → `<Shift><Control>space`,
  `switch-input-source-backward` → `[]`, and `Control+space` removed from the IBus
  `trigger`.

Confirmed working by the user: single-press Chinese ↔ English in gcin-everywhere.

## Status at End of Session

- Working & user-confirmed: engine builds clean; 29/29 unit tests pass; all 7 engines
  appear in `ibus list-engine`; gcin-everywhere selectable; `Ctrl+Alt+1/2/3/4/5/8`
  switches method in place; `Ctrl+Space` toggles Chinese ↔ English (panel 英).
- No regressions in the existing 6 engines (their code paths are untouched).

## Next Steps

- Resume Phase 3 (Windows TSF port).

---

**Files Changed:**
- `ibus-engine/Makefile` — install component to system dir `$(COMPDIR)` (default `/usr/share/ibus/component`) via sudo; run `ibus write-cache`/`ibus restart` (deployment fix)
- `ibus-engine/gcin_engine.c` — Ctrl+Space in-engine English toggle (`chinese_mode`, panel 英); unified engine: `allow_switch`/property fields,
  `mode_symbol()`, `digit_to_mode()`, `ensure_property()`, `update_property()`,
  Ctrl+Alt+digit handler, `everywhere` detection, `focus_in` re-register, factory entry
- `ibus-engine/component/gcin.xml` — added `gcin-everywhere` engine (symbol 全)
- `gcin-core/test_feedkey.c` — added 2 method-switch tests (4 assertions); 29 total
- `SPEC.md` — FR8 (unified switcher) + success criterion 6
- `DESIGN.md` — decision 8 (unified switcher engine)
- `IMPLEMENTATION-GUIDE.md` — Phase 10
