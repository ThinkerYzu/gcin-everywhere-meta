# Session 2: Implementation Guide Deep Audit

**Date:** 2026-05-05
**Phase:** Planning — refining Phase 1 implementation plan
**Branch:** master

---

## Goals

- Verify and tighten the Phase 1 implementation plan through source-level audit
- Determine the minimal set of gcin changes needed to build `libgcin-core.a`
- Resolve any contradictions or hidden issues in the plan before writing code

---

## What Was Done

### Per-file audit of all MODIFY-classified gcin files

Audited each file previously marked MODIFY (`gtab.cpp`, `gtab-init.cpp`, `gtab-list.cpp`,
`gtab-buf.cpp`, `pho.cpp`, `tsin.cpp`, `util.cpp`, `gcin-common.cpp`) for actual GTK/X11
function calls vs. mere type usage.

**Finding:** Only two files call actual GTK/X11 functions:
- `gcin-common.cpp` — `XBell`, `gdk_beep`, `gtk_label_set_text`, Pango calls → **EXCLUDE** entirely
- `util.cpp` — `gtk_message_dialog_new/run/destroy` in `p_err()` → one `#ifndef` guard

All other MODIFY files only have `extern GtkWidget *varname` declarations — no function
calls. Reclassified as **INCLUDE as-is**. The compat/ fake-header directory was
eliminated in favour of a `GCIN_CORE_BUILD` guard block in `gcin.h`.

### Discovery: gcin already shows the pattern

`os-dep.h`'s WIN32 path already defines `Display` as `void`, `KeySym` as `unsigned int`,
`Window` as `unsigned int` with no system headers. We add an identical `GCIN_CORE_BUILD`
path to `gcin.h`. This eliminates the entire compat/ directory.

### New finding: gcin-conf.cpp has an actual X11 call

`gcin-conf.cpp` (previously marked INCLUDE) contains `get_gcin_atom(Display *dpy)` which
calls `XInternAtom`. Guards needed. Raises modified-file count from 2 to 4.

### Minimising the GCIN_CORE_BUILD type list

Audited usage counts for every type across all compiled files and headers. Used
`GCIN_CORE_BUILD` declaration guards to eliminate types that were only needed for
declarations we don't use in core builds:

- Guarded `extern Display *dpy`, `extern GdkWindow *gdkwin0`, unused function decls
  in `gcin.h` → dropped `Display`, `GdkWindow`, `gint`
- Guarded `PreeditAttributes`/`StatusAttributes` in `IC.h` → dropped `CARD32`,
  `XRectangle`, `Pixmap`, `Cursor`, `Colormap`
- Guarded `Window client_win` in `IC.h`'s `ClientState` struct (never accessed in
  compiled code) → dropped `Window`
- Dropped 7 zero-use types: `gulong`, `guint64`, `guint`, `guchar`, `gpointer`,
  `gchar`, `KeyCode`

**Final GCIN_CORE_BUILD type list: 5 types** — `gboolean`, `gint64`, `KeySym`,
`GtkWidget`, `unich_t`.

### GtkWidget elimination analysis

Investigated eliminating `GtkWidget` by guarding local `extern GtkWidget *gwin_*`
in `gtab.cpp`, `gtab-buf.cpp`, `pho.cpp`, `tsin.cpp` + handling `WSP_S` struct in
`win-save-phrase.h`. Cost: 4 more modified gcin files (4 → 8 total).
`GTK_WIDGET_VISIBLE(w)` must be defined regardless (called in `feedkey_gtab:985`
and `feedkey_pho:844`).
**Decision: keep `typedef void GtkWidget`.** It has no headers, no link-time
footprint, no runtime cost. Not worth the extra invasiveness.

### Duplicate symbol bug found and fixed

Compiling `gtab.cpp`, `pho.cpp`, `tsin.cpp` brings in function DEFINITIONS beyond
the entry points, conflicting with our planned stubs:

- `gtab.cpp` defines: `ClrIn`, `ClrSelArea`, `clear_after_put`, `disp_selection0`,
  `close_gtab_pho_win`, `is_gtab_query_mode`, `use_tsin_sel_win`,
  `same_query_show_pho_win`, `set_gtab_target_displayed`
- `pho.cpp` defines: `clr_in_area_pho`, `ClrPhoSelArea`, `clrin_pho`
- `tsin.cpp` defines: `drawcursor`

These 13 functions were removed from the `gcin_stubs.cpp` stub list. Their bodies
call other stubs (e.g. `show_win_gtab`) which become no-ops — correct behaviour.

---

## Key Findings

- **Only 2 gcin files call actual GTK/X11 functions** in our compiled set —
  `gcin-common.cpp` (excluded) and `util.cpp` (one guard). `gcin-conf.cpp` adds a
  third (also one guard).
- **gcin's WIN32 path** in `os-dep.h` already solves the problem we were trying to
  solve with compat/ headers — same pattern applied to `GCIN_CORE_BUILD`.
- **`GTK_WIDGET_VISIBLE`** is called inside `feedkey_gtab` and `feedkey_pho` code
  paths — a hidden dependency that would have surfaced as a compile error.
- **13 stubs** would have caused duplicate symbol linker errors — functions that are
  defined in compiled files, not just declared there.
- **`Window`** type (from `ClientState.client_win`) is never accessed in compiled
  code — guarding the field in `IC.h` eliminates the last X11 integer type.

---

## Decisions Made

- **No compat/ directory** — modify `gcin/gcin.h` with `GCIN_CORE_BUILD` block instead.
  Cleaner: single source of truth, no fake headers shadowing system paths.
- **Exclude `gcin-common.cpp`** — actual GTK calls; re-implement `case_inverse` and
  `current_time` in `gcin_stubs.cpp` (trivial).
- **Keep `typedef void GtkWidget`** — eliminating it costs 4 more file modifications
  (4 → 8) for zero practical benefit. The type has no footprint.
- **4 gcin files to modify total:** `gcin.h`, `IC.h`, `util.cpp`, `gcin-conf.cpp`.

---

## Status at End of Session

- Implementation guide fully revised and audited — ready to write code
- All GCIN_CORE_BUILD decisions locked down
- Stub list corrected (13 duplicate symbols removed)
- No code written yet

---

## Next Steps

1. Modify `gcin/gcin.h` — add GCIN_CORE_BUILD block and declaration guards
2. Modify `gcin/IC.h` — guard PreeditAttributes/StatusAttributes + `Window client_win`
3. Modify `gcin/util.cpp` — guard GTK dialog in `p_err()`
4. Modify `gcin/gcin-conf.cpp` — guard `get_gcin_atom()` body
5. Create `gcin-core/` with `gcin_stubs.cpp`, `gcin-core.h`, `Makefile`
6. Build `libgcin-core.a` — iterate until zero errors

---

**Files Changed:**
- `IMPLEMENTATION-GUIDE.md` — major revision: compat/ eliminated, type list reduced
  to 5, declaration guards documented, stub list corrected, GtkWidget decision recorded
- `DESIGN.md` — architecture diagram and component table updated; Decisions 1 & 2
  rewritten; modified-file count updated to 4
- `README.md` — Core Concepts corrected (no gcin_adapter.cpp reference)
- `HANDOFF.md` — Next Actions updated; session log added
- `INIT-GUIDE.md` — deleted (Phase 2 initialization complete)
