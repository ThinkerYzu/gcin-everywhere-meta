# Session 4: Phase 2 — IBus Engine Skeleton Builds

**Date:** 2026-05-05
**Phase:** Phase 2 — IBus skeleton
**Branch:** master

---

## Goals

- Create `ibus-engine/gcin_engine.c`, `component/gcin.xml`, and `ibus-engine/Makefile`
- Link `libgcin-core.a` into the IBus engine binary
- Reach a buildable `ibus-engine-gcin` executable

## What Was Done

### IBus skeleton files

Created three new files:
- `ibus-engine/gcin_engine.c` — IBus GObject subclass (`GcinEngine`/`GcinEngineClass`), registered via `G_DEFINE_TYPE`. `process_key_event` returns FALSE for now (Phase 3/4 will wire feedkey). `main()` creates the factory, registers gcin-cangjie and gcin-zhuyin, calls `gcin_core_init("/usr/share/gcin")`, then `ibus_main()`.
- `ibus-engine/component/gcin.xml` — IBus component descriptor: two engines (gcin-cangjie symbol 倉, gcin-zhuyin symbol 注), both zh_TW rank 99.
- `ibus-engine/Makefile` — builds against `libgcin-core.a` + `libibus-1.0`; links `-lm` for `pow()` in `tsin-parse.cpp`.

### libibus-1.0-dev not installed — workaround

`libibus-1.0-dev` is not installed and `sudo` is unavailable. Resolved by downloading the `.deb` with `apt-get download` and extracting headers with `dpkg-deb -x` to `/tmp/ibus-dev-extract/`. The linker symlink (`libibus-1.0.so`) in the extracted package points to `.so.5.0.532` (not present), so the installed runtime `.so.5` is passed directly on the linker command line.

### Duplicate stubs from Phase 1

Linking the engine binary (not just building the `.a`) exposed 8 functions stubbed in `gcin_stubs.cpp` that are also defined in compiled gcin files: `hide_row2_if_necessary`, `shift_char_proc`, `disp_gbuf`, `gtab_scan_pre_select`, `start_gtab_pho_query`, `show_tsin_stat`, `pre_punctuation`, `pre_punctuation_hsu`. These duplicate the compiled definitions; removed from stubs.

### Extended libgcin-core.a with 5 more files

Link-time audit revealed ~80 undefined symbols. Most were resolved by adding:
- `locale.cpp` — all utf8 string utilities (`utf8_sz`, `utf8cpy`, `u8cpy`, etc.)
- `gcin-settings.cpp` — all configuration globals (`gtab_*`, `tsin_*`, `pho_*`, `gcin_*`)
- `phrase.cpp` — `feed_phrase`, `watch_fopen`
- `gtab-use-count.cpp` — `inc_gtab_use_count`, `get_gtab_use_count`
- `table-update.cpp` — `update_table_file`

All five have zero GTK/X11 function calls.

### gcin.h GCIN_CORE_BUILD block additions

Three new files required additional stubs in the GCIN_CORE_BUILD block:
- `g_strdup_printf` — inline implementation using `vsnprintf`/`strdup`; used in `gcin-settings.cpp` for UI color strings
- `_(x)` — identity translation macro; used throughout `gcin-settings.cpp`
- `GError`, `gsize`, `g_locale_from_utf8` — used in `locale.cpp`'s `!GCIN_IME` Big5 block
- `XK_F1`–`XK_F12`, `XK_KP_1`–`XK_KP_8`, `XK_KP_Insert`, `XK_KP_Begin` — used in `phrase.cpp` static initializer

### -DUSE_TSIN=1 required

`add_to_tsin_buf` (called from `tsin.cpp`) is inside `#if USE_TSIN`. `USE_TSIN` normally comes from `config.h` (autoconf). Added `-DUSE_TSIN=1` to CFLAGS.

### Remaining stubs added

