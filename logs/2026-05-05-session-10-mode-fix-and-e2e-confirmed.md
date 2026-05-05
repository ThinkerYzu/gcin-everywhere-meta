# Session 10: Mode Detection Fix — Phase 1 Complete

**Date:** 2026-05-05
**Phase:** Phase 1 complete
**Branch:** master

---

## Goals

- Fix Zhuyin mode: both Cangjie and Zhuyin were behaving as Cangjie
- Confirm end-to-end input works for both engines

## What Was Done

### Mode detection moved from init() to enable()

`gcin_engine_init()` was calling `ibus_engine_get_name()` to detect Cangjie vs Zhuyin,
but GObject properties are not yet set when `_init()` runs — the name came back NULL,
so both engines defaulted to Cangjie (mode 0).

Fix: moved mode detection to `gcin_engine_enable()`, which is called by IBus when the
user switches to the engine. At that point the engine name is available and correct.
Also added `gcin_core_reset()` in `enable()` to clear any stale state on engine switch.

```c
static void gcin_engine_enable(IBusEngine *e) {
    GcinEngine *ge = (GcinEngine *)e;
    const gchar *name = ibus_engine_get_name(e);
    ge->mode = (name && g_str_has_suffix(name, "zhuyin")) ? 1 : 0;
    gcin_core_reset();
}
```

## Status at End of Session

- **Cangjie:** typing works end-to-end in GNOME
- **Zhuyin:** typing works end-to-end in GNOME
- **Phase 1 complete** — both engines install, autostart, and accept input

## Next Steps

- Phase 2: additional input methods (Quick/速成, Array/行列)
- Phase 3: cross-platform ports (Windows TSF, macOS IMKit)

---

**Files Changed:**
- `ibus-engine/gcin_engine.c` — mode detection moved from `gcin_engine_init()` to `gcin_engine_enable()`
