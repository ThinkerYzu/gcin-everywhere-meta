# Session 14: Phase 2 — Quick and Array Input Methods

**Date:** 2026-05-05
**Phase:** Phase 2 (Additional Input Methods)
**Status:** Complete

---

## Navigation

**Project Docs:** [README](../README.md) | [SPEC](../SPEC.md) | [DESIGN](../DESIGN.md) | [IMPLEMENTATION-GUIDE](../IMPLEMENTATION-GUIDE.md) | [HANDOFF](../HANDOFF.md)

---

## Summary

Implemented Phase 2: Quick (速成) and Array (行列) input methods. Both share the same `feedkey_gtab` code path as Cangjie — only the `.gtab` table differs. Added a `feedkey_gtab_method()` helper to switch `cur_inmd` before dispatching. 20/20 unit tests pass. Dayi (大易) was considered but skipped — `dayi3.cin` is not in the gcin source snapshot.

---

## What Was Done

### Step 1 — `gcin_core_feedkey_quick()` and `gcin_core_feedkey_array()` added

Added `g_quick_inmd` and `g_array_inmd` index variables to `gcin-core/gcin_stubs.cpp`. These are set during `gcin_core_init()` using `find_inmd("simplex")` and `find_inmd("ar30")` to locate the Quick and Array entries in `gtab.list`.

Added a shared helper:
```c
static int feedkey_gtab_method(int inmd_idx, unsigned long keyval, int modifiers) {
    cur_inmd = &inmd[inmd_idx];
    init_gtab(inmd_idx);
    return feedkey_gtab((KeySym)keyval, modifiers) ? 1 : 0;
}
```

Public API functions delegate to the helper:
```c
int gcin_core_feedkey_quick(unsigned long keyval, int modifiers) {
    return feedkey_gtab_method(g_quick_inmd, keyval, modifiers);
}
int gcin_core_feedkey_array(unsigned long keyval, int modifiers) {
    return feedkey_gtab_method(g_array_inmd, keyval, modifiers);
}
```

### Step 2 — `gcin-core/gcin-core.h` updated

Added declarations:
```c
int gcin_core_feedkey_quick(unsigned long keyval, int modifiers);
int gcin_core_feedkey_array(unsigned long keyval, int modifiers);
```

### Step 3 — `ibus-engine/gcin_engine.c` extended

- `GcinEngine.mode` comment extended: `0=Cangjie, 1=Zhuyin, 2=Quick, 3=Array`
- `update_ui()`: changed `mode==0` Cangjie branch to an `else` catch-all (Cangjie, Quick, Array all use the same preedit/candidates functions — they all go through `feedkey_gtab`)
- `process_key_event()`: changed ternary to `switch(mode)` routing:
  ```c
  switch (e->mode) {
      case 0: consumed = gcin_core_feedkey_cangjie(keyval, modifiers); break;
      case 1: consumed = gcin_core_feedkey_zhuyin(keyval, modifiers); break;
      case 2: consumed = gcin_core_feedkey_quick(keyval, modifiers); break;
      case 3: consumed = gcin_core_feedkey_array(keyval, modifiers); break;
  }
  ```
- `gcin_engine_enable()`: added mode detection for Quick and Array:
  ```c
  else if (g_str_has_suffix(name, "quick")) e->mode = 2;
  else if (g_str_has_suffix(name, "array")) e->mode = 3;
  ```
- `main()`: added `ibus_factory_add_engine` for `gcin-quick` and `gcin-array`

### Step 4 — `ibus-engine/component/gcin.xml` updated

Added `<engine>` entries:
- `gcin-quick` — longname "gcin Quick (速成)", symbol 速
- `gcin-array` — longname "gcin Array (行列)", symbol 列

### Step 5 — `Makefile` updated

Added `simplex.gtab` and `ar30.gtab` compilation to the `tables` target:
```makefile
NO_GTK_INIT=1 ./gcin2tab data/simplex.cin && cp data/simplex.gtab $(TABLES)/
NO_GTK_INIT=1 ./gcin2tab data/ar30.cin    && cp data/ar30.gtab    $(TABLES)/
```

### Step 6 — Unit tests added to `gcin-core/test_feedkey.c`

Added 5 new tests:
- `test_quick_single_char` — single-key commit via Quick
- `test_quick_two_char` — two-key sequence via Quick
- `test_quick_escape_clears` — Escape clears preedit
- `test_array_three_key` — three-key Array input sequence
- `test_array_escape_clears` — Escape clears preedit

Quick multi-match tests use `EXPECT_COMMITTED_NONEMPTY` because candidates are sorted by tsin use-count in the compiled binary, not by `.cin` file order.

---

## Key Findings

- **Quick and Array share `feedkey_gtab`** — the only difference from Cangjie is which `.gtab` table is loaded via `init_gtab(inmd_idx)`. Preedit and candidates use the same functions as Cangjie. No new UI integration was needed.
- **Quick candidate order is use-count sorted** — candidates are sorted by tsin frequency data in the compiled binary, not by `.cin` file order. Tests for multi-match cases use `EXPECT_COMMITTED_NONEMPTY` rather than asserting a specific character.
- **Array `%endkey 1234567890`** — digits serve as combined endkey+selkey. Pressing a digit after a full code auto-commits the single match in one step (no space needed). Pressing space first triggers a different code path that also auto-commits single matches.
- **Dayi skipped** — `dayi3.cin` is not present in the gcin source snapshot. Skipped for now.

---

## Test Results

```
20 passed, 0 failed, 0 skipped
```

All 15 pre-existing tests continue to pass; 5 new Quick/Array tests pass.

---

## Files Changed

| File | Change |
|------|--------|
| `gcin-core/gcin_stubs.cpp` | Added `g_quick_inmd`, `g_array_inmd`; `feedkey_gtab_method()` helper; `gcin_core_feedkey_quick()`, `gcin_core_feedkey_array()` |
| `gcin-core/gcin-core.h` | Added declarations for `gcin_core_feedkey_quick()` and `gcin_core_feedkey_array()` |
| `ibus-engine/gcin_engine.c` | Extended `mode` comment; `update_ui()` gtab catch-all; `switch(mode)` routing; Quick/Array mode detection in `enable()`; factory registration for `gcin-quick` and `gcin-array` |
| `ibus-engine/component/gcin.xml` | Added `gcin-quick` and `gcin-array` engine entries |
| `Makefile` | Added `simplex.gtab` and `ar30.gtab` to `tables` target |
| `gcin-core/test_feedkey.c` | Added 5 Quick/Array tests |
