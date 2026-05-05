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
- [Key Findings from Source Audit](#key-findings-from-source-audit)
- [Phase 1: libgcin-core.a](#phase-1-libgcin-corea)
- [Phase 2: IBus Engine Skeleton](#phase-2-ibus-engine-skeleton)
- [Phase 3: Cangjie Integration](#phase-3-cangjie-integration)
- [Phase 4: Zhuyin Integration](#phase-4-zhuyin-integration)
- [Phase 5: IBus Registration & Install](#phase-5-ibus-registration--install)
- [gcin Source File Reference](#gcin-source-file-reference)

---

## Prerequisites

Build dependencies (Debian/Ubuntu package names):

```bash
# IBus and GLib (runtime + dev)
sudo apt install libibus-1.0-dev libglib2.0-dev

# gcin's own build tools — needed to compile data tables (.cin → .gtab, etc.)
# Build gcin once to produce cintotab, phoconv, and the compiled tables:
cd sources/gcin-everywhere/gcin
./configure && make
```

**No GTK3 or X11 dev headers required** for libgcin-core.a — the compat headers
in `gcin-core/compat/` replace them with type stubs (see Phase 1).

---

## Repository Layout

```
sources/gcin-everywhere/
├── gcin/                    gcin upstream (submodule: github.com/pkg-ime/gcin)
│   └── data/                source tables (.cin, .tab2.src, .kbmsrc)
│
├── gcin-core/               NEW — platform-independent static library
│   ├── Makefile             builds libgcin-core.a
│   ├── gcin-core.h          public API (used by all platform integrations)
│   ├── gcin_stubs.cpp       extern globals + UI stubs + send_text callback
│   └── compat/              fake X11/GTK headers (compile-time only, not installed)
│       ├── gtk/gtk.h        GLib/GTK type stubs (gboolean, GHashTable, GtkWidget, ...)
│       ├── gdk/gdkx.h       empty
│       ├── X11/Xlib.h       X11 type stubs (Display, Window, KeySym, ...)
│       ├── X11/keysym.h     XK_* key constant definitions
│       ├── IMdkit.h         empty (included by gtab.cpp)
│       └── Xi18n.h          empty (included by gtab.cpp)
│
└── ibus-engine/             IBus platform integration (links libgcin-core.a)
    ├── Makefile
    ├── gcin_engine.c        IBus GObject subclass
    └── component/
        └── gcin.xml         IBus component registration
```

---

## Key Findings from Source Audit

### Entry points (confirmed by reading source)

| Function | File | Line | Purpose |
|----------|------|------|---------|
| `feedkey_gtab(KeySym key, int kbstate)` | `gcin/gtab.cpp` | 924 | Cangjie: process one keypress |
| `feedkey_gtab_release(KeySym key, int kbstate)` | `gcin/gtab-buf.cpp` | 1153 | Cangjie: key release |
| `feedkey_pho(KeySym xkey, int kbstate)` | `gcin/pho.cpp` | 517 | Zhuyin: process one keypress |

### IBus ↔ X11 key compatibility

IBus `keyval` values are numerically identical to X11 `KeySym` values — both use
the same key symbol table (XFree86/X.Org). IBus `modifiers` bits match X11 `kbstate`
bits exactly: `ShiftMask=1`, `LockMask=2`, `ControlMask=4`, `Mod1Mask=8`, etc.

**Consequence:** `feedkey_gtab(keyval, modifiers)` and `feedkey_pho(keyval, modifiers)`
can be called with IBus values directly — no translation layer needed.

### X11/GTK dependency strategy: compat headers

gcin source files include `<gtk/gtk.h>` and `<X11/Xlib.h>` for type definitions
(`gboolean`, `KeySym`, `GtkWidget`, etc.) and constants (`ShiftMask`, `XK_Escape`, etc.).

The key-processing code paths (`feedkey_gtab`, `feedkey_pho`, table loading, lookup)
never call actual GTK widget or X11 display functions at runtime — those calls only
appear in UI display functions that we stub out.

**Strategy:** Place `gcin-core/compat/` first on the include path. These fake headers
define all the needed types and constants, and turn GTK/X11 function calls into
no-ops via macros. No GTK3 or X11 dev packages needed at all.

### gcin source modifications required

Only **one file** needs a code change (the rest are handled by compat headers + stubs):

- **`gcin/util.cpp`** — `p_err()` calls `gtk_message_dialog_new()` and stores the
  result in a local `GtkWidget*`. While compat macros can make the GTK calls no-ops,
  `GtkWidget*` as a local variable type could cause issues depending on how `GtkWidget`
  is defined. Guard the dialog block with `#ifndef GCIN_CORE_BUILD` and use
  `p_err_no_alert()` (stderr only) instead.

All other problematic calls (`XBell`, `gdk_beep`, `gtk_label_set_text`, Pango calls,
`gdk_window_set_override_redirect`) are in functions that are either:
- Stubbed in `gcin_stubs.cpp` (entire function replaced), or
- Made into no-ops by macros in compat headers

### UI functions to stub in gcin_stubs.cpp

These are called from gcin core files but defined only in excluded UI files.
Provide empty/no-op bodies in `gcin_stubs.cpp`:

**Void stubs (no return value):**
`show_win_gtab`, `hide_win_gtab`, `show_win_pho`, `hide_win_pho`, `hide_win_kbm`,
`hide_win0`, `hide_row2_if_necessary`, `minimize_win_gtab`, `minimize_win_pho`,
`disp_gtab`, `disp_gbuf`, `disp_gtab_sel`, `disp_gtab_pre_sel`, `disp_selection0`,
`disp_pho`, `disp_pho_sel`, `disp_pho_sub`, `disp_label_edit`, `disp_char`,
`ClrIn`, `ClrSelArea`, `ClrPhoSelArea`, `clear_after_put`,
`clear_gtab_input_error_color`, `set_gtab_input_error_color`,
`set_key_codes_label`, `set_page_label`, `set_label_font_size`, `set_label_space`,
`set_no_focus`, `clr_in_area_pho`, `clr_tsin_cursor`,
`bell`, `disp_tray_icon`, `save_CS_current_to_temp`,
`show_tsin_stat`, `recreate_win1_if_nessary`,
`start_gtab_pho_query`, `close_gtab_pho_win`, `set_gtab_target_displayed`,
`pho_play`, `gtab_scan_pre_select`, `hide_gtab_pre_sel`,
`change_win_fg_bg`, `change_win_bg`

**Boolean stubs (return FALSE):**
`full_char_proc`, `shift_char_proc`, `pre_punctuation`, `pre_punctuation_hsu`,
`is_gtab_query_mode`, `use_tsin_sel_win`, `same_query_show_pho_win`,
`gcin_edit_display_ap_only`

**Other stubs:**
`send_gcin_message` (void), `exec_gcin_setup` (void),
`get_win_size` (void), `win32_init_win` (void)

### Output interception: send_text and send_utf8_ch

`send_text()` and `send_utf8_ch()` are declared in `gcin.h` and implemented in
`gcin-send.cpp` (XIM client dispatch — excluded). The library provides its own
implementations in `gcin_stubs.cpp` that fire a registered callback instead.

`send_ascii()` passes single-byte ASCII keys (e.g. when not in Chinese mode) — same
callback, single char.

---

## Phase 1: libgcin-core.a

**Goal:** A static library containing gcin's Cangjie and Zhuyin engines with no
X11/GTK runtime dependencies. Platform integrations (IBus, Windows TSF, macOS IMKit)
link against this library.

### 1a. compat/ headers

`gcin-core/compat/gtk/gtk.h` — provides GLib/GTK types and turns function calls into
no-ops:

```c
#pragma once
/* GLib types */
typedef int           gboolean;
typedef int           gint;
typedef unsigned int  guint;
typedef char          gchar;
typedef unsigned char guchar;
typedef long          glong;
typedef unsigned long gulong;
typedef void*         gpointer;
#define TRUE  1
#define FALSE 0
#define G_GNUC_UNUSED __attribute__((unused))

/* GObject/GLib stubs — used as types only, calls are no-ops */
typedef void GObject;
typedef void GHashTable;
typedef void GList;
typedef void GtkWidget;
typedef void GtkWindow;
typedef void GtkLabel;
typedef void GdkWindow;
typedef void PangoContext;
typedef void PangoFontDescription;

/* Macro stubs for GTK/GLib function calls */
#define g_object_ref(o)              ((void)(o))
#define g_object_unref(o)            ((void)(o))
#define g_object_ref_sink(o)         ((void)(o))
#define g_hash_table_new(a,b)        NULL
#define g_hash_table_insert(h,k,v)   ((void)(h))
#define g_hash_table_lookup(h,k)     NULL
#define g_hash_table_destroy(h)      ((void)(h))
#define g_list_append(l,d)           NULL
#define g_list_free(l)               ((void)(l))
#define g_malloc(n)                  malloc(n)
#define g_free(p)                    free(p)
#define g_strdup(s)                  strdup(s)
#define g_new(t,n)                   ((t*)malloc(sizeof(t)*(n)))
#define g_new0(t,n)                  ((t*)calloc((n),sizeof(t)))
#define g_realloc(p,n)               realloc(p,n)
#define gdk_beep()                   ((void)0)
#define gtk_label_set_text(l,s)      ((void)(l),(void)(s))
#define GTK_LABEL(l)                 ((GtkLabel*)(l))
#define GTK_WINDOW(w)                ((GtkWindow*)(w))
#define GTK_WIDGET(w)                ((GtkWidget*)(w))
#define GTK_DIALOG(d)                ((void*)(d))
#define GTK_DIALOG_MODAL             0
#define GTK_MESSAGE_ERROR            0
#define GTK_BUTTONS_CLOSE            0
#define gtk_message_dialog_new(...)  NULL
#define gtk_dialog_run(d)            ((void)(d))
#define gtk_widget_destroy(w)        ((void)(w))
#define gtk_widget_show(w)           ((void)(w))
#define gtk_widget_get_pango_context(w) NULL
#define gtk_widget_get_window(w)     NULL
#define gtk_widget_override_font(w,f) ((void)(w))
#define gtk_window_set_decorated(w,b) ((void)(w))
#define gtk_window_set_keep_above(w,b) ((void)(w))
#define gtk_window_set_accept_focus(w,b) ((void)(w))
#define gtk_window_set_type_hint(w,h) ((void)(w))
#define gtk_window_set_skip_taskbar_hint(w,b) ((void)(w))
#define GDK_WINDOW_TYPE_HINT_TOOLTIP 0
#define pango_font_description_from_string(s) NULL
#define pango_font_description_set_size(f,s) ((void)(f))
#define PANGO_SCALE 1024
#define pango_context_set_font_description(c,f) ((void)(c))
#define pango_font_description_free(f) ((void)(f))
#define gdk_window_set_override_redirect(w,b) ((void)(w))
```

`gcin-core/compat/X11/Xlib.h`:

```c
#pragma once
typedef void          Display;
typedef unsigned long Window;
typedef unsigned long KeySym;
typedef unsigned int  KeyCode;
#define XBell(dpy,vol) ((void)0)
#define XFlush(dpy)    ((void)0)
#define None           0L
```

`gcin-core/compat/X11/keysym.h` — X11 key symbol constants (copy verbatim from
`/usr/include/X11/keysym.h` or write the subset gcin uses):

Key XK_* values needed by gcin (at minimum):
`XK_Escape`, `XK_BackSpace`, `XK_Return`, `XK_space`, `XK_Tab`,
`XK_Delete`, `XK_Home`, `XK_End`, `XK_Left`, `XK_Right`, `XK_Up`, `XK_Down`,
`XK_Page_Up`, `XK_Page_Down`, `XK_Shift_L`, `XK_Shift_R`,
`XK_Control_L`, `XK_Control_R`, `XK_Caps_Lock`,
modifier masks: `ShiftMask=1`, `LockMask=2`, `ControlMask=4`,
`Mod1Mask=8`, `Mod4Mask=64`, `Mod5Mask=128`.

```c
#pragma once
#define XK_space        0x0020
#define XK_BackSpace    0xff08
#define XK_Tab          0xff09
#define XK_Return       0xff0d
#define XK_Escape       0xff1b
#define XK_Delete       0xffff
#define XK_Home         0xff50
#define XK_Left         0xff51
#define XK_Up           0xff52
#define XK_Right        0xff53
#define XK_Down         0xff54
#define XK_Page_Up      0xff55
#define XK_Page_Down    0xff56
#define XK_End          0xff57
#define XK_Caps_Lock    0xffe5
#define XK_Shift_L      0xffe1
#define XK_Shift_R      0xffe2
#define XK_Control_L    0xffe3
#define XK_Control_R    0xffe4
#define ShiftMask       (1<<0)
#define LockMask        (1<<1)
#define ControlMask     (1<<2)
#define Mod1Mask        (1<<3)
#define Mod2Mask        (1<<4)
#define Mod3Mask        (1<<5)
#define Mod4Mask        (1<<6)
#define Mod5Mask        (1<<7)
```

`gcin-core/compat/gdk/gdkx.h` — empty file (included by os-dep.h).

`gcin-core/compat/IMdkit.h` and `gcin-core/compat/Xi18n.h` — empty files
(included by gtab.cpp).

### 1b. Modification to gcin/util.cpp

Add `#ifndef GCIN_CORE_BUILD` guard around the GTK dialog block in `p_err()`.
The function already calls `p_err_no_alert()` for stderr output; in core build
mode, skip the dialog and return after that.

```diff
 void p_err(const char *fmt, ...) {
     ...
     p_err_no_alert(...);   // stderr output — keep
+#ifndef GCIN_CORE_BUILD
     GtkWidget *dialog = gtk_message_dialog_new(...);
     gtk_dialog_run(GTK_DIALOG(dialog));
     gtk_widget_destroy(dialog);
+#endif
     exit(1);
 }
```

Apply the same guard to the second `p_err` variant at line ~371 if present.

### 1c. gcin_stubs.cpp

`gcin-core/gcin_stubs.cpp` provides:
1. Definitions for all `extern` globals gcin source files reference
2. Stub bodies for all UI functions listed in [Key Findings](#ui-functions-to-stub-in-gcin_stubscpp)
3. The `send_text()` / `send_utf8_ch()` / `send_ascii()` intercepts with callback

```cpp
#include "gcin-core.h"
#include "../gcin/gcin.h"
#include "../gcin/pho.h"
#include "../gcin/tsin.h"
#include "../gcin/gst.h"

/* ── Globals expected by gcin source ─────────────────────── */
Display    *dpy       = NULL;
Window      xwin0     = 0;
Window      root      = 0;
GtkWidget  *gwin0     = NULL;
GdkWindow  *gdkwin0   = NULL;
int         dpy_xl    = 1920;
int         dpy_yl    = 1080;
int         win_xl    = 0, win_yl = 0;
int         win_x     = 0, win_y  = 0;
char        TableDir[512] = {0};

/* current_CS: gcin tracks the active X11 client via this pointer.
   The IBus engine is a single-client model; use a static instance. */
static CLIENT_STATE _cs = {0};
CLIENT_STATE *current_CS = &_cs;

/* ── Output callback ──────────────────────────────────────── */
static GcinCommitCb g_commit_cb   = NULL;
static void        *g_commit_data = NULL;

void gcin_core_set_commit_cb(GcinCommitCb cb, void *userdata) {
    g_commit_cb   = cb;
    g_commit_data = userdata;
}

void send_text(char *text) {
    if (g_commit_cb) g_commit_cb(text, g_commit_data);
}

void send_utf8_ch(char *ch) {
    /* ch is a CH_SZ (4-byte) UTF-8 buffer; may not be NUL-terminated */
    char buf[CH_SZ + 1];
    memcpy(buf, ch, CH_SZ);
    buf[CH_SZ] = '\0';
    if (g_commit_cb) g_commit_cb(buf, g_commit_data);
}

void send_ascii(char key) {
    char buf[2] = { key, '\0' };
    if (g_commit_cb) g_commit_cb(buf, g_commit_data);
}

/* ── UI stubs — void ──────────────────────────────────────── */
void show_win_gtab(void)            {}
void hide_win_gtab(void)            {}
void show_win_pho(void)             {}
void hide_win_pho(void)             {}
void hide_win_kbm(void)             {}
void hide_win0(void)                {}
void hide_row2_if_necessary(void)   {}
void minimize_win_gtab(void)        {}
void minimize_win_pho(void)         {}
void disp_gtab(char *s)             { (void)s; }
void disp_gbuf(void)                {}
void disp_gtab_sel(char *s)         { (void)s; }
void disp_gtab_pre_sel(char *s)     { (void)s; }
void disp_selection0(gboolean a, gboolean b) { (void)a; (void)b; }
void disp_pho(int i, char *s)       { (void)i; (void)s; }
void disp_pho_sel(char *s)          { (void)s; }
void disp_pho_sub(GtkWidget *l, int i, char *s) { (void)l; (void)i; (void)s; }
void disp_label_edit(char *s)       { (void)s; }
void disp_char(int i, char *s)      { (void)i; (void)s; }
void ClrIn(void)                    {}
void ClrSelArea(void)               {}
void ClrPhoSelArea(void)            {}
void clear_after_put(void)          {}
void clear_gtab_input_error_color(void) {}
void set_gtab_input_error_color(void)   {}
void set_key_codes_label(char *s, int b) { (void)s; (void)b; }
void set_page_label(char *s)        { (void)s; }
void set_label_font_size(GtkWidget *l, int sz) { (void)l; (void)sz; }
void set_label_space(GtkWidget *l)  { (void)l; }
void set_no_focus(GtkWidget *w)     { (void)w; }
void clr_in_area_pho(void)          {}
void clr_tsin_cursor(int i)         { (void)i; }
void bell(void)                     {}
void disp_tray_icon(void)           {}
void save_CS_current_to_temp(void)  {}
void show_tsin_stat(void)           {}
void recreate_win1_if_nessary(void) {}
void start_gtab_pho_query(char *s)  { (void)s; }
void close_gtab_pho_win(void)       {}
void set_gtab_target_displayed(void){}
void pho_play(phokey_t k)           { (void)k; }
void gtab_scan_pre_select(gboolean b) { (void)b; }
void hide_gtab_pre_sel(void)        {}
void change_win_fg_bg(GtkWidget *w, GtkWidget *l) { (void)w; (void)l; }
void change_win_bg(GtkWidget *w)    { (void)w; }
void send_gcin_message(Display *d, char *s) { (void)d; (void)s; }
void exec_gcin_setup(void)          {}
void get_win_size(GtkWidget *w, int *wd, int *ht) { (void)w; if(wd)*wd=0; if(ht)*ht=0; }
void win32_init_win(GtkWidget *w)   { (void)w; }

/* ── UI stubs — boolean ───────────────────────────────────── */
gboolean full_char_proc(KeySym k)          { (void)k; return FALSE; }
gboolean shift_char_proc(KeySym k, int s)  { (void)k; (void)s; return FALSE; }
gboolean pre_punctuation(KeySym k)         { (void)k; return FALSE; }
gboolean pre_punctuation_hsu(KeySym k)     { (void)k; return FALSE; }
gboolean is_gtab_query_mode(void)          { return FALSE; }
gboolean use_tsin_sel_win(void)            { return FALSE; }
gboolean same_query_show_pho_win(void)     { return FALSE; }
gboolean gcin_edit_display_ap_only(void)   { return FALSE; }
```

### 1d. gcin-core.h — public API

```c
#pragma once
#ifdef __cplusplus
extern "C" {
#endif

/* Callback fired when gcin commits a character or string */
typedef void (*GcinCommitCb)(const char *utf8, void *userdata);

/* Register the commit callback before calling init or feedkey */
void gcin_core_set_commit_cb(GcinCommitCb cb, void *userdata);

/* Initialize gcin core. table_dir: path to compiled data tables
   (the directory containing cj.gtab, pho.tab, tsin, etc.)
   Returns 0 on success, -1 on failure. */
int gcin_core_init(const char *table_dir);

/* Feed a keypress to the Cangjie engine.
   keyval: IBus/X11 key symbol. modifiers: IBus/X11 modifier bitmask.
   Returns 1 if key was consumed, 0 to pass through to application. */
int gcin_core_feedkey_cangjie(unsigned long keyval, int modifiers);
int gcin_core_feedkey_cangjie_release(unsigned long keyval, int modifiers);

/* Feed a keypress to the Zhuyin engine. Same conventions. */
int gcin_core_feedkey_zhuyin(unsigned long keyval, int modifiers);

/* Reset engine state (e.g. on focus loss) */
void gcin_core_reset(void);

#ifdef __cplusplus
}
#endif
```

### 1e. Makefile for libgcin-core.a

```makefile
GCIN     := ../gcin
COMPAT   := compat

# compat/ must come before system includes to shadow gtk/gtk.h, X11/Xlib.h, etc.
CXXFLAGS := -std=c++11 -g -O2 \
            -DGCIN_CORE_BUILD -DHAVE_CONFIG_H \
            -I$(COMPAT) -I$(GCIN) -I$(GCIN)/IMdkit

GCIN_SRCS := \
    $(GCIN)/gtab.cpp         \
    $(GCIN)/gtab-init.cpp    \
    $(GCIN)/gtab-list.cpp    \
    $(GCIN)/gtab-buf.cpp     \
    $(GCIN)/gtab-util.cpp    \
    $(GCIN)/gtab-tsin-fname.cpp \
    $(GCIN)/pho.cpp          \
    $(GCIN)/pho-lookup.cpp   \
    $(GCIN)/pho-util.cpp     \
    $(GCIN)/pho-kbm-name.cpp \
    $(GCIN)/tsin.cpp         \
    $(GCIN)/tsin-util.cpp    \
    $(GCIN)/tsin-char.cpp    \
    $(GCIN)/tsin-scan.cpp    \
    $(GCIN)/tsin-parse.cpp   \
    $(GCIN)/util.cpp         \
    $(GCIN)/gcin-conf.cpp    \
    $(GCIN)/gcin-common.cpp  \
    $(GCIN)/fullchar.cpp     \
    $(GCIN)/cache.cpp        \
    $(GCIN)/lang.cpp

CORE_SRCS := gcin_stubs.cpp

OBJS := $(patsubst %.cpp,%.o,$(notdir $(GCIN_SRCS))) \
        $(patsubst %.cpp,%.o,$(CORE_SRCS))

.PHONY: all clean

all: libgcin-core.a

libgcin-core.a: $(OBJS)
	$(AR) rcs $@ $^

# Rule for gcin source files (vpath handles the directory)
vpath %.cpp $(GCIN) .

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f *.o libgcin-core.a
```

### 1f. Build and iterate

```bash
cd sources/gcin-everywhere/gcin-core
make 2>&1 | head -40
```

Expect linker errors on the first pass — each undefined symbol gets a stub added
to `gcin_stubs.cpp`. Repeat until `libgcin-core.a` builds with zero errors.

---

## Phase 2: IBus Engine Skeleton

**Goal:** A minimal IBus engine binary that registers with ibus-daemon, links
`libgcin-core.a`, and does nothing yet.

### Component XML: ibus-engine/component/gcin.xml

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
      <longname>gcin Zhuyin (注音)</longname>
      <description>Zhuyin/Bopomofo Traditional Chinese input via gcin engine</description>
      <rank>99</rank>
      <symbol>注</symbol>
      <layout>default</layout>
    </engine>
  </engines>
</component>
```

### Skeleton gcin_engine.c

IBus GObject subclass — passes all keys through for now.

```c
#include <ibus.h>
#include "../gcin-core/gcin-core.h"

typedef struct _GcinEngine      GcinEngine;
typedef struct _GcinEngineClass GcinEngineClass;

struct _GcinEngine {
    IBusEngine       parent;
    IBusLookupTable *table;
    int              mode;         /* 0=Cangjie, 1=Zhuyin */
    gboolean         chinese_mode;
};
struct _GcinEngineClass { IBusEngineClass parent; };

G_DEFINE_TYPE(GcinEngine, gcin_engine, IBUS_TYPE_ENGINE)

static gboolean gcin_engine_process_key_event(IBusEngine *e,
        guint keyval, guint keycode, guint modifiers) {
    return FALSE; /* Phase 3/4 */
}
static void gcin_engine_enable(IBusEngine *e)    {}
static void gcin_engine_disable(IBusEngine *e)   {}
static void gcin_engine_reset(IBusEngine *e)     {}
static void gcin_engine_focus_out(IBusEngine *e) {}

static void gcin_engine_class_init(GcinEngineClass *klass) {
    IBusEngineClass *ec = IBUS_ENGINE_CLASS(klass);
    ec->process_key_event = gcin_engine_process_key_event;
    ec->enable    = gcin_engine_enable;
    ec->disable   = gcin_engine_disable;
    ec->reset     = gcin_engine_reset;
    ec->focus_out = gcin_engine_focus_out;
}
static void gcin_engine_init(GcinEngine *e) {
    e->table        = ibus_lookup_table_new(10, 0, TRUE, TRUE);
    e->chinese_mode = TRUE;
    g_object_ref_sink(e->table);
}

int main(int argc, char **argv) {
    ibus_init();
    IBusBus *bus = ibus_bus_new();
    g_assert(ibus_bus_is_connected(bus));
    IBusFactory *factory = ibus_factory_new(ibus_bus_get_connection(bus));
    ibus_factory_add_engine(factory, "gcin-cangjie", GCIN_TYPE_ENGINE); /* gcin_engine */
    ibus_factory_add_engine(factory, "gcin-zhuyin",  GCIN_TYPE_ENGINE);
    ibus_bus_request_name(bus, "org.freedesktop.IBus.Gcin", 0);
    gcin_core_init("/usr/share/gcin");
    ibus_main();
    return 0;
}
```

### Verify skeleton registers

```bash
sudo cp component/gcin.xml /usr/share/ibus/component/
./ibus-engine-gcin &
ibus list-engine | grep gcin
# expect: gcin-cangjie and gcin-zhuyin listed
```

---

## Phase 3: Cangjie Integration

**Goal:** `process_key_event` routes to `feedkey_gtab()`, commits characters,
updates preedit and candidate list.

### Key routing

```c
static gboolean gcin_engine_process_key_event(IBusEngine *iengine,
        guint keyval, guint keycode, guint modifiers) {
    if (modifiers & IBUS_RELEASE_MASK) return FALSE;
    GcinEngine *e = (GcinEngine *)iengine;
    if (!e->chinese_mode) return FALSE;

    int consumed = gcin_core_feedkey_cangjie(keyval, modifiers);

    /* Commit — gcin called send_text() → our callback stored the text */
    /* (implementation detail: adapt callback to call ibus_engine_commit_text) */

    /* Preedit — read from gcin's ggg buffer via get_DispInArea_str() */

    /* Candidates — disp_gtab_sel() stub captures candidate string */

    return consumed;
}
```

The commit callback (registered via `gcin_core_set_commit_cb`) calls
`ibus_engine_commit_text()` directly on the IBus engine.

For preedit: expose `gcin_core_get_preedit(char *out, int outlen)` in gcin-core.h,
implemented by calling gcin's `get_DispInArea_str()` (gtab.cpp:376).

For candidates: the `disp_gtab_sel(char *s)` stub captures the candidate string.
Expose `gcin_core_get_candidates(char *out, int outlen)` in gcin-core.h.
Parse `s` into individual characters (each UTF-8 character is one candidate).

### Test

Type in GNOME Text Editor with gcin-cangjie selected:
- `d` → preedit shows "大"
- `i` → preedit shows "大人" candidates
- `1` or space → commits 大人

---

## Phase 4: Zhuyin Integration

**Goal:** Same flow using `feedkey_pho()` for phonetic input.

`gcin_core_feedkey_zhuyin(keyval, modifiers)` calls `feedkey_pho(keyval, modifiers)`.

Preedit for Zhuyin comes from `poo.typ_pho[]` (the phonetic buffer in `PHO_ST`).
Expose a `gcin_core_get_pho_preedit()` helper that reads `poo` and converts
the phonetic codes to display characters using `phokey_to_str()` (pho.cpp).

Candidates: `disp_pho_sel(char *s)` stub captures them — same parse logic.

Keyboard layout: starts with Standard (大千). The layout is loaded from
`pho.tab2.src` which encodes the Standard layout by default.

### Test

Type ㄓ (v) + ㄨ (u) + ˋ (4) → candidates include 住, 助, 注, etc.
Select with number key → commits character.

---

## Phase 5: IBus Registration & Install

### Install paths

```
/usr/lib/ibus-gcin/ibus-engine-gcin
/usr/share/ibus/component/gcin.xml
/usr/share/gcin/              (cj.gtab, pho.tab, tsin, ...)
```

### Compile data tables

```bash
# From gcin build directory (after ./configure && make):
# cj.gtab — Cangjie table
./cintotab data/cj.cin data/cj.gtab

# pho.tab — Zhuyin table (Standard layout)
./phoconv data/pho.tab2.src data/pho.tab

# tsin — word frequency database
./tsa2d32 data/tsin.src data/tsin
```

### Activate and test end-to-end

```bash
sudo make install
ibus restart
# GNOME Settings → Keyboard → Input Sources → + → Chinese (Traditional)
# → gcin Cangjie  (or gcin Zhuyin)
# Open gedit, switch to gcin Cangjie, type: d i → select 大人
```

---

## gcin Source File Reference

### Files compiled into libgcin-core.a

| File | Verdict | Notes |
|------|---------|-------|
| `gtab.cpp` | MODIFY | contains `feedkey_gtab()`; UI calls handled by compat macros + stubs |
| `gtab-init.cpp` | MODIFY | compat macros handle GTK type references |
| `gtab-list.cpp` | MODIFY | `p_err()` redirect; compat handles rest |
| `gtab-buf.cpp` | MODIFY | contains `feedkey_gtab_release()` and `output_gbuf()`→`send_text()`; UI calls stubbed |
| `gtab-util.cpp` | INCLUDE | pure: `CONVT2()`, `gtab_key2name()` |
| `gtab-tsin-fname.cpp` | INCLUDE | file path utilities |
| `pho.cpp` | MODIFY | contains `feedkey_pho()`; `hide_win_pho`, `full_char_proc` stubbed |
| `pho-lookup.cpp` | INCLUDE | pure: phonetic lookup |
| `pho-util.cpp` | INCLUDE | file I/O: loads pho.tab |
| `pho-kbm-name.cpp` | INCLUDE | keyboard layout name table |
| `tsin.cpp` | MODIFY | UI calls (`hide_win0`, `show_tsin_stat`, etc.) stubbed |
| `tsin-util.cpp` | INCLUDE | file I/O: loads tsin database |
| `tsin-char.cpp` | INCLUDE | character index |
| `tsin-scan.cpp` | INCLUDE | pure: phrase matching |
| `tsin-parse.cpp` | INCLUDE | pure: recursive parse |
| `util.cpp` | MODIFY | `p_err()` needs `#ifdef GCIN_CORE_BUILD` guard (1 change) |
| `gcin-conf.cpp` | INCLUDE | file path + config loading; X11 include unused |
| `gcin-common.cpp` | MODIFY | `bell()`, `disp_pho_sub()`, etc. handled by compat macros |
| `fullchar.cpp` | INCLUDE | full-width character table |
| `cache.cpp` | INCLUDE | pure: parse result cache |
| `lang.cpp` | INCLUDE | pure: language detection |

### Files excluded (not compiled)

| File | Reason |
|------|--------|
| `gcin.cpp` | main() — application entry point |
| `gcin-send.cpp` | XIM text dispatch — replaced by `gcin_stubs.cpp` |
| `IC.cpp` | X11 input context — not used |
| `win-*.cpp`, `win0.cpp`, `win1.cpp` | X11/GTK windows |
| `gcin-icon.cpp`, `tray.cpp`, `eggtrayicon.cpp` | system tray |
| `im-srv.cpp`, `im-addr.cpp`, `im-dispatch.cpp` | XIM server |
| `gcin-setup*.cpp`, `gcin-module*.cpp` | settings UI, plugin loader |
| `phoa2d.cpp`, `phod2a.cpp` | standalone conversion tools (have own `main()`) |
| `IMdkit/` (entire dir) | X11 XIM server implementation |
| `eve.cpp` | X11 event loop dispatcher |

### Key data files (built by gcin's tools, installed to /usr/share/gcin/)

| File | Source | Input method |
|------|--------|-------------|
| `cj.gtab` | `data/cj.cin` → `cintotab` | Cangjie (倉頡) |
| `pho.tab` | `data/pho.tab2.src` → `phoconv` | Zhuyin Standard (大千) |
| `tsin` | `data/tsin.src` → `tsa2d32` | Word frequency database |

---

**Last Updated:** 2026-05-04
