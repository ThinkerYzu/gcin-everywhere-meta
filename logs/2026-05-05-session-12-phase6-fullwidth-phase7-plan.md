# Session 12: Phase 6 — Full-Width Mode; Phase 7 Planned

**Date:** 2026-05-05
**Phase:** Phase 6 complete; Phase 7 planned
**Branch:** master

---

## Goals

- Implement full-width character mode (Shift+Space toggle)
- Investigate and plan Alt+Shift / Ctrl+key special character support

## What Was Done

### Phase 6 — Full-width character mode

Implemented gcin's Shift+Space toggle exactly as gcin does it:

**`half_char_to_full_char()` copied from `gcin.cpp`** (excluded — conflicts with our
stubs for `dpy`/`root`/`win_xl` and contains `main()`). One-liner into `fullchar[]`
already compiled from `fullchar.cpp`. Zero X11/GTK dependencies.

**`full_char_proc()` copied from `eve.cpp`** (excluded — XTest/GDK and hundreds of
X11-dependent functions). TSIN-mode and phrase-buffer branches omitted (inactive in our
build). Calls `half_char_to_full_char()` → `utf8cpy()` → `send_text()`.

**`gcin_core_toggle_full_width()` / `gcin_core_get_full_width()`** added to public API.
Mirrors `toggle_half_full_char()` in `eve.cpp` (omitting display-update side effects).

**Shift+Space in `gcin_engine.c`**: intercepted before feedkey routing using
`IBUS_space` + `IBUS_SHIFT_MASK` (not `XK_space` — learned from a compile error).

**Test**: `test_cangjie_full_width()` — comma in half-width mode is not consumed by
engine (passes through to app); comma in full-width mode commits `，`. 11/11 pass.

**One fix during testing**: test incorrectly expected `,` to be committed in half-width
mode. In half-width, `feedkey_gtab` returns 0 (not consumed) and IBus passes the key
to the application directly — our callback is never called.

### Phase 7 planning — Alt+Shift and Ctrl phrase tables

Investigation of gcin's `eve.cpp` revealed two more special-character mechanisms
beyond full-width mode:

1. **Alt+Shift+key** → `feed_phrase(keysym, Mod1Mask|ShiftMask)` → `phrase.table`
2. **Ctrl+key** → `feed_phrase(keysym, ControlMask)` → `phrase-ctrl.table`

Both go through `feed_phrase()` in `phrase.cpp` — **already compiled** into
`libgcin-core.a`, no copy needed, no X11/GTK dependencies. `feed_phrase()` routes to
the right table based on `ControlMask`.

Also noted: `zxac` = `、`, `zxal` = `…`, `zxay` = `—` etc. are standard Cangjie
codes in `cj.gtab` — these already work without any new code.

Design decision 7 and Phase 7 implementation plan documented in DESIGN.md and
IMPLEMENTATION-GUIDE.md.

## Key Findings

- `IBUS_space` not `XK_space` in IBus engine context (`XK_space` is undefined there)
- Half-width mode: non-component keys are NOT consumed by the engine; they pass through
  to the app via IBus. Only full-width mode routes them through `send_text()`.
- `phrase.cpp` is already in GCIN_SRCS — `feed_phrase()` needs only an `extern`
  declaration wrapper, not a copy
- `cj.gtab` already contains `zx__` codes for all common Chinese punctuation — users
  who know Cangjie already have direct access to `、`, `…`, `—`, etc.

## Status at End of Session

- Phase 6 complete: Shift+Space toggles full-width mode; 11/11 tests pass
- Phase 7 plan complete: design decision 7 + IMPLEMENTATION-GUIDE Phase 7 written
- Code pushed to github.com/ThinkerYzu/gcin-everywhere

## Next Steps

- Phase 7 implementation: `gcin_core_feed_phrase()` wrapper + Alt+Shift + Ctrl intercepts in engine + install phrase tables

---

**Files Changed (source):**
- `gcin-core/gcin_stubs.cpp` — copy `half_char_to_full_char` + `full_char_proc`; add `gcin_core_toggle_full_width/get_full_width`
- `gcin-core/gcin-core.h` — add toggle/get full-width API
- `gcin-core/test_feedkey.c` — add `test_cangjie_full_width()`
- `ibus-engine/gcin_engine.c` — handle Shift+Space with `IBUS_space`/`IBUS_SHIFT_MASK`
