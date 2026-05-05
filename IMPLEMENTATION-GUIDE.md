# Implementation Guide: gcin-everywhere

**Project:** gcin-everywhere
**Created:** 2026-05-04
**Last Updated:** 2026-05-04

---

## Navigation

**Project Docs:** [README](README.md) | [SPEC](SPEC.md) | [DESIGN](DESIGN.md) | [IMPLEMENTATION-GUIDE](IMPLEMENTATION-GUIDE.md) *(you are here)* | [HANDOFF](HANDOFF.md)

**This Document:**
- [Prerequisites](#prerequisites)
- [Repository Layout](#repository-layout)
- [Key Finding: GTK3 Dependency](#key-finding-gtk3-dependency)
- [Phase 1: Stub Layer](#phase-1-stub-layer)
- [Phase 2: IBus Engine Skeleton](#phase-2-ibus-engine-skeleton)
- [Phase 3: Cangjie Integration](#phase-3-cangjie-integration)
- [Phase 4: Zhuyin Integration](#phase-4-zhuyin-integration)
- [Phase 5: IBus Registration & Install](#phase-5-ibus-registration--install)
- [gcin Source File Reference](#gcin-source-file-reference)

---

## Prerequisites

Build dependencies (Debian/Ubuntu package names):

```bash
# IBus and GLib
sudo apt install libibus-1.0-dev libglib2.0-dev

# GTK3 — required for gcin source compilation (gcin.h / gtab.cpp pull in gtk/gtk.h)
sudo apt install libgtk-3-dev

# X11 — required for gcin header types (Display*, Window, etc.)
sudo apt install libx11-dev

# gcin's own build tools (to compile data tables)
# Build gcin first to get cintotab and other tools:
cd sources/gcin-everywhere/gcin
./configure && make
```

Verify IBus dev headers are present:
```bash
pkg-config --cflags ibus-1.0    # should print include paths
pkg-config --cflags gtk+-3.0    # should print include paths
```

---

## Repository Layout

```
sources/gcin-everywhere/
├── gcin/                        gcin upstream (submodule)
│   ├── data/                    source tables (.cin, .tab2.src, .kbmsrc)
│   ├── gtab.cpp / gtab.h        table-based input engine (Cangjie)
│   ├── pho.cpp / pho.h          phonetic input engine (Zhuyin)
│   └── ...                      other gcin source files
│
└── ibus-engine/                 NEW — IBus engine wrapper
    ├── Makefile                 builds ibus-engine-gcin binary
    ├── gcin_engine.c            IBus GObject subclass (IBus protocol)
    ├── gcin_adapter.cpp         X11 stub shim + key routing
    ├── gcin_stubs.cpp           stub implementations of gcin globals/UI calls
    └── component/
        └── gcin.xml             IBus component registration file
```

---

## Key Finding: GTK3 Dependency

gcin's source files (`gtab.cpp`, `pho.cpp`, etc.) include `<gtk/gtk.h>` directly and
declare X11 types (`Display *dpy`, `Window xwin0`, `GtkWidget *gwin0`) as external globals.

**This means:**
- GTK3 headers must be present at compile time — even though the IBus engine never opens a window.
- `libgtk-3-dev` and `libx11-dev` are compile-time dependencies.
- At runtime, these globals are set to NULL (stubbed). The key-processing code paths in
  `gtab.cpp` and `pho.cpp` never dereference them during normal input operation.
- Only the UI/window code paths (candidate window, tray icon, etc.) use them — those
  code paths are excluded from the IBus engine binary entirely.

**Excluded gcin files** (never compiled into the IBus engine):
- `gcin.cpp` — main application entry point
- `win-*.cpp`, `win0.cpp`, `win1.cpp` — candidate/status window UI
- `gcin-icon.cpp`, `tray.cpp`, `eggtrayicon.cpp` — system tray
- `IMdkit/` — X11 XIM server (entire directory)
- `im-srv.cpp`, `im-addr.cpp`, `im-dispatch.cpp` — XIM client dispatch
- `gcin-setup*.cpp` — settings UI
- `gcin-module.cpp` — plugin module loader

---

## Phase 1: Stub Layer

**Goal:** Compile gcin's core files without linker errors by providing stub definitions
for everything the IBus engine won't actually use.

### 1a. gcin_stubs.cpp

Create `ibus-engine/gcin_stubs.cpp`. This file provides:

- **Global variable stubs** — `Display *dpy = NULL`, `GtkWidget *gwin0 = NULL`, etc.
- **UI function stubs** — empty bodies for `send_gcin_message()`, `set_no_focus()`, etc.
- **`send_text()` / `send_utf8_ch()` intercepts** — instead of sending to X11 clients,
  store the committed text in a thread-local buffer for the IBus engine to pick up.

Key stubs needed (inspect linker errors to find the full list):

```cpp
// X11 globals
Display *dpy = NULL;
Window xwin0 = 0;
int dpy_xl = 1920, dpy_yl = 1080;  // dummy screen size

// GTK globals
GtkWidget *gwin0 = NULL;

// gcin state
int current_CS = 0;  // no active client
char TableDir[256];  // set from $HOME/.gcin or /usr/share/gcin

// Output intercept — IBus engine reads these after each key event
static char committed_text[256];
static int  committed_len = 0;

void send_text(char *text) {
    strncpy(committed_text, text, sizeof(committed_text)-1);
    committed_len = strlen(text);
}

void send_utf8_ch(char *ch) {
    // CH_SZ bytes (4 bytes max for UTF-8)
    memcpy(committed_text, ch, CH_SZ);
    committed_len = strnlen(ch, CH_SZ);
}

void send_ascii(char key) {
    committed_text[0] = key;
    committed_text[1] = '\0';
    committed_len = 1;
}

// Accessor for IBus engine to retrieve committed text
const char *gcin_get_committed(int *len) {
    *len = committed_len;
    committed_len = 0;  // consume
    return committed_text;
}
```

### 1b. Build smoke test

Write a minimal `Makefile` that compiles `gtab.cpp` + `gcin_stubs.cpp` together and
links — the goal is zero linker errors before writing any IBus code.

```makefile
GCIN     = ../gcin
CXXFLAGS = $(shell pkg-config --cflags gtk+-3.0) -I$(GCIN) -I$(GCIN)/IMdkit -DHAVE_CONFIG_H
LDFLAGS  = $(shell pkg-config --libs gtk+-3.0)

GCIN_SRCS = \
    $(GCIN)/gtab.cpp \
    $(GCIN)/gtab-init.cpp \
    $(GCIN)/gtab-list.cpp \
    $(GCIN)/gtab-buf.cpp \
    $(GCIN)/gtab-util.cpp \
    $(GCIN)/gtab-tsin-fname.cpp \
    $(GCIN)/util.cpp \
    $(GCIN)/gcin-conf.cpp \
    $(GCIN)/gcin-common.cpp \
    $(GCIN)/fullchar.cpp \
    $(GCIN)/cache.cpp \
    $(GCIN)/tsin.cpp \
    $(GCIN)/tsin-util.cpp \
    $(GCIN)/tsin-char.cpp \
    $(GCIN)/tsin-scan.cpp \
    $(GCIN)/lang.cpp

smoke-test: gcin_stubs.cpp $(GCIN_SRCS)
    $(CXX) $(CXXFLAGS) $^ $(LDFLAGS) -o smoke-test
```

Iterate: compile, read linker errors, add stubs, repeat until it links.

---

## Phase 2: IBus Engine Skeleton

**Goal:** A minimal IBus engine that registers with ibus-daemon and does nothing yet.

### 2a. gcin_engine.c — IBus GObject skeleton

```c
#include <ibus.h>

/* Forward declarations */
static void gcin_engine_class_init(GcinEngineClass *klass);
static void gcin_engine_init(GcinEngine *engine);
static gboolean gcin_engine_process_key_event(IBusEngine *engine,
    guint keyval, guint keycode, guint modifiers);
static void gcin_engine_enable(IBusEngine *engine);
static void gcin_engine_disable(IBusEngine *engine);
static void gcin_engine_reset(IBusEngine *engine);
static void gcin_engine_focus_out(IBusEngine *engine);

typedef struct _GcinEngine      GcinEngine;
typedef struct _GcinEngineClass GcinEngineClass;

struct _GcinEngine {
    IBusEngine  parent;
    IBusLookupTable *table;
    int          mode;          // 0=Cangjie, 1=Zhuyin
    gboolean     chinese_mode; // TRUE=Chinese, FALSE=English passthrough
};

struct _GcinEngineClass {
    IBusEngineClass parent;
};

G_DEFINE_TYPE(GcinEngine, gcin_engine, IBUS_TYPE_ENGINE)

static void gcin_engine_class_init(GcinEngineClass *klass) {
    IBusEngineClass *engine_class = IBUS_ENGINE_CLASS(klass);
    engine_class->process_key_event = gcin_engine_process_key_event;
    engine_class->enable            = gcin_engine_enable;
    engine_class->disable           = gcin_engine_disable;
    engine_class->reset             = gcin_engine_reset;
    engine_class->focus_out         = gcin_engine_focus_out;
}

static void gcin_engine_init(GcinEngine *engine) {
    engine->table = ibus_lookup_table_new(10, 0, TRUE, TRUE);
    g_object_ref_sink(engine->table);
    engine->chinese_mode = TRUE;
}

static gboolean gcin_engine_process_key_event(IBusEngine *engine,
        guint keyval, guint keycode, guint modifiers) {
    // Phase 3 and 4 will fill this in
    return FALSE;  // pass all keys through for now
}

static void gcin_engine_enable(IBusEngine *engine)   { /* Phase 3 */ }
static void gcin_engine_disable(IBusEngine *engine)  { /* Phase 3 */ }
static void gcin_engine_reset(IBusEngine *engine)    { /* Phase 3 */ }
static void gcin_engine_focus_out(IBusEngine *engine){ /* Phase 3 */ }

int main(int argc, char *argv[]) {
    ibus_init();
    IBusBus *bus = ibus_bus_new();
    g_assert(ibus_bus_is_connected(bus));

    IBusFactory *factory = ibus_factory_new(ibus_bus_get_connection(bus));
    ibus_factory_add_engine(factory, "gcin-cangjie",
                            GCIN_TYPE_ENGINE);  // same type, mode set per engine name

    ibus_bus_request_name(bus, "org.freedesktop.IBus.Gcin", 0);
    ibus_main();
    return 0;
}
```

### 2b. component/gcin.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<component>
  <name>org.freedesktop.IBus.Gcin</name>
  <description>gcin Traditional Chinese Input Method</description>
  <exec>/usr/lib/ibus-gcin/ibus-engine-gcin</exec>
  <version>0.1</version>
  <author>gcin-everywhere contributors</author>
  <license>GPL</license>
  <homepage>https://github.com/pkg-ime/gcin</homepage>
  <textdomain>gcin</textdomain>

  <engines>
    <engine>
      <name>gcin-cangjie</name>
      <language>zh_TW</language>
      <license>GPL</license>
      <author>gcin-everywhere contributors</author>
      <icon>ibus-gcin</icon>
      <longname>gcin Cangjie (倉頡)</longname>
      <description>Cangjie Traditional Chinese input via gcin engine</description>
      <rank>99</rank>
      <symbol>倉</symbol>
      <layout>default</layout>
    </engine>

    <engine>
      <name>gcin-zhuyin</name>
      <language>zh_TW</language>
      <license>GPL</license>
      <author>gcin-everywhere contributors</author>
      <icon>ibus-gcin</icon>
      <longname>gcin Zhuyin (注音)</longname>
      <description>Zhuyin/Bopomofo Traditional Chinese input via gcin engine</description>
      <rank>99</rank>
      <symbol>注</symbol>
      <layout>default</layout>
    </engine>
  </engines>
</component>
```

### 2c. Verify skeleton registers

```bash
# Install the component XML
sudo cp component/gcin.xml /usr/share/ibus/component/

# Run the engine manually (ibus-daemon must already be running)
./ibus-engine-gcin &

# Check it registered
ibus list-engine | grep gcin
```

Expected output:
```
language: zh_TW, name: gcin-cangjie, longname: gcin Cangjie (倉頡), ...
language: zh_TW, name: gcin-zhuyin, longname: gcin Zhuyin (注音), ...
```

---

## Phase 3: Cangjie Integration

**Goal:** `process_key_event` routes keys to gcin's gtab engine and commits characters.

### 3a. gcin_adapter.cpp — initialization and key routing

```cpp
// Called once at engine startup
void gcin_adapter_init(const char *table_dir) {
    strncpy(TableDir, table_dir, sizeof(TableDir)-1);
    load_gtab_list(FALSE);   // gcin function: loads all .gtab files
    // Select Cangjie: find INMD entry by name
    for (int i = 0; i < inmdN; i++) {
        if (strstr(inmd[i].cname, "倉頡") || strstr(inmd[i].filename, "cj.gtab")) {
            cur_inmd = &inmd[i];
            break;
        }
    }
}

// Called per keypress
// Returns: TRUE if key was consumed, FALSE to pass through
gboolean gcin_adapter_process_key(guint keyval, guint modifiers,
                                   char *preedit_out, char **candidates_out, int *n_candidates) {
    // Delegate to gtab key handler
    // gcin's gtab key handler is gcin_gtab_key_press() in gtab.cpp
    // It updates internal state and may call send_text() / send_utf8_ch()
    // ...
}
```

**Note:** The exact gcin function to call for key dispatch needs to be identified by
reading `gtab.cpp`'s key handler. Look for the function called from `gcin.cpp`'s
key-press event handler (search for `GDK_KEY_PRESS` or `key_press_event`).

### 3b. Key routing in process_key_event

```c
static gboolean gcin_engine_process_key_event(IBusEngine *iengine,
        guint keyval, guint keycode, guint modifiers) {
    GcinEngine *engine = (GcinEngine *)iengine;

    // Ignore release events
    if (modifiers & IBUS_RELEASE_MASK)
        return FALSE;

    // English passthrough
    if (!engine->chinese_mode)
        return FALSE;

    // Delegate to gcin adapter
    char preedit[256] = {0};
    char *candidates[64] = {0};
    int  n_cands = 0;
    gboolean consumed = gcin_adapter_process_key(keyval, modifiers,
                                                  preedit, candidates, &n_cands);

    // Check if gcin committed something via send_text()
    int committed_len = 0;
    const char *committed = gcin_get_committed(&committed_len);
    if (committed_len > 0) {
        IBusText *text = ibus_text_new_from_string(committed);
        ibus_engine_commit_text(iengine, text);
        g_object_unref(text);
    }

    // Update preedit
    if (preedit[0]) {
        IBusText *pre = ibus_text_new_from_string(preedit);
        ibus_engine_update_preedit_text(iengine, pre, strlen(preedit), TRUE);
        g_object_unref(pre);
    } else {
        ibus_engine_hide_preedit_text(iengine);
    }

    // Update candidate lookup table
    ibus_lookup_table_clear(engine->table);
    for (int i = 0; i < n_cands; i++) {
        IBusText *cand = ibus_text_new_from_string(candidates[i]);
        ibus_lookup_table_append_candidate(engine->table, cand);
        g_object_unref(cand);
    }
    if (n_cands > 0)
        ibus_engine_update_lookup_table(iengine, engine->table, TRUE);
    else
        ibus_engine_hide_lookup_table(iengine);

    return consumed;
}
```

---

## Phase 4: Zhuyin Integration

**Goal:** Same as Phase 3 but routing to gcin's phonetic engine (`pho.cpp`).

gcin's Zhuyin processing is in `pho.cpp`. The adapter needs:
- `pho_load()` — load the phonetic table (declared in `pho.h`)
- A key handler that maps IBus keysyms to gcin's phonetic key codes
- Tone key detection (ˊˋ˙ˇ and space for tone 1)

The keyboard layout mapping (Standard/Hsu/IBM/etc.) is in `.kbmsrc` files compiled
into a keyboard map. Start with the Standard (大千) layout.

The Zhuyin flow differs from Cangjie: keys accumulate a phonetic syllable buffer
(initial consonant + medial + final + tone), and candidates appear only after the
tone key is pressed.

---

## Phase 5: IBus Registration & Install

### Install paths

```
/usr/lib/ibus-gcin/ibus-engine-gcin     the engine binary
/usr/share/ibus/component/gcin.xml      IBus component registration
/usr/share/gcin/                        data tables (cj.gtab, pho.tab, tsin, etc.)
```

### Makefile install target

```makefile
DESTDIR ?=
LIBDIR  = $(DESTDIR)/usr/lib/ibus-gcin
DATADIR = $(DESTDIR)/usr/share/gcin
COMPDIR = $(DESTDIR)/usr/share/ibus/component

install: ibus-engine-gcin
    install -Dm755 ibus-engine-gcin $(LIBDIR)/ibus-engine-gcin
    install -Dm644 component/gcin.xml $(COMPDIR)/gcin.xml
    install -Dm644 ../gcin/data/*.gtab $(DATADIR)/
    install -Dm644 ../gcin/data/pho.tab $(DATADIR)/
    install -Dm644 ../gcin/data/tsin $(DATADIR)/
```

### Activate and test

```bash
sudo make install
ibus restart
# Open GNOME Settings → Keyboard → Input Sources → Add → Chinese (Traditional) → gcin Cangjie
# Switch to gcin Cangjie, open gedit, type: d (大) i (人) = 大人
```

---

## gcin Source File Reference

### Files to compile into ibus-engine-gcin

| File | Purpose |
|------|---------|
| `gtab.cpp` | Table-based input engine core (Cangjie) |
| `gtab-init.cpp` | Table initialization, loading from .gtab files |
| `gtab-list.cpp` | Input method list management |
| `gtab-buf.cpp` | Key buffer management |
| `gtab-util.cpp` | Table utilities |
| `gtab-tsin-fname.cpp` | Data file path resolution |
| `pho.cpp` | Phonetic engine core (Zhuyin) |
| `pho-lookup.cpp` | Phonetic character lookup |
| `pho-util.cpp` | Phonetic utilities |
| `pho-kbm-name.cpp` | Keyboard layout names |
| `phoa2d.cpp` | Phonetic array-to-data conversion |
| `phod2a.cpp` | Phonetic data-to-array conversion |
| `tsin.cpp` | Word frequency database |
| `tsin-util.cpp` | tsin utilities |
| `tsin-char.cpp` | tsin character handling |
| `tsin-scan.cpp` | tsin scanning |
| `util.cpp` | General utilities |
| `gcin-conf.cpp` | Configuration loading |
| `gcin-common.cpp` | Common helpers |
| `fullchar.cpp` | Full-width character conversion |
| `cache.cpp` | Table caching |
| `lang.cpp` | Language utilities |

### Files to stub (do not compile, provide empty replacements)

| File | Reason |
|------|--------|
| `gcin-send.cpp` | Intercept `send_text()` — replaced by `gcin_stubs.cpp` |
| `IC.cpp` | X11 input context — not needed |
| `win-*.cpp`, `win0.cpp`, `win1.cpp` | Candidate window UI — not needed |
| `gcin-module.cpp` | Plugin loading — not needed |
| All of `IMdkit/` | X11 XIM server — not needed |

### Key data files (built by gcin's own tools)

| File | Built from | Input method |
|------|-----------|-------------|
| `data/cj.gtab` | `data/cj.cin` via `cintotab` | Cangjie (倉頡) |
| `data/pho.tab` | `data/pho.tab2.src` via `phoconv` | Zhuyin Standard layout |
| `data/tsin` | `data/tsin.src` | Word frequency database |

---

**Last Updated:** 2026-05-04
