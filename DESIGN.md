# Design: gcin-everywhere

**Project:** gcin-everywhere
**Created:** 2026-05-04
**Last Updated:** 2026-05-04

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

### 6. Cangjie punctuation: intercept before feedkey_gtab, not inside gcin

**Decision:** Chinese punctuation for Cangjie is handled in `gcin_core_feedkey_cangjie()` by a lookup table that fires the commit callback directly, before the key reaches `feedkey_gtab()`.

**Background:** In gcin's original Cangjie flow, `feedkey_gtab` has no punctuation interception. Chinese punctuation is delivered via `full_char_proc()` (in excluded `eve.cpp`) which activates only when the user manually toggles a full-width character mode (`b_half_full_char`). For Zhuyin, `feedkey_pho` calls `pre_punctuation()` (in `tsin.cpp`, compiled) — but `pre_punctuation` routes through `add_to_tsin_buf()` for non-PHO methods rather than calling `send_text()` directly, because our `current_method_type()` stub returns 0.

**Decision detail:** When `ggg.ci == 0` (no Cangjie composition in progress) and the keyval matches a shifted punctuation key, `gcin_core_feedkey_cangjie()` fires the commit callback with the Chinese punctuation character and returns 1 (consumed). The mapping reuses gcin's existing `pre_punctuation()` table:

| Key (shifted) | Keyval | Chinese |
|--------------|--------|---------|
| Shift+, | `<` | ， |
| Shift+. | `>` | 。 |
| Shift+/ | `?` | ？ |
| Shift+; | `:` | ： |
| Shift+' | `"` | ； |
| Shift+[ | `{` | 「 |
| Shift+] | `}` | 」 |
| Shift+1 | `!` | ！ |
| Shift+- | `_` | —— |

**Why not reuse `pre_punctuation()` directly?** `pre_punctuation_sub()` branches on `current_method_type() == method_type_PHO`. Since our `current_method_type()` stub returns 0, the else-branch routes to `add_to_tsin_buf()` + `flush_tsin_buffer()` — the phrase buffer path. Intercepting in `gcin_core_feedkey_cangjie()` with a direct `send_text()` call is simpler and avoids that complexity.

**When NOT to intercept:** If `ggg.ci > 0` (a Cangjie key sequence is in progress), the punctuation key is passed to `feedkey_gtab()` unchanged — it may be a valid component key or trigger candidate display.

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

**Last Updated:** 2026-05-05 (added decision 6: Cangjie punctuation interception)