After adding the 5 new files, ~30 symbols remained (window/display functions from excluded UI files). Added to `gcin_stubs.cpp`: `current_method_type`, `init_in_method`, `win_sym_page_up/down`, `half_char_to_full_char`, `load_pin_juyin`, `inph_typ_pho_pinyin`, `set_win1_cb`, all win0/win1/win-gtab display stubs, `gtab_disp_empty`, `watch_fopen` (with real `fopen`/`fstat`), plus globals `gwin0`, `b_show_win_kbm`, `b_use_full_space`, `win_kbm_inited`.

## Key Findings

- **`G_DEFINE_TYPE` does not generate `GCIN_TYPE_ENGINE`** — must manually `#define GCIN_TYPE_ENGINE (gcin_engine_get_type())` after the macro.
- **Duplicate symbol detection requires linking an executable** — `ar` happily archives duplicate definitions; only the executable linker reports conflicts. Phase 1's "930KB library" silently contained duplicate stubs.
- **gcin-settings.cpp is the global-definition file** — nearly all `gtab_*`, `tsin_*`, `pho_*`, and `gcin_*` configuration variables are defined there, not in their respective feature files.
- **`USE_TSIN` not defined without config.h** — must explicitly pass `-DUSE_TSIN=1`; otherwise `add_to_tsin_buf` is compiled out.
- **`libibus-1.0.so` symlink in extracted .deb points to `.so.5.0.532`** — not present in extracted package; linker must be given the full runtime path `/usr/lib/x86_64-linux-gnu/libibus-1.0.so.5` directly.

## Decisions Made

- **Pass runtime `.so.5` directly to linker** — rather than creating a local symlink, use the absolute path. When `libibus-1.0-dev` is properly installed the standard `pkg-config --libs ibus-1.0` will work; the Makefile supports overriding `IBUS_CFLAGS`/`IBUS_LIBS`.
- **Add 5 files to libgcin-core.a rather than stubs for every symbol** — `locale.cpp`, `gcin-settings.cpp` etc. have no GTK/X11 calls; compiling them gives real behavior (settings loading, utf8 ops) vs. no-op stubs.
- **`watch_fopen` stub does real `fopen`** — the function is needed at runtime to load data tables; stubbing it as a no-op would silently fail later. Implemented with `fopen` + `fstat` for modification-time tracking.

## Status at End of Session

- `ibus-engine-gcin` (520KB ELF) builds and links cleanly
- `libgcin-core.a` now includes 26 source files
- All key entry points present; `process_key_event` passes all keys through
- Engine not yet registered with ibus-daemon (data tables not compiled; binary not installed)
- No runtime testing done yet

## Next Steps

1. **Compile data tables** — run `cintotab data/cj.cin data/cj.gtab` and `phoconv data/pho.tab2.src data/pho.tab` from a gcin build dir, install to `/usr/share/gcin/`
2. **Install and register** — `sudo cp component/gcin.xml /usr/share/ibus/component/`; run `./ibus-engine-gcin &`; verify `ibus list-engine | grep gcin`
3. **Phase 3: Cangjie** — wire `gcin_core_feedkey_cangjie()` → `feedkey_gtab()` in `process_key_event`; expose preedit via `get_DispInArea_str()`; expose candidates via `disp_gtab_sel()` stub

---

**Files Changed:**
- `gcin/gcin.h` — GCIN_CORE_BUILD: add g_strdup_printf, _(), GError/gsize, g_locale_from_utf8, XK_F1-F12, XK_KP_1-8/Insert/Begin
- `gcin-core/Makefile` — add locale.cpp, phrase.cpp, gtab-use-count.cpp, gcin-settings.cpp, table-update.cpp; add -DUSE_TSIN=1
- `gcin-core/gcin_stubs.cpp` — remove 8+2 duplicate stubs; add gwin0/b_show_win_kbm/b_use_full_space/win_kbm_inited globals; add ~35 new stubs; add <sys/stat.h>; add win1.h include
- `ibus-engine/gcin_engine.c` — NEW: IBus GObject skeleton
- `ibus-engine/component/gcin.xml` — NEW: IBus component registration
- `ibus-engine/Makefile` — NEW: build rule linking libgcin-core.a
- `ibus-engine/.gitignore` — NEW: ignore ibus-engine-gcin binary
