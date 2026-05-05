# Session 7: Phase 3 — Cangjie Working End-to-End

**Date:** 2026-05-05
**Phase:** Phase 3 complete
**Branch:** master

---

## Goals

- Wire `process_key_event` → `gcin_core_feedkey_cangjie()` with preedit and candidates
- Verify `ko` → preedit shows 大, candidates appear, select commits 大人

## What Was Done

### gcin-core API additions

Added two new functions to `gcin-core.h` and implemented in `gcin_stubs.cpp`:

**`gcin_core_get_preedit(char *out, int outlen)`** — calls `get_DispInArea_str()` (gtab.cpp:376) which reads `ggg.inch[]` key-name glyphs accumulated so far. Returns byte count.

**`gcin_core_get_candidates_cangjie(char (*cands)[32], int max_n)`** — reads `seltab[0..M_DUP_SEL-1]` directly (defined in `gtab-init.cpp`, accessible via `extern char **seltab`). Bypasses the HTML-formatted `disp_gtab_sel` string entirely.

### gcin_engine.c — Phase 3 implementation

Rewrote `process_key_event` and added `update_ui()`:

- `update_ui()`: calls `gcin_core_get_preedit()` → `ibus_engine_update_preedit_text()`; calls `gcin_core_get_candidates_cangjie()` → populates `IBusLookupTable` → `ibus_engine_update_lookup_table()`
- `on_commit()`: callback that calls `ibus_engine_commit_text()` 
- `gcin_engine_reset()` / `gcin_engine_focus_out()`: now also call `ibus_engine_hide_preedit_text()` and `ibus_engine_hide_lookup_table()`

### Key design decision: callback re-registration

`gcin_core_set_commit_cb(on_commit, iengine)` is called at the start of every `process_key_event` rather than once at engine init. Reason: gcin has a single global commit callback; if multiple engine instances exist, the last-active one must be the target.

## Key Findings

- `seltab` is defined in `gtab-init.cpp` (not `gtab.cpp`); `extern char **seltab` in `gcin_stubs.cpp` resolves correctly at link time
- `disp_gtab_sel()` receives HTML-formatted strings (with `<span>` tags) — reading `seltab[]` directly is far simpler than parsing that output
- `gcin_core_get_preedit` needs a 512-byte buffer; `get_DispInArea_str` writes key-name glyphs (each up to 3 bytes UTF-8) for up to `ggg.ci` keystrokes

## Status at End of Session

- Cangjie input works end-to-end: preedit updates, candidates show, selection commits
- 6/6 unit tests still pass
- Zhuyin routing is wired (`gcin_core_feedkey_zhuyin` exists) but preedit display not yet implemented

## Next Steps

- Phase 4 — Zhuyin: expose preedit from `poo.typ_pho[]` via `phokey_to_str()`; test `vu4` → commits 住

---

**Files Changed:**
- `gcin-core/gcin-core.h` — added `gcin_core_get_preedit()`, `gcin_core_get_candidates_cangjie()`
- `gcin-core/gcin_stubs.cpp` — implemented both new API functions
- `ibus-engine/gcin_engine.c` — full Phase 3 implementation: commit callback, update_ui(), wired process_key_event
