# Design: gcin-everywhere

**Project:** gcin-everywhere
**Created:** 2026-05-04
**Last Updated:** 2026-06-22 (added decision 9: GNOME panel indicator extension)

---

## Navigation

**Project Docs:** [README](README.md) | [SPEC](SPEC.md) | [DESIGN](DESIGN.md) *(you are here)* | [IMPLEMENTATION-GUIDE](IMPLEMENTATION-GUIDE.md) | [HANDOFF](HANDOFF.md)

**This Document:**
- [Design Philosophy](#design-philosophy)
- [Architecture Overview](#architecture-overview)
- [Key Design Decisions](#key-design-decisions)
- [Data Model](#data-model)
- [IBus Engine Interface](#ibus-engine-interface)

---

## Design Philosophy

1. **Minimize gcin changes.** The gcin core is mature and correct. Only two source files are modified: `gcin.h` (add `GCIN_CORE_BUILD` type block) and `util.cpp` (guard one GTK dialog call).
2. **Clean platform boundary.** Platform dependencies are isolated in `gcin_stubs.cpp`. The gcin core files compile as-is against the type definitions in `gcin.h`.
3. **Static library for portability.** Core engine and tables are packaged as `libgcin-core.a` — platform integrations (IBus, future Windows TSF, macOS IMKit) link against it.
4. **IBus built-in UI.** Candidate display is delegated entirely to IBus — no custom windowing code needed.
5. **Small scope.** Phase 1 ships one working thing: Cangjie and Zhuyin on GNOME/Wayland. No feature creep.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│              GNOME / Wayland Applications            │
│           (GTK4, Qt6, any IBus-aware app)            │
└──────────────────────┬──────────────────────────────┘
                       │ Wayland text-input protocol
┌──────────────────────▼──────────────────────────────┐
│                  ibus-daemon                         │
│         (GNOME's input method coordinator)           │
└──────────────────────┬──────────────────────────────┘
                       │ D-Bus (IBus engine protocol)
┌──────────────────────▼──────────────────────────────┐
│   ibus-engine-gcin  (ibus-engine/)                   │
│   gcin_engine.c — IBus GObject                       │
│   - process_key_event()                              │
│   - enable() / disable() / reset()                   │
└──────────────────────┬──────────────────────────────┘
                       │ links against
┌──────────────────────▼──────────────────────────────┐
│   libgcin-core.a  (gcin-core/)                       │
│                                                      │
│   gcin_stubs.cpp — public API + stubs                │
│   - gcin_core_init() / feedkey_cangjie/zhuyin()      │
│   - send_text() → GcinCommitCb callback              │
│   - extern globals (dpy=NULL, gwin0=NULL, ...)       │
│   - UI function stubs (show_win_gtab etc.)           │
│                       │                              │
│   gcin/ source (compiled in, modified minimally)     │
│   ┌─────────────────┐  ┌──────────────────────────┐ │
│   │ gtab.cpp + buf  │  │ pho.cpp + pho-util etc.  │ │
│   │ feedkey_gtab()  │  │ feedkey_pho()            │ │
│   └────────┬────────┘  └──────────┬───────────────┘ │
│            └──────────┬───────────┘                  │
│   ┌──────────────────▼──────────────────────────┐   │
│   │  gcin Data Tables (loaded at runtime)        │   │
│   │  cj.gtab  pho.tab  tsin                      │   │
│   └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### Component Roles

| Component | Source | Role |
|-----------|--------|------|
| `ibus-engine-gcin` binary | New (`ibus-engine/`) | Process launched by ibus-daemon |
| `gcin_engine.c` | New | IBus GObject: handles IBus protocol, calls gcin-core API |
| `libgcin-core.a` | New (`gcin-core/`) | Platform-independent static library |
| `gcin_stubs.cpp` | New | Public API, extern globals, UI stubs, send_text callback |
| `gcin/gcin.h` | Modified (4 files total) | GCIN_CORE_BUILD type block (6 types only) + guards on unused declarations |
| `gcin/IC.h` | Modified | Guard `PreeditAttributes`/`StatusAttributes` (XIM-only, unused by core) |
| `gcin/util.cpp` | Modified | Guard GTK dialog calls in `p_err()` |
| `gcin/gcin-conf.cpp` | Modified | Guard `get_gcin_atom()` which calls `XInternAtom` |
| `gtab.cpp` + `gtab-buf.cpp` + related | gcin (as-is) | Cangjie: `feedkey_gtab()`, key buffer, table lookup |
| `pho.cpp` + related | gcin (as-is) | Zhuyin: `feedkey_pho()`, phonetic lookup |
| `data/cj.gtab` | gcin (built) | Compiled Cangjie character table |
| `data/pho.tab` | gcin (built) | Compiled Zhuyin phonetic table |
| `data/tsin` | gcin (built) | Word frequency database |
| `gcin.xml` | New | IBus component registration file |

---

## Key Design Decisions

### 1. Build a platform-independent static library (libgcin-core.a)

**Decision:** Compile selected gcin source files into `libgcin-core.a`. Platform integrations (IBus, future Windows TSF, macOS IMKit) link against it. The library has zero GTK/X11 runtime dependency.

**Rationale:** A static library creates a clean boundary between the platform-independent input logic and each platform's integration layer. It also enables future ports without touching the gcin core again.

**Files compiled in:** `gtab.cpp`, `gtab-buf.cpp`, `pho.cpp`, and ~15 other gcin files. Excluded: `gcin.cpp` (main), all UI/window files, XIM server, `gcin-common.cpp` (GTK calls; its two useful functions re-implemented in `gcin_stubs.cpp`).

### 2. Eliminate GTK/X11 type dependencies via GCIN_CORE_BUILD in gcin.h

**Decision:** Add a `#ifdef GCIN_CORE_BUILD` block to `gcin/gcin.h` that defines all needed types (`gboolean`, `GtkWidget`, `Display`, `KeySym`, etc.) as plain C types inline — no system headers. Guard the GTK dialog calls in `gcin/util.cpp` with `#ifndef GCIN_CORE_BUILD`.

**Rationale:** Source audit confirmed that only `gcin-common.cpp` and `util.cpp` make actual GTK/X11 function calls. All other files use these types only as pointer declarations or function parameter types — trivially satisfied by simple typedefs. gcin's own WIN32 path in `os-dep.h` already does exactly this. No fake/shadow headers needed.

**Result:** Four gcin source files modified total. `libgcin-core.a` requires only a C++ compiler and the standard library.

### 3. One binary, two engines registered via IBus component XML

**Decision:** A single `ibus-engine-gcin` binary hosts both Cangjie and Zhuyin engines. The IBus component XML declares both as separate engine entries. The binary starts the correct engine based on the engine name passed by ibus-daemon.

**Rationale:** Simpler deployment and shared initialization cost for gcin data tables. IBus supports multiple engines per component.

### 4. Data tables compiled by gcin's existing build, loaded at runtime

**Decision:** The `.cin` and `.tab2.src` source files are compiled to binary format by gcin's existing tools (`cintotab`, `phoconv`) as part of the build. The IBus engine loads them at runtime from a fixed install path (e.g., `/usr/share/gcin/`).

**Rationale:** The table compiler is already correct and battle-tested. Reusing it avoids re-implementing the binary format. Runtime loading matches how gcin already works.

### 5. IBus built-in candidate window

**Decision:** Use `ibus_engine_update_lookup_table()` with IBus's built-in candidate window. No custom candidate UI.

**Rationale:** Simpler, integrates naturally with GNOME's IBus UI. Can revisit with a custom window in a later phase if the look and feel matters.

### 6. Full-width character mode: un-stub full_char_proc, match gcin exactly

**Decision:** Implement `half_char_to_full_char()` and `full_char_proc()` in `gcin_stubs.cpp` (removing the FALSE stubs), and handle Shift+Space in `gcin_engine.c` to toggle `current_CS->b_half_full_char`. This matches gcin's own mechanism exactly.

**How gcin does it:**

gcin uses a full-width character mode toggled by Shift+Space. When active (`b_half_full_char == 1`), `feedkey_gtab()` routes every key through `full_char_proc()` before any table lookup. `full_char_proc()` calls `half_char_to_full_char()` which indexes into `fullchar[]` — a complete ASCII→full-width mapping table already compiled in `fullchar.cpp`.

The `fullchar[]` table covers ALL printable ASCII (space through `~`):
- Letters → ａ-ｚ, Ａ-Ｚ
- Digits → ０-９
- Punctuation → ，。！？：；「」…etc.

`feedkey_gtab()` already calls `full_char_proc()` at every key-handling branch when `b_half_full_char == 1` — the wiring is already in gcin. We only need to un-stub the two functions and wire the toggle.

**Why our original stub broke it:** `full_char_proc()` was stubbed to return `FALSE` because it's in excluded `eve.cpp`. `half_char_to_full_char()` was stubbed to return `NULL` (also in excluded `gcin.cpp`). Both have zero GTK/X11 dependencies — they only use `fullchar[]` and `send_text()`.

**Implementation:**

```c
/* in gcin_stubs.cpp — replace the NULL stub */
char *half_char_to_full_char(KeySym xkey) {
    extern unich_t *fullchar[];
    if (xkey < ' ' || xkey > 127) return NULL;
    return fullchar[xkey - ' '];
}

/* in gcin_stubs.cpp — replace the FALSE stub */
gboolean full_char_proc(KeySym keysym) {
    char *s = half_char_to_full_char(keysym);
    if (!s) return 0;
    char tt[CH_SZ + 1];
    utf8cpy(tt, s);
    /* For our use: not TSIN mode, phrase buffer off → send_text() */
    send_text(tt);
    return 1;
}
```

**Toggle in gcin_engine.c:** Shift+Space (`keyval == XK_space && modifiers & ShiftMask`) flips `current_CS->b_half_full_char` and resets gcin state.

**Scope:** This applies to both Cangjie and Zhuyin (both call `full_char_proc()` when `b_half_full_char` is set in their respective feedkey functions). It is the correct, complete solution — not a partial punctuation-only workaround.

### 7. Alt+Shift phrase table: intercept in engine, delegate to feed_phrase()

**Decision:** Intercept `Alt+Shift+<key>` in `gcin_engine_process_key_event()` before
routing to feedkey functions, and call a new `gcin_core_feed_phrase(keyval, modifiers)`
API that wraps `feed_phrase()` from `phrase.cpp` (already compiled into libgcin-core.a).

**How gcin does it:**

In `eve.cpp`, before any input-method dispatch, two separate intercepts both call
`feed_phrase()`:

```c
/* eve.cpp:1227 — Alt+Shift → phrase.table */
if ((kev_state & (Mod1Mask|ShiftMask)) == (Mod1Mask|ShiftMask))
    return feed_phrase(keysym, kev_state);

/* eve.cpp:1293 — Ctrl (alone) → phrase-ctrl.table */
if (kev_state & ControlMask)
    if (feed_phrase(keysym, kev_state)) return TRUE;
```

`feed_phrase()` is in `phrase.cpp` (compiled). It internally routes to `tran`
(phrase.table) or `tran_ctrl` (phrase-ctrl.table) based on `ControlMask`.
With our build (phrase buffer off, `current_method_type()` returns 0), it calls
`send_text(str)` directly — the same path as all other committed text.
If the key is not in the table, `feed_phrase()` returns FALSE and the key passes through.

**`phrase.table`** (Alt+Shift):
```
Alt+Shift+i  →  、       Alt+Shift+h  →  「      Alt+Shift+j  →  」
Alt+Shift+o  →  。       Alt+Shift+f  →  『      Alt+Shift+g  →  』
Alt+Shift+,  →  ，       Alt+Shift+[  →  【      Alt+Shift+]  →  】
Alt+Shift+.  →  ‧       Alt+Shift+;  →  ；      Alt+Shift+k  →  §
Alt+Shift+m  →  ─       Alt+Shift+l  →  │       (+ box drawing, etc.)
```

**`phrase-ctrl.table`** (Ctrl):
```
Ctrl+,  →  ，    Ctrl+.  →  。    Ctrl+'  →  、
Ctrl+;  →  ；    Ctrl+/  →  ？    Ctrl+[  →  「    Ctrl+]  →  」
```

Both tables are user-editable.

**Why a wrapper instead of calling feed_phrase() directly from gcin_engine.c:**
`feed_phrase()` is declared in `phrase.cpp` with C++ linkage; the engine is C.
`gcin_core_feed_phrase()` in `gcin_stubs.cpp` provides the `extern "C"` bridge and
keeps the engine layer isolated from libgcin-core internals.

**Data files:** `phrase.table` and `phrase-ctrl.table` must be added to the install
target so `feed_phrase()` can find them at runtime alongside the other table files.

### 8. Unified switcher engine (`gcin-everywhere`): Ctrl+Alt+digit switches mode in place

**Decision:** Add a 7th IBus engine, `gcin-everywhere`, that is **not** bound to a
single input method. Inside it, `Ctrl+Alt+<digit>` switches the active method in place,
mirroring gcin's native hotkeys. The six single-method engines are unchanged; the
switching code is gated so it only runs for `gcin-everywhere`.

**How gcin does it:**

In `eve.cpp:1240`, when Ctrl+Alt is held, gcin maps the keysym to an input-method
index and switches the active method in-process:

```c
/* eve.cpp:1240 */
if ((kev_state & ControlMask) && (kev_state & (Mod1Mask|Mod5Mask))) {
    ...
    int kidx = gcin_switch_keys_lookup(keysym);   // scan inmd[] for matching key_ch
    if (kidx < 0) return FALSE;
    current_CS->im_state = GCIN_STATE_CHINESE;
    init_in_method(kidx);                          // switch cur_inmd / gtab in place
    return TRUE;
}
```

`gcin_switch_keys_lookup()` (`gtab-list.cpp:156`) scans `inmd[]` for the entry whose
`key_ch` (2nd column of `gtab.list`) equals the pressed digit. This is purely
*intra-process* state — exactly what our engine already does per keypress via
`feedkey_gtab_method()` (sets `current_CS->in_method` + `init_gtab()`).

**Why this maps cleanly onto our architecture:** `gcin_engine.c` already has a mutable
`e->mode` field and a `switch(e->mode)` dispatch in `process_key_event()`. The single-
method engines fix `e->mode` once in `enable()` from the engine-name suffix. The unified
engine just makes `e->mode` **mutable at runtime**: a Ctrl+Alt+digit handler maps the
digit to a mode and updates `e->mode`. No core changes are needed — the per-mode feedkey
functions (`gcin_core_feedkey_cangjie/zhuyin/quick/array/cj5/simplex_punc`) already
perform the `init_gtab()`/`in_method` switch on their first call after a mode change.

**Digit → mode mapping** (follows gcin's `gtab.list` `key_ch` where defined; 4/5 are
extensions since gcin assigns Quick and SimplexPunc `-`, not a digit):

| Hotkey | gcin `key_ch` | `e->mode` | Method |
|--------|---------------|-----------|--------|
| `Ctrl+Alt+1` | `1` | 0 | 倉頡 Cangjie |
| `Ctrl+Alt+2` | `2` | 4 | 倉五 CJ5 |
| `Ctrl+Alt+3` | `3` | 1 | 注音 Zhuyin |
| `Ctrl+Alt+4` | (ext.) | 2 | 速成 Quick |
| `Ctrl+Alt+5` | (ext.) | 5 | 標點簡易 SimplexPunc |
| `Ctrl+Alt+8` | `8` | 3 | 行列 Array |

**Handler placement:** the Ctrl+Alt+digit check must run **first** in
`process_key_event()` — before the existing "Ctrl (without Alt) → phrase-ctrl.table"
intercept (which requires `!(modifiers & MOD1)` and so won't fire on Ctrl+Alt anyway)
and before the feedkey dispatch. On a recognized digit: reset composition state, update
`e->mode`, update the panel property (below), and return `TRUE` (consume). An
unrecognized digit/key under Ctrl+Alt returns `FALSE` to pass through to the app.

**Gating to the unified engine:** `gcin_engine_enable()` sets `e->allow_switch = TRUE`
only when the engine name ends with `everywhere` (and starts that engine in Cangjie =
mode 0); for the six single-method engines `allow_switch` stays `FALSE` so Ctrl+Alt+digit
falls through to the app as before.

**Visual feedback — IBus property:** the unified engine registers a single
`IBusProperty` (type `PROP_TYPE_NORMAL`) in `gcin_engine_constructed`/`enable` via
`ibus_engine_register_properties()`. On each switch, `ibus_engine_update_property()`
updates the property's **symbol** and **label** to the active method (全→倉/注/速/列/五/標),
so the GNOME panel shows which method is live. The single-method engines do not register
this property.

**Why a 7th engine rather than replacing the six:** the dedicated engines remain useful
for users who want a fixed method and an accurate panel label; `gcin-everywhere` is an
additive convenience that reproduces gcin's all-in-one switching UX.

**English toggle — `Ctrl+Space` (gcin-native `gcin_im_toggle`):** within
`gcin-everywhere`, `Ctrl+Space` flips the engine's `chinese_mode` flag between Chinese
input and English passthrough. In English mode `process_key_event()` returns FALSE for
every key (the app receives raw keystrokes); the active method (`e->mode`) is untouched,
so toggling back resumes it. The panel property shows 英 in English mode. The handler is
placed **before** the `if (!chinese_mode) return FALSE` early-return so it can also turn
Chinese back on. The single-method engines do not toggle — they return FALSE for
`Ctrl+Space` so desktop source-switching still works there.

**Why this needs desktop config, not just code:** on GNOME/Wayland, mutter checks its
own keyboard shortcuts *before* forwarding a key to the IBus engine. If any desktop
shortcut binds plain `Ctrl+Space` (GNOME's `switch-input-source` /
`switch-input-source-backward`, or IBus's legacy `general.hotkey.trigger`), the key
never reaches the engine and the toggle can't fire. Those bindings must be cleared (or
moved to `Shift+Ctrl+Space` / `Super+Space`) so plain `Ctrl+Space` reaches the engine.
Symmetric two-press behavior when switching desktop input sources is the tell-tale of a
double-bound `Ctrl+Space`. See [HANDOFF key design decisions](HANDOFF.md#key-design-decisions).

---

### 9. GNOME panel indicator: state file + GNOME Shell extension

**Problem.** `gcin-everywhere` is a single IBus engine, and GNOME Shell's top-bar input
indicator renders only an engine's **static `symbol` from the component XML** (全). It
**ignores live `IBusProperty` symbol updates**, so the symbol-flipping in decision 8 — which
works on KDE and the standalone `ibus-ui-gtk3` panel — is a no-op on GNOME. The user has no
way to tell which method is active.

**Decision.** Publish the active method from the engine to a small state file and render it
with a bundled GNOME Shell extension. This rides *alongside* the existing IBus property — no
mechanism is removed — so each desktop uses whatever it supports.

- **Engine → state file.** `write_state()` writes `$XDG_RUNTIME_DIR/gcin-everywhere/state`
  as `"<glyph>\t<label>"` (e.g. `注\t注音 Zhuyin`; `英\t英文 English` in English mode), or an
  **empty** file when the engine is disabled. It's called from `update_property()` (so it
  tracks every switch, `enable`, and `focus_in`) and from `disable()` (to clear). Gated on
  `allow_switch`, so the six single-method engines never write it.
- **Extension ← state file.** `gcin-everywhere@gcin.dev` (GNOME 45+ ESM) is a
  `PanelMenu.Button` with an `St.Label`. A `Gio.FileMonitor` on the state **directory**
  (robust against atomic replacement) drives a refresh that reads the file, sets the glyph,
  and **shows the button only when the file is non-empty** — i.e. only while gcin-everywhere
  is the active source. inotify-driven, no polling.

**Why a file, not D-Bus.** A watched file needs zero new D-Bus plumbing in the C engine and
is equally responsive via inotify. The extension's mere existence is the "GNOME detection"
required by FR10 — on non-GNOME desktops nothing reads the file and the IBus property drives
the native panel; the engine doesn't branch on desktop type.

**Visibility = engine lifecycle.** Populated on `enable`, emptied on `disable`, so the
indicator appears and disappears with the gcin-everywhere source — satisfying "show only on
the switcher engine". On Wayland the extension must be enabled once and the session
restarted (logout/in) for GNOME Shell to load it. See
[HANDOFF key design decisions](HANDOFF.md#key-design-decisions).

---

## Data Model

### Cangjie (table-based) input flow

```
Key sequence (e.g., "dm" for 大木)
    ↓
gtab key buffer (accumulates up to MAX_GTAB_KEYS keys)
    ↓
Binary search in INMD.items[] (sorted ITEM array from cj.gtab)
    ↓
Candidate list: array of Unicode characters
    ↓
IBus lookup table → user selects → commit UTF-8 character
```

**Key structure:** `ITEM` — maps a packed key bitmask to a Unicode codepoint.
**Table metadata:** `TableHead` — describes the input method (name, max key length, selection keys).
**Runtime state:** `INMD` — loaded table + current key buffer + candidate array.

### Zhuyin (phonetic) input flow

```
Phonetic key (e.g., ㄓ ㄨ ˋ for "住")
    ↓
Phonetic buffer: initial + medial + final + tone
    ↓
Lookup in pho.tab (phonetic → Unicode codepoint list)
    ↓
Candidate list (filtered by tsin word frequency if phrase mode)
    ↓
IBus lookup table → user selects → commit UTF-8 character(s)
```

**Key structure:** `pho_item` — maps a phonetic code (initial/medial/final/tone packed) to a Unicode codepoint.
**Keyboard layout:** Configurable (Standard/Hsu/IBM/etc.) — stored in `.kbmsrc` / compiled keyboard map.

### IBus Engine State (per engine instance)

```c
typedef struct {
    IBusEngine parent;          // must be first
    INMD      *inmd;            // gcin input method descriptor (Cangjie) or NULL
    pho_state  pho;             // gcin phonetic state (Zhuyin) or zeroed
    IBusLookupTable *table;     // candidate table (reused across key events)
    engine_mode_t mode;         // CANGJIE or ZHUYIN
    int        input_mode;      // Chinese vs. English passthrough
} GcinEngine;
```

---

## IBus Engine Interface

The IBus engine implements these virtual methods by subclassing `IBusEngine`:

| Method | Trigger | Action |
|--------|---------|--------|
| `engine_enable` | User selects this input source | Load data tables, initialize gcin state |
| `engine_disable` | User switches away | Reset gcin state, clear preedit |
| `engine_process_key_event` | Every keypress in a focused app | Route key to gcin; update preedit + candidates; commit on confirmation |
| `engine_candidate_clicked` | User clicks a candidate | Commit the clicked character |
| `engine_property_activate` | User changes a property | Switch between Chinese/English mode |
| `engine_reset` | Focus lost or ESC | Clear preedit and candidate state |
| `engine_focus_out` | App loses focus | Same as reset |

### Key routing logic in `engine_process_key_event`

```
if key is modifier-only → return FALSE (pass through)
if in English passthrough mode → return FALSE
if mode == CANGJIE:
    forward to gtab key handler
    if output ready → commit via ibus_engine_commit_text()
    update preedit via ibus_engine_update_preedit_text()
    update candidates via ibus_engine_update_lookup_table()
if mode == ZHUYIN:
    forward to pho key handler
    same update sequence
return TRUE (key consumed)
```

---

**Last Updated:** 2026-06-22 (added decision 9: GNOME panel indicator extension)
