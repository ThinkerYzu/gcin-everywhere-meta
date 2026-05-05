# Session 13: Phase 7 — Alt+Shift / Ctrl Phrase Tables

**Date:** 2026-05-05
**Phase:** Phase 7
**Status:** Complete

---

## Navigation

**Project Docs:** [README](../README.md) | [SPEC](../SPEC.md) | [DESIGN](../DESIGN.md) | [IMPLEMENTATION-GUIDE](../IMPLEMENTATION-GUIDE.md) | [HANDOFF](../HANDOFF.md)

---

## Summary

Implemented Phase 7: Alt+Shift phrase table and Ctrl phrase-ctrl table support. `feed_phrase()` was already compiled from `phrase.cpp`; this session wired it into the public API and the IBus engine. 15/15 unit tests pass.

---

## What Was Done

### Step 1 — `gcin_core_feed_phrase()` added to `gcin-core/gcin-core.h`

New declaration:
```c
int gcin_core_feed_phrase(unsigned long keyval, int modifiers);
```
`modifiers` uses X11 bitmask values (`Mod1Mask|ShiftMask` for Alt+Shift, `ControlMask` for Ctrl).

### Step 2 — Implemented in `gcin-core/gcin_stubs.cpp`

```c
extern gboolean feed_phrase(KeySym ksym, int state);

int gcin_core_feed_phrase(unsigned long keyval, int modifiers) {
    return feed_phrase((KeySym)keyval, modifiers) ? 1 : 0;
}
```

`feed_phrase()` is in `phrase.cpp` (already compiled into `libgcin-core.a`). It internally routes to `phrase.table` when `Mod1Mask|ShiftMask` is set and to `phrase-ctrl.table` when `ControlMask` is set.

### Step 3 — Bug fix: `watch_fopen` stub updated

`feed_phrase()` calls `load_phrase("phrase.table", ...)` with a bare filename. The real `watch_fopen` in `win-sym.cpp` prepends `TableDir/` as fallback. Our stub only did a plain `fopen()`, so it found nothing. Fixed the stub to mirror the real behavior:

```c
FILE *watch_fopen(char *filename, time_t *pfile_modify_time) {
    FILE *fp = fopen(filename, "rb");
    if (!fp && TableDir) {
        char path[512];
        snprintf(path, sizeof(path), "%s/%s", TableDir, filename);
        fp = fopen(path, "rb");
    }
    ...
}
```

This also fixes any future file that loads by bare name via `watch_fopen`.

### Step 4 — Intercepts added to `ibus-engine/gcin_engine.c`

Added X11 modifier defines at the top (IBus headers don't include `<X11/X.h>`):
```c
#define ShiftMask   0x0001
#define ControlMask 0x0004
#define Mod1Mask    0x0008
```

Intercepts inserted after the Shift+Space check, before the feedkey routing:
```c
/* Alt+Shift: phrase.table */
if ((modifiers & (IBUS_MOD1_MASK|IBUS_SHIFT_MASK)) == (IBUS_MOD1_MASK|IBUS_SHIFT_MASK)) {
    gcin_core_set_commit_cb(on_commit, iengine);
    return gcin_core_feed_phrase(keyval, Mod1Mask|ShiftMask) ? TRUE : FALSE;
}

/* Ctrl (without Alt): phrase-ctrl.table — pass through if key not in table */
if ((modifiers & IBUS_CONTROL_MASK) && !(modifiers & IBUS_MOD1_MASK)) {
    gcin_core_set_commit_cb(on_commit, iengine);
    if (gcin_core_feed_phrase(keyval, ControlMask)) return TRUE;
}
```

### Step 5 — `phrase.table` and `phrase-ctrl.table` added to Makefile

```makefile
cp $(GCIN)/data/phrase.table      $(TABLES)/
cp $(GCIN)/data/phrase-ctrl.table $(TABLES)/
```

### Step 6 — Unit tests added to `gcin-core/test_feedkey.c`

Added `ShiftMask`, `ControlMask`, `Mod1Mask` defines and `test_phrase_table()`:

- `alt+shift+i` → `、`  (phrase.table)
- `alt+shift+o` → `。`  (phrase.table)
- `ctrl+,` → `，`  (phrase-ctrl.table)
- `ctrl+'` → `、`  (phrase-ctrl.table)

Gracefully SKIPs if `phrase.table` is absent.

---

## Test Results

```
15 passed, 0 failed, 0 skipped
```

All 11 pre-existing tests continue to pass; 4 new phrase table tests pass.

---

## Files Changed

| File | Change |
|------|--------|
| `gcin-core/gcin-core.h` | Added `gcin_core_feed_phrase()` declaration |
| `gcin-core/gcin_stubs.cpp` | Implemented `gcin_core_feed_phrase()`; fixed `watch_fopen` to prepend `TableDir` |
| `ibus-engine/gcin_engine.c` | Added X11 modifier defines; Alt+Shift and Ctrl intercepts in `process_key_event` |
| `Makefile` | Copy `phrase.table` + `phrase-ctrl.table` in `tables` target |
| `gcin-core/test_feedkey.c` | Added modifier defines; `test_phrase_table()` with 4 tests |

---

## Key Discovery

**`watch_fopen` must prepend `TableDir`** — `phrase.cpp` calls `load_phrase("phrase.table", ...)` with a bare filename. The real `watch_fopen` (in `win-sym.cpp`) uses `get_gcin_user_or_sys_fname()` first, then `TableDir + "/" + filename` as fallback. Our stub only did `fopen(filename)` so it silently missed the file. Fixed to match the real behavior.
