# Session 6: GCIN_TABLE_DIR Support + System-Wide IBus Registration

**Date:** 2026-05-05
**Phase:** Phase 2 → Phase 3 boundary
**Branch:** master

---

## Goals

- Allow the IBus engine to load tables from a user-specified directory (no root needed for testing)
- Silence spurious `mv: cannot stat ~/.gcin/pho.tab2` error on first run
- Verify system-wide IBus registration

## What Was Done

### GCIN_TABLE_DIR support in the IBus engine

`ibus-engine/gcin_engine.c` hardcoded `/usr/share/gcin` when calling `gcin_core_init()`.
Changed it to read `GCIN_TABLE_DIR` from the environment first:

```c
const char *table_dir = getenv("GCIN_TABLE_DIR");
gcin_core_init(table_dir ? table_dir : "/usr/share/gcin");
```

The gcin core already supports this env var via `init_TableDir()` in `gcin-conf.cpp`; the engine just wasn't passing it through.

### test-registration.sh: auto-detect /tmp/gcin-tables

Updated the script to resolve the table directory without requiring the user to set any env var:
1. If `GCIN_TABLE_DIR` is set, use it.
2. Else if `/tmp/gcin-tables/cj.gtab` exists, use `/tmp/gcin-tables` (locally built tables).
3. Else fall back to `/usr/share/gcin`.

Also changed the auto-build step to always run `make` (not only when the binary is missing), so a stale binary linked against an old `libgcin-core.a` is automatically rebuilt.

### Silenced mv error on first run

`gcin/table-update.cpp` runs `mv -f ~/.gcin/pho.tab2 ~/.gcin/pho.tab2.old` as a backup before copying a newer system table. On first run the user copy doesn't exist and `mv` prints an error to stderr. In gcin-everywhere we load tables from a specified directory and don't need user-local table copies.

Fix: removed `table-update.cpp` from `gcin-core/Makefile` and added a no-op stub in `gcin_stubs.cpp`:

```c
void update_table_file(char *name, int version) { (void)name; (void)version; }
```

### System-wide IBus registration verified

User installed tables and component XML system-wide. Confirmed:

```
$ ibus list-engine | grep gcin
  gcin-cangjie - gcin Cangjie (倉頡)
  gcin-zhuyin - gcin Zhuyin (注音)
```

## Key Findings

- `init_TableDir()` is called after `gcin_core_init()` sets `TableDir`, so the env var takes precedence over the parameter — this is the intended priority order.
- `table-update.cpp`'s `mv` error is benign (return value of `system()` is unchecked) but noisy; a stub is cleaner than patching the upstream submodule.

## Decisions Made

- **No-op stub over submodule patch** — `update_table_file` stubbed in our code rather than modifying `gcin/table-update.cpp`, keeping the submodule clean.
- **Always run make in test script** — cheaper than a stale-binary bug; `make` is a no-op when nothing changed.

## Status at End of Session

- Engine loads tables from `GCIN_TABLE_DIR` or auto-detects `/tmp/gcin-tables`
- No spurious `mv` error on first run
- `ibus list-engine` shows gcin-cangjie + gcin-zhuyin system-wide
- All 6 unit tests still pass

## Next Steps

- Phase 3 — Cangjie key routing: wire `process_key_event` → `feedkey_gtab()`, expose preedit and candidates, test `di` → commits 大人

---

**Files Changed:**
- `ibus-engine/gcin_engine.c` — read `GCIN_TABLE_DIR` env var; pass to `gcin_core_init()`
- `ibus-engine/test-registration.sh` — auto-detect `/tmp/gcin-tables`; always run `make`
- `gcin-core/Makefile` — removed `table-update.cpp` from source list
- `gcin-core/gcin_stubs.cpp` — added no-op `update_table_file()` stub
