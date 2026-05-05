# Session 8: Phase 4 — Zhuyin Preedit and Candidates

**Date:** 2026-05-05
**Phase:** Phase 4 complete
**Branch:** master

---

## Goals

- Add `gcin_core_get_preedit_zhuyin()` and `gcin_core_get_candidates_zhuyin()` to the API
- Wire `update_ui()` in `gcin_engine.c` to call correct functions based on Cangjie vs Zhuyin mode
- Detect engine mode (Cangjie/Zhuyin) from IBus engine name at init time
- Verify with 3 new unit tests: preedit builds, candidates appear, both clear after commit

## What Was Done

### gcin-core API additions

Added two new functions to `gcin-core.h` and implemented in `gcin_stubs.cpp`:

**`gcin_core_get_preedit_zhuyin(char *out, int outlen)`** — reads `poo.typ_pho[4]`
(the partial phonetic syllable currently being typed), packs it into a `phokey_t` via
`pho2key()`, then converts to display bopomofo characters via `phokey_to_str()`.
Returns byte count. Returns 0 and empty string when phonetic buffer is empty.

**`gcin_core_get_candidates_zhuyin(char (*cands)[32], int max_n)`** — reads
`ch_pho[poo.start_idx + poo.cpg]` through `[...poo.maxi-1]` directly.
`poo.maxi` is set by `feedkey_pho` when candidates are displayed (after a complete
syllable: initial + medial + tone). Returns 0 when no candidates are pending.

### gcin_engine.c — mode detection and Zhuyin preedit/candidates

**Mode detection:** `gcin_engine_init()` now calls `ibus_engine_get_name()` and
sets `e->mode = 1` if the engine name ends with "zhuyin", otherwise `e->mode = 0`.
This means the same GObject type handles both engines with the right behavior.

**`update_ui()`:** Now branches on `e->mode`:
- mode 0 (Cangjie): calls `gcin_core_get_preedit()` + `gcin_core_get_candidates_cangjie()`
- mode 1 (Zhuyin): calls `gcin_core_get_preedit_zhuyin()` + `gcin_core_get_candidates_zhuyin()`

### Unit tests — 3 new Zhuyin API tests

Added to `test_feedkey.c`:
- `test_zhuyin_preedit_builds()` — types j, u, 4; asserts preedit non-empty after j, grows after 4
- `test_zhuyin_candidates_appear_after_tone()` — types j+u+4; asserts candidates count > 0
- `test_zhuyin_preedit_clears_after_commit()` — types j+u+4+1; asserts preedit and candidates both empty

## Key Findings

- **ㄨ is implicit after ㄓ in Daqian** — pressing `u` after `j` (ㄓ) does NOT grow the preedit string. `feedkey_pho` internally handles the ㄨ medial, but `poo.typ_pho[]` doesn't separately reflect it in the phokey. The tone press (4) does grow the preedit.
- **Candidates come from `ch_pho[]` not from `disp_pho_sel` string** — `poo.start_idx + poo.cpg` gives the page start; `poo.maxi` gives count on current page. Mirrors the Cangjie `seltab[]` approach.
- **`poo.maxi` is set before `disp_pho_sel()` call** — so after `feedkey_pho` returns, `poo.maxi` is already valid for reading candidates.

## Status at End of Session

- Zhuyin preedit API works: shows bopomofo syllable as user types
- Zhuyin candidates API works: returns `ch_pho` entries after complete syllable
- `gcin_engine.c` routes preedit/candidates to correct functions based on engine mode
- 9/9 unit tests pass
- End-to-end test (in GNOME with IBus) not yet done

## Next Steps

- Phase 5 — Install: `make install`, enable in GNOME Settings, end-to-end test in gedit for both Cangjie and Zhuyin

---

**Files Changed:**
- `gcin-core/gcin-core.h` — added `gcin_core_get_preedit_zhuyin()`, `gcin_core_get_candidates_zhuyin()`
- `gcin-core/gcin_stubs.cpp` — implemented both new API functions
- `gcin-core/test_feedkey.c` — added 3 Zhuyin API tests (9/9 pass)
- `ibus-engine/gcin_engine.c` — mode detection from engine name; `update_ui()` branches on mode
