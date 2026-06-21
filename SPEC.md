# Spec: gcin-everywhere

**Project:** gcin-everywhere
**Created:** 2026-05-04
**Last Updated:** 2026-06-21 (added FR8: unified `gcin-everywhere` switcher engine)
**Status:** Approved

---

## Navigation

**Project Docs:** [README](README.md) | [SPEC](SPEC.md) *(you are here)* | [DESIGN](DESIGN.md) | [IMPLEMENTATION-GUIDE](IMPLEMENTATION-GUIDE.md) | [HANDOFF](HANDOFF.md)

**This Document:**
- [Problem Statement](#problem-statement)
- [Goals](#goals)
- [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Constraints](#constraints)
- [Success Criteria](#success-criteria)
- [Open Questions](#open-questions)

---

## Problem Statement

gcin is a well-loved Traditional Chinese input method framework widely used in Taiwan. It supports input methods such as Cangjie (倉頡), Zhuyin (注音/Bopomofo), Array (行列), Dayi (大易), Bu-xie-mi (嘸蝦米), and others. It was built for X11 and is effectively unmaintained for modern Linux desktops.

With GNOME fully transitioning to Wayland, gcin no longer works for users who relied on it daily. There is no suitable replacement that faithfully reproduces gcin's input behavior and key bindings. Users who grew up with gcin find current alternatives unfamiliar and uncomfortable.

The goal of this project is to bring gcin's input methods back to life on modern platforms — starting with GNOME/Wayland, and eventually extending to Windows and macOS — by porting gcin's existing engine and data tables into a modern IME integration layer.

### Background

gcin was created by Edward G.J. Lee and uses its own X11-based UI and XIM protocol for input. Its core strengths are:
- Mature, well-tested input method tables for Traditional Chinese
- Familiar key bindings for long-time users
- Support for a wide range of input methods under one framework

Modern GNOME on Wayland uses IBus as its default input method framework. An IBus engine is the standard integration path: the engine implements IBus's D-Bus interface and GNOME handles candidate display, focus, and text commitment.

---

## Goals

1. **Wayland/GNOME support (Phase 1):** Wrap gcin's core engine as an IBus engine so it works on GNOME/Wayland desktops.
2. **Cangjie and Zhuyin first:** Support Cangjie (倉頡) and Zhuyin (注音) as the top-priority input methods in Phase 1.
3. **Reuse gcin's data and logic:** Port gcin's existing source code, data tables, and input algorithms directly — do not rewrite the input method logic.
4. **Cross-platform foundation (future phases):** Establish a clean separation between gcin's core and the platform integration layer so future ports to Windows (TSF) and macOS (IMKit) are straightforward.

## Non-Goals

1. **Not a clean rewrite** — existing gcin source, data tables, and character lookup algorithms are reused directly.
2. **No Windows or macOS support in Phase 1** — cross-platform ports are future work.
3. **No Fcitx5 engine in Phase 1** — IBus is the only integration target for now.
4. **No redesign of input algorithms or table formats** — gcin's existing formats are used as-is.
5. **No X11-specific support** — the project targets Wayland; XWayland compatibility is incidental.

---

## Requirements

### Functional Requirements

1. **IBus engine registration** — The engine registers with IBus and appears as a selectable input source in GNOME Settings → Keyboard → Input Sources.
2. **Cangjie input** — Full Cangjie (倉頡) input support using gcin's existing lookup tables and algorithms.
3. **Zhuyin input** — Full Zhuyin (注音/Bopomofo) input support using gcin's existing tables and tone key handling.
4. **Candidate window** — Display character candidates during composition; the user can select from them.
5. **Preedit / composition display** — Show in-progress input (preedit string) in the input field while composing.
6. **Character commitment** — Commit the selected Traditional Chinese character(s) to the application on confirmation.
7. **Input method switching** — User can switch between Cangjie and Zhuyin (and other supported methods) via IBus/GNOME.
8. **Unified switcher engine (`gcin-everywhere`)** — A single IBus engine that lets the user switch between all supported input methods *in place* via `Ctrl+Alt+<digit>`, mirroring gcin's native hotkeys. The digit→method mapping follows gcin's `gtab.list` `key_ch` column where defined, extended for methods gcin leaves unnumbered:

   | Hotkey | Method |
   |--------|--------|
   | `Ctrl+Alt+1` | 倉頡 Cangjie |
   | `Ctrl+Alt+2` | 倉五 CJ5 |
   | `Ctrl+Alt+3` | 注音 Zhuyin |
   | `Ctrl+Alt+4` | 速成 Quick (extension — gcin uses `-`) |
   | `Ctrl+Alt+5` | 標點簡易 SimplexPunc (extension — gcin uses `-`) |
   | `Ctrl+Alt+8` | 行列 Array |

   - The switch persists for the session until changed again; the engine starts in Cangjie.
   - `Ctrl+Alt+<digit>` switching is active **only** in the `gcin-everywhere` engine. The six single-method engines (`gcin-cangjie`, …) remain fixed to their method so the IBus panel label stays accurate.
   - The IBus panel reflects the active method via an engine property (symbol updates 全→倉/注/…).
9. **English toggle (`Ctrl+Space`)** — within `gcin-everywhere`, `Ctrl+Space` toggles between Chinese input and English passthrough in place — the gcin-native `gcin_im_toggle` behavior. The previously selected method is preserved, so toggling back resumes it. The panel symbol shows 英 while in English. This is an in-engine toggle (not a desktop input-source switch), so it requires that no desktop shortcut grab plain `Ctrl+Space` (see DESIGN §8).

### Non-Functional Requirements

1. **Performance** — Candidate lookup must feel instantaneous; target <50ms from keypress to candidate display.
2. **Compatibility** — Works on GNOME 45+ with Wayland. Input works correctly in GTK4 and Qt6 applications via IBus.
3. **Reliability** — Engine must not crash on invalid or unexpected input sequences; handle edge cases gracefully.

---

## Constraints

1. Must reuse gcin's existing data tables (character lookup tables, input method definitions) without reformatting them.
2. Must reuse gcin's existing input algorithms directly (ported C/C++ code, not reimplemented).
3. Implementation language: **C/C++**.
4. Platform integration: **IBus** for Phase 1 (GNOME/Wayland).
5. gcin is licensed **GPL** — the project inherits this license.

---

## Success Criteria

1. **Cangjie works end-to-end** — A user can type Cangjie key sequences and commit Traditional Chinese characters in a GNOME Wayland app (e.g., gedit, GNOME Text Editor). Verified manually with test phrases.
2. **Zhuyin works end-to-end** — Same verification for Zhuyin input with tone key selection.
3. **GTK4 and Qt6 compatibility** — Input works correctly in at least one GTK4 app and one Qt6 app.
4. **IBus registration** — Engine appears in GNOME Settings → Keyboard → Input Sources and can be selected without manual D-Bus manipulation.
5. **No crashes** — Engine runs stably for a 30-minute typing session without crashing or hanging.
6. **Unified switching works** — With the `gcin-everywhere` engine active, `Ctrl+Alt+1/2/3/4/5/8` switches the active method in place; subsequent keystrokes use the newly selected method and the panel symbol updates accordingly.

---

## Open Questions

All open questions resolved.

| Question | Decision |
|----------|----------|
| gcin source base | https://github.com/pkg-ime/gcin |
| Candidate window | IBus built-in candidate window |
| Phase 1 input methods | Cangjie and Zhuyin only |
| Build system | Keep gcin's existing Makefile |

---

**Last Updated:** 2026-06-21 (added FR8: unified `gcin-everywhere` switcher engine)
