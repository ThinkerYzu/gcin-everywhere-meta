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

1. **Minimize gcin changes.** The gcin core is mature and correct. Extract what is needed without modifying its input logic.
2. **Clean platform boundary.** All X11/display-specific code is replaced by a thin adapter at the boundary, not patched throughout the source.
3. **IBus built-in UI.** Candidate display is delegated entirely to IBus — no custom windowing code needed.
4. **Small scope.** Phase 1 ships one working thing: Cangjie and Zhuyin on GNOME/Wayland. No feature creep.

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
│             ibus-engine-gcin  (NEW)                  │
│  ┌────────────────────────────────────────────────┐  │
│  │  IBus Engine GObject (gcin_engine.c)           │  │
│  │  - process_key_event()                         │  │
│  │  - enable() / disable()                        │  │
│  │  - property_activate() (input method switch)   │  │
│  └────────────────┬───────────────────────────────┘  │
│                   │ direct C function calls           │
│  ┌────────────────▼───────────────────────────────┐  │
│  │  gcin Core Adapter (gcin_adapter.c)  (NEW)     │  │
│  │  - Initializes gcin state                      │  │
│  │  - Routes keys to correct input module         │  │
│  │  - Returns: preedit string, candidates, commit │  │
│  │  - Provides stubs for X11/display globals      │  │
│  └───────────┬──────────────────┬─────────────────┘  │
│              │                  │                     │
│  ┌───────────▼──────┐  ┌───────▼─────────────────┐  │
│  │  gtab.cpp (gcin) │  │  pho.cpp / pho*.cpp      │  │
│  │  Cangjie engine  │  │  Zhuyin/Bopomofo engine  │  │
│  │  (ported as-is)  │  │  (ported as-is)          │  │
│  └───────────┬──────┘  └───────┬─────────────────-┘  │
│              │                  │                     │
│  ┌───────────▼──────────────────▼─────────────────┐  │
│  │  gcin Data Tables                              │  │
│  │  cj.cin → cj.gtab   (Cangjie table)            │  │
│  │  pho.tab2.src       (Zhuyin phonetic table)    │  │
│  │  tsin.src → tsin    (word frequency database)  │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Component Roles

| Component | Source | Role |
|-----------|--------|------|
| `ibus-engine-gcin` binary | New | Process launched by ibus-daemon |
| `gcin_engine.c` | New | IBus GObject: handles IBus protocol, calls adapter |
| `gcin_adapter.c` | New | Thin shim: initializes gcin, provides X11 stubs, routes keys |
| `gtab.cpp` | gcin (ported) | Table-based input: Cangjie key → candidate lookup |
| `pho.cpp` and related | gcin (ported) | Phonetic input: Zhuyin key accumulation and lookup |
| `data/cj.gtab` | gcin (built) | Compiled Cangjie character table |
| `data/pho.tab` | gcin (built) | Compiled Zhuyin phonetic table |
| `data/tsin` | gcin (built) | Word frequency database for phrase selection |
| `gcin.xml` | New | IBus component registration file |

---

## Key Design Decisions

### 1. Port gcin source files, don't link against a gcin library

**Decision:** Compile selected gcin `.cpp` files directly into the `ibus-engine-gcin` binary. Do not try to build gcin as a shared library.

**Rationale:** gcin was never designed as a library. It has many globals, no stable API, and X11 entangled throughout. Compiling only the needed files and providing stubs for the missing parts is far less invasive than restructuring gcin as a library.

**Files to include:** `gtab.cpp`, `gtab-pho.cpp`, phonetic engine files (`pho.cpp`, etc.), character conversion utilities. Exclude: `gcin.cpp` (main), `gtk-im/`, all X11/GTK UI code.

### 2. Stub out X11/display dependencies with a gcin_adapter layer

**Decision:** Create `gcin_adapter.c` that provides stub implementations of gcin's X11 globals (`dpy`, `gwin0`, `xwin0`, etc.) and UI functions (`send_text()`, `send_utf8_ch()`, etc.).

**Rationale:** gcin's input logic is intermixed with X11 calls, but many of them are never reached during a pure key-processing code path (they're in the UI update paths). Stubs let us compile the input files cleanly without modifying them.

**Boundary:** The adapter intercepts `send_text()` and `send_utf8_ch()` — these are gcin's output calls. Instead of sending to X11 clients, the adapter stores the result for the IBus engine to pick up and commit via `ibus_engine_commit_text()`.

### 3. One binary, two engines registered via IBus component XML

**Decision:** A single `ibus-engine-gcin` binary hosts both Cangjie and Zhuyin engines. The IBus component XML declares both as separate engine entries. The binary starts the correct engine based on the engine name passed by ibus-daemon.

**Rationale:** Simpler deployment and shared initialization cost for gcin data tables. IBus supports multiple engines per component.

### 4. Data tables compiled by gcin's existing build, loaded at runtime

**Decision:** The `.cin` and `.tab2.src` source files are compiled to binary format by gcin's existing tools (`cintotab`, `phoconv`) as part of the build. The IBus engine loads them at runtime from a fixed install path (e.g., `/usr/share/gcin/`).

**Rationale:** The table compiler is already correct and battle-tested. Reusing it avoids re-implementing the binary format. Runtime loading matches how gcin already works.

### 5. IBus built-in candidate window

**Decision:** Use `ibus_engine_update_lookup_table()` with IBus's built-in candidate window. No custom candidate UI.

**Rationale:** Simpler, integrates naturally with GNOME's IBus UI. Can revisit with a custom window in a later phase if the look and feel matters.

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

**Last Updated:** 2026-05-04
