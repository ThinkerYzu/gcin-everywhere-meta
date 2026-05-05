# Session 5: Data Tables Compiled; All Unit Tests Pass

**Date:** 2026-05-05
**Phase:** Phase 2 / test infrastructure
**Branch:** master

---

## Goals

- Compile gcin data tables without GTK2
- Get `make test` passing with real data
- Fix all `gcin_core_init()` initialization issues found during testing

## What Was Done

### Table compiler tools (gcin2tab, phoa2d, tsa2d32, kbmcv)

gcin's build system requires GTK2 (`./configure && make`) which isn't installed. Built the four table compiler tools directly with `GCIN_CORE_BUILD + -lgcin-core.a`:

```bash
cc -x c -std=gnu99 -DGCIN_CORE_BUILD ... gcin2tab.cpp gtk_stub.c -o gcin2tab -lgcin-core -lm
cc ... phoa2d.cpp  gtk_stub.c -o phoa2d  -lgcin-core -lm
cc ... tsa2d32.cpp gtk_stub.c -o tsa2d32 -lgcin-core -lm
cc ... kbmcv.cpp   gtk_stub.c -o kbmcv   -lgcin-core -lm
```

`gtk_stub.c` provides: `gtk_init()` no-op, `Display` typedef, `send_gcin_message()` no-op, `pinyin2phokey()` stub returning 0.

Two extra additions to `gcin.h` GCIN_CORE_BUILD block required:
- `typedef void Display` — needed by phoa2d/tsa2d32 forward declarations
- `#define GDK_DISPLAY() ((Display*)0)` — phoa2d calls `send_gcin_message(GDK_DISPLAY(), "reload")`

Tables compiled to `/tmp/gcin-tables/`:
- `cj.gtab` (189KB) — Cangjie 5 lookup table
- `pho.tab2` (123KB) — Zhuyin phonetic table (Standard/Daqian layout)
- `tsin32` + `tsin32.idx` (774KB + 169KB) — word frequency database
- `zo.kbm` (769B) — Zhuyin Standard keyboard map
- `gtab.list` — copied from gcin/data/ (needed by `load_gtab_list()`)

Tool names differ from IMPLEMENTATION-GUIDE: `gcin2tab` (not `cintotab`), `phoa2d` (not `phoconv`), outputs go to input file's directory.

### gcin_core_init() initialization cascade (6 bugs fixed)

Running the tests with tables exposed 6 init problems one by one:

| Bug | Symptom | Fix |
|-----|---------|-----|
| `pho_kbm_name` NULL | segfault in `strstr(pho_kbm_name, "pinyin")` | Call `load_setttings()` before `load_tab_pho_file()` |
| `cur_inmd` NULL | segfault in `feedkey_gtab` | Call `load_gtab_list()` + `init_gtab(cj_index)` in init |
| Keys passing through as ASCII | `feedkey_gtab` hits ASCII passthrough for all printable keys | Set `current_CS->tsin_pho_mode = 1` |
| Characters go to phrase buffer | `putstr_inp` routes to `insert_gbuf_cursor1_cond` instead of `send_utf8_ch` | Set `gtab_auto_select_by_phrase = GTAB_OPTION_NO (2)` |
| `gcin_core_reset()` no-op | State leaked between tests; tests passed for wrong reasons | Implement: calls `ClrIn()` + `clrin_pho()` |
| Wrong test sequences | Cangjie nofull requires space+'1', not just space | Update tests: k+space+'1' not k+space |

### Cangjie input UX discovery

`cj.gtab` uses `space_style = GTAB_space_auto_first_nofull (4)`:
- Space alone does NOT auto-select the first candidate
- Space sets `ggg.spc_pressed = 1` and shows candidates
- '1'-'9' then selects the candidate

Correct sequence: `radicals... + space + '1'`

Example verified against actual table:
- `k + space + '1'` → 大
- `a + b + space + '1'` → 明 (日+月 radicals)

### Final test results

```
gcin-core feedkey tests
Table dir: /tmp/gcin-tables

Cangjie:
  PASS  cangjie: k+space+1 commits 大
  PASS  cangjie: ab+space+1 commits 明
  PASS  cangjie: escape after partial input does not commit
  PASS  cangjie: backspace then select still outputs

Zhuyin:
  PASS  zhuyin: ju4 + 1 commits a character
  PASS  zhuyin: escape after partial input does not commit

6 passed, 0 failed, 0 skipped
```

## Key Findings

- **Table tool names differ from IMPLEMENTATION-GUIDE** — `gcin2tab` (not `cintotab`), `phoa2d` (not `phoconv`); outputs go beside input file not to cwd
- **`pho.tab2` required (not `pho.tab`)** — gcin uses `pho.tab2` as the phonetic table filename; `pho.tab` is a different file
- **`gtab.list` must be in table dir** — `load_gtab_list()` needs it to populate `inmd[]`; without it, no input methods are loaded
- **Cangjie `space_style = GTAB_space_auto_first_nofull`** — the standard UX is space-to-page, number-to-select (not space-to-commit)
- **Phrase buffering must be disabled for direct commit** — `gtab_auto_select_by_phrase = GTAB_OPTION_NO` makes characters commit immediately via `send_utf8_ch` instead of buffering
- **`tsin_pho_mode = 1` required** — without this flag, `feedkey_gtab` drops into the ASCII passthrough branch for all printable keys (0x20-0x7e)

## Status at End of Session

- All 6 unit tests pass with `/tmp/gcin-tables/`
- Tables not yet installed system-wide (need sudo for `/usr/share/gcin/`)
- IBus registration not yet verified with live engine (needs system tables)
- `gcin_core_init()` now fully functional; commit callbacks fire correctly

## Next Steps

1. Install tables system-wide: `sudo cp /tmp/gcin-tables/* /usr/share/gcin/`
2. Install component XML: `sudo cp component/gcin.xml /usr/share/ibus/component/`
3. Run `./test-registration.sh` — should get 7/7 pass with tables installed
4. Phase 3: wire `gcin_core_feedkey_cangjie()` into IBus `process_key_event`

---

**Files Changed:**
- `gcin/gcin.h` — add `typedef void Display` and `#define GDK_DISPLAY()` to GCIN_CORE_BUILD
- `gcin-core/gcin_stubs.cpp` — fix `gcin_core_init()` (load_setttings, load_gtab_list, init_gtab, tsin_pho_mode, phrase buffer disable); fix `gcin_core_reset()` (ClrIn + clrin_pho); add gtab.h include; add load_setttings/load_gtab_list/init_gtab externs
- `gcin-core/test_feedkey.c` — fix Cangjie test sequences (space+'1' not space alone); use verified codes k→大, ab→明; fix reset between tests
