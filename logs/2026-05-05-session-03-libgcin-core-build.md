# Session 3: Phase 1 Complete — libgcin-core.a Builds

**Date:** 2026-05-05
**Phase:** Phase 1 — libgcin-core.a
**Result:** libgcin-core.a (930KB) builds with zero errors; all gcin_core_* API symbols present

---

## What Was Done

Implemented Phase 1 in full: modified 4 gcin source files and created the `gcin-core/` directory.

### gcin source file modifications

**`gcin/gcin.h`** — Added GCIN_CORE_BUILD block before existing includes. Block provides:
- Standard headers: `<stdarg.h>`, `<stdio.h>`, `<stdlib.h>`, `<ctype.h>`, `<string.h>`, `<sys/types.h>`, `<unistd.h>`, `<time.h>`
- 5 core types: `gboolean`, `gint64`, `KeySym`, `GtkWidget` (=void), `unich_t`
- Macros: `TRUE`/`FALSE`, `_L`, `UNIX=1`, `GTK_CHECK_VERSION(a,b,c)=0`, `GTK_WIDGET_VISIBLE(w)=(0)`
- GLib memory aliases: `g_malloc`, `g_free`, `g_strdup`, `g_new`, `g_new0`, `g_realloc`
- `g_markup_escape_text` stub (used in gtab.cpp:htmlspecialchars)
- XK_* key symbols and modifier masks (full set used by feedkey_gtab/pho)
- `unix_exec` declaration (os-dep.h excluded, but function compiled from unix-exec.cpp)

Declaration guards added:
- `extern Display *dpy`, `GdkWindow *gdkwin0`, `Window xwin0/root` → `#ifndef GCIN_CORE_BUILD`
- `loadIC()`, `FindIC()` → guarded (XIM-only)
- `inmd_switch_popup_handler` → guarded (uses GdkEvent)
- `Atom get_gcin_atom(Display *dpy)` → guarded
- `send_gcin_message(Display *dpy, char *s)` → guarded
- `gwin0` kept unguarded — referenced directly in tsin.cpp:tsin_reset()

**`gcin/IC.h`**:
- `PreeditAttributes`/`StatusAttributes`: changed `#if UNIX` to `#if UNIX && !defined(GCIN_CORE_BUILD)` (they need XRectangle/Colormap/Pixmap/Cursor not defined in GCIN_CORE_BUILD)
- `Window client_win` and `INT32 input_style` in ClientState: guarded with `#ifndef GCIN_CORE_BUILD`
- `XPoint spot_location` in ClientState: guarded with `#ifndef GCIN_CORE_BUILD`
- Entire IC struct, DUAL_XIM_ENTRY, and `Window get_ic_win()`: guarded (never used in core)

**`gcin/util.cpp`**:
- GTK dialog block in `p_err()`: wrapped with `#ifndef GCIN_CORE_BUILD` / `#else fprintf` 
- `box_warn()`: changed condition to `#if !GCIN_IME && !CLIENT_LIB && !GCIN_CORE_BUILD` to exclude the whole GTK-only function

**`gcin/gcin-conf.cpp`**:
- `#include "os-dep.h"`: wrapped with `#ifndef GCIN_CORE_BUILD`
- `#include <X11/Xatom.h>`: guarded out; `<dirent.h>` kept for UNIX GCIN_CORE_BUILD
- `get_gcin_atom()` function body: wrapped with `#ifndef GCIN_CORE_BUILD`

### New gcin-core/ directory

**`gcin-core/gcin-core.h`**: Public C API:
- `gcin_core_set_commit_cb(GcinCommitCb, void*)` — register output callback
- `gcin_core_init(const char *table_dir)` — initialize, loads tables
- `gcin_core_feedkey_cangjie(keyval, modifiers)` — routes to `feedkey_gtab()`
- `gcin_core_feedkey_cangjie_release(keyval, modifiers)` — routes to `feedkey_gtab_release()`
- `gcin_core_feedkey_zhuyin(keyval, modifiers)` — routes to `feedkey_pho()`
- `gcin_core_reset()` — placeholder for focus-loss reset

