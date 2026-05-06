# Session 15: Phase 2 — CJ5 (倉頡五代) Input Method

**Date:** 2026-05-05
**Phase:** Phase 2 (additional input methods)
**Branch:** master

---

## Goals

- Add CJ5 (倉頡五代) as a fifth IBus engine, following the same `feedkey_gtab_method()` pattern as Quick and Array

## What Was Done

### CJ5 engine added

Buxiemi (嘸蝦米) — the originally planned next method — is absent from the gcin snapshot (`noseeing.gtab` not in `data/`). CJ5 (`cj5.cin`) is available and is widely used among Traditional Chinese speakers (many prefer CJ5 over CJ3 for its larger character coverage: 74,944 characters vs 13,209 in CJ3).

All changes follow the established `feedkey_gtab_method()` adapter pattern:

1. **`gcin-core/gcin-core.h`** — declared `gcin_core_feedkey_cj5()`
2. **`gcin-core/gcin_stubs.cpp`** — added `g_cj5_inmd`; `find_inmd("cj5")` in `gcin_core_init()`; `gcin_core_feedkey_cj5()` delegates to `feedkey_gtab_method(g_cj5_inmd, ...)`
3. **`ibus-engine/gcin_engine.c`** — mode 4; `g_str_has_suffix(name, "cj5")` in `enable()`; `case 4` in `process_key_event` switch; `ibus_factory_add_engine("gcin-cj5", ...)`
4. **`ibus-engine/component/gcin.xml`** — added `<engine>` entry for `gcin-cj5` (symbol: 五)
5. **`gcin-core/test_feedkey.c`** — 3 CJ5 tests: single char (k→大), two char (ab→明), escape clears
6. **`Makefile`** — `gcin2tab data/cj5.cin` → `cj5.gtab` in the `tables` target

### Tests

All 23 tests pass (20 from Session 14 + 3 new CJ5 tests). `make test` output:

```
CJ5 (倉頡五代):
  PASS  cj5: k+space+1 commits 大
  PASS  cj5: ab+space+1 commits 明
  PASS  cj5: escape after partial input does not commit

23 passed, 0 failed, 0 skipped
```

## Key Findings

- **`find_inmd("cj5")` is safe alongside `find_inmd("cj")`** — gtab.list lists `cj.gtab` (倉頡) before `cj5.gtab` (倉五), so `find_inmd("cj")` returns the CJ3 index and `find_inmd("cj5")` correctly skips it (strstr("cj.gtab","cj5") = NULL).
- **CJ5 has 74,944 characters** vs 13,209 in CJ3 — compiled table is significantly larger but the same code path handles it transparently.
- **Buxiemi absent** — `noseeing.gtab` not in gcin snapshot. No `.cin` source either.

## Decisions Made

- **CJ5 mode = 4** — extends the existing mode enum; suffix "cj5" detected before the catch-all cangjie default in `enable()`.
- **Symbol = 五** — single-character IBus symbol; matches gcin's 倉五 label visually.

## Status at End of Session

- 5 IBus engines: gcin-cangjie, gcin-zhuyin, gcin-quick, gcin-array, gcin-cj5
- 23/23 unit tests pass
- `make test` and `make install` are the complete workflow
- No blockers

## Next Steps

- Phase 2 is now feature-complete for the available gcin snapshot (Buxiemi absent, Dayi absent)
- **Phase 3: Windows TSF port** — platform layer for Windows using Text Services Framework; `libgcin-core.a` links as-is, only the platform integration layer changes

---

**Files Changed:**
- `gcin-core/gcin-core.h` — added `gcin_core_feedkey_cj5()` declaration
- `gcin-core/gcin_stubs.cpp` — added `g_cj5_inmd`, init in `gcin_core_init()`, `gcin_core_feedkey_cj5()` implementation
- `ibus-engine/gcin_engine.c` — mode 4, enable detection, switch case, factory registration
- `ibus-engine/component/gcin.xml` — added `gcin-cj5` engine entry
- `gcin-core/test_feedkey.c` — 3 CJ5 unit tests + file-presence guard in main()
- `Makefile` — `cj5.gtab` in tables target
