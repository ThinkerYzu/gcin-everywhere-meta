# Session 16: Phase 2 — Simplex+Punc (標點簡易)

**Date:** 2026-05-05
**Phase:** Phase 2 (additional input methods)
**Branch:** master

---

## Goals

- Add Simplex+Punctuation (標點簡易) as a sixth IBus engine

## What Was Done

Added `gcin-simplex-punc` following the established `feedkey_gtab_method()` pattern.
`simplex-punc.cin` is in the gcin snapshot; it extends simplex (速成) with punctuation
keys as endkeys (`%endkey` includes `` `\,'[]/.-;,./1234567890-()~!: ``).

Changes:
1. **`gcin-core/gcin-core.h`** — declared `gcin_core_feedkey_simplex_punc()`
2. **`gcin-core/gcin_stubs.cpp`** — added `g_simplex_punc_inmd`; `find_inmd("simplex-punc")` in `gcin_core_init()`; `gcin_core_feedkey_simplex_punc()` delegates to `feedkey_gtab_method()`
3. **`ibus-engine/gcin_engine.c`** — mode 5; `g_str_has_suffix(name, "simplex-punc")` in `enable()`; `case 5` in switch; factory registration
4. **`ibus-engine/component/gcin.xml`** — added `gcin-simplex-punc` entry (symbol: 標)
5. **`gcin-core/test_feedkey.c`** — 2 tests: single char (k→大), escape clears
6. **`Makefile`** — `gcin2tab data/simplex-punc.cin` → `simplex-punc.gtab` in tables target

### Tests

```
Simplex+Punc (標點簡易):
  PASS  simplex-punc: k+space+1 commits 大
  PASS  simplex-punc: escape after partial input does not commit

25 passed, 0 failed, 0 skipped
```

## Key Findings

- **`simplex-punc.cin` has 17,535 characters** (vs 17,457 in plain simplex) — the extra entries are punctuation mappings
- **`%space_style 4`** = `GTAB_space_auto_first_nofull_sel` — same behavior as Cangjie: space shows candidates, digit selects
- **`find_inmd("simplex-punc")` is unambiguous** — `strstr("simplex.gtab", "simplex-punc")` = NULL, so it never matches the plain simplex entry

## Status at End of Session

- 6 IBus engines: gcin-cangjie, gcin-zhuyin, gcin-quick, gcin-array, gcin-cj5, gcin-simplex-punc
- 25/25 unit tests pass

## Next Steps

- Phase 2 is complete for the available gcin snapshot
- **Phase 3: Windows TSF port**

---

**Files Changed:**
- `gcin-core/gcin-core.h` — added `gcin_core_feedkey_simplex_punc()` declaration
- `gcin-core/gcin_stubs.cpp` — `g_simplex_punc_inmd`, init, implementation
- `ibus-engine/gcin_engine.c` — mode 5, enable detection, switch case, factory
- `ibus-engine/component/gcin.xml` — added `gcin-simplex-punc` engine entry
- `gcin-core/test_feedkey.c` — 2 simplex-punc tests
- `Makefile` — `simplex-punc.gtab` in tables target