**`gcin-core/gcin_stubs.cpp`**: Provides:
- Extern globals from excluded files: `test_mode`, `win_xl/yl`, `win_x/y`, `dpy_xl/yl`, `gcin_font_size`, `gwin_gtab`, `gwin_pho`, `gwin1`, `win_gtab_max_key_press`, `last_cursor_off`, `pin_juyin`, `text_pho_N`, `current_in_win_x/y`
- Static `ClientState _cs = {0}` with `current_CS = &_cs`
- `send_text()`, `send_utf8_ch()`, `send_ascii()` → fire `GcinCommitCb`
- `case_inverse()` — reimplemented (flip alpha KeySym case by ±0x20)
- `current_time()` — reimplemented using `clock_gettime(CLOCK_MONOTONIC)` in microseconds
- All UI function stubs (void and boolean)

**`gcin-core/Makefile`**: Compiles 22 gcin source files + stubs as C:
- Flags: `-x c -std=gnu99 -Wno-implicit-function-declaration`  
- Defines: `-DGCIN_CORE_BUILD -DHAVE_CONFIG_H -DGCIN_TABLE_DIR -DGCIN_BIN_DIR`
- Key addition vs. IMPLEMENTATION-GUIDE: added `pho-sym.cpp` (defines `pho_chars[]` used by tsin.cpp), `unix-exec.cpp` (defines `unix_exec` declared in GCIN_CORE_BUILD block but excluded from os-dep.h)
- Removed `gcin-common.cpp` from compiled list (GTK/X11 calls; stubs replace what's needed)

---

## Discoveries / Corrections to Implementation Guide

The IMPLEMENTATION-GUIDE Phase 1a code block still has the "include all types" approach from before Session 2. The actual implementation follows the Session 2 Key Findings (5 types + targeted IC.h guards). These are the same result, but the guide is inconsistent — HANDOFF takes precedence.

Additional files needed beyond what the guide listed:
- **`pho-sym.cpp`**: must be compiled (defines `pho_chars[]`, which tsin.cpp uses via `extern char *pho_chars[]`)
- **`unix-exec.cpp`**: must be compiled (defines `unix_exec`, used in gtab-tsin-fname.cpp for merging user tables)

Additional modifications beyond what the guide planned:
- `gcin.h` GCIN_CORE_BUILD block needs: `<unistd.h>`, `<time.h>`, `GTK_CHECK_VERSION(a,b,c)=0`, `g_markup_escape_text` stub, `unix_exec` declaration
- `util.cpp`: also need to guard `box_warn()` (uses GTK_DIALOG_MODAL etc.), not just `p_err()`
- Compile as C (`-x c`), not C++: gcin source uses `goto` that crosses variable initializations (valid C, error in C++)

Stub list correction confirmed: 13 functions from the IMPLEMENTATION-GUIDE stub list are already defined in compiled files — NOT stubbed. Full list in IMPLEMENTATION-GUIDE "Do NOT stub" section.

---

## Compile Stats

- 22 gcin source files + 1 stubs file = 23 compilation units
- libgcin-core.a: 930KB
- Key symbols verified: `feedkey_gtab`, `feedkey_gtab_release`, `feedkey_pho`, `gcin_core_init`, `gcin_core_set_commit_cb`, `gcin_core_feedkey_cangjie`, `gcin_core_feedkey_zhuyin`, `send_text`

---

## Git

Commits in `sources/gcin-everywhere/`:
- `d2ad4de`: Phase 1: build libgcin-core.a — gcin core compiles without X11/GTK
- `6140eea`: Add .gitignore for gcin-core build artifacts

---

**Next:** Phase 2 — IBus engine skeleton (`ibus-engine/gcin_engine.c`, `component/gcin.xml`, `ibus-engine/Makefile`). Verify `ibus list-engine | grep gcin` shows both engines.
