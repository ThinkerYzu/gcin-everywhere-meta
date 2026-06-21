# gcin-everywhere

**Status:** Phase 10 complete — 7 IBus engines incl. unified gcin-everywhere (Ctrl+Alt+digit switcher); Cangjie, Zhuyin, Quick, Array, CJ5, SimplexPunc, full-width, phrase tables all working
**Created:** 2026-05-04
**Last Updated:** 2026-06-21
**Goal:** Port gcin's Traditional Chinese input engine to modern platforms, starting with GNOME/Wayland via IBus.

---

## Project Documentation

### Core Documentation

- **README.md** (This document) - Project overview and getting started
- **[SPEC.md](SPEC.md)** — Problem statement, requirements, constraints, and success criteria
- **[DESIGN.md](DESIGN.md)** — Architecture, design decisions, and technical approach
- **[IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md)** — Detailed implementation guide with code examples
- **[HANDOFF.md](HANDOFF.md)** — Current status, next actions, session logs (the handoff package)

### Testing Documentation

- **[TESTING-GUIDE.md](TESTING-GUIDE.md)** — Testing procedures, expected output, troubleshooting

**Quick Links:**
- [Overview](#overview) | [Design & Architecture](DESIGN.md) | [Current Status](HANDOFF.md#current-status) | [Testing](TESTING-GUIDE.md)

---

## Overview

gcin is a Traditional Chinese input method framework that was widely used in Taiwan for input methods such as Cangjie (倉頡), Zhuyin (注音/Bopomofo), Array (行列), and others. Built for X11, it became effectively unmaintained as modern Linux desktops moved to Wayland. Users who grew up with gcin find no adequate replacement — current alternatives behave differently and break years of muscle memory.

gcin-everywhere ports gcin's engine and data tables to modern platforms. Rather than reimplementing the input logic, it reuses gcin's existing C source code and character lookup tables directly, wrapping them in platform-specific integration layers. Phase 1 targets GNOME/Wayland via IBus — the standard input method framework for GNOME.

The architecture is designed for portability: the gcin core is isolated from the platform layer, making future ports to Windows (TSF) and macOS (IMKit) straightforward additions.

## Recent Updates

See [HANDOFF.md](HANDOFF.md) for the full changelog, session history, and next actions.

---

## Core Concepts

### Adapter pattern: gcin core stays untouched

gcin's input logic (`gtab.cpp`, `pho.cpp`, and ~15 related files) is compiled into `libgcin-core.a` — a static library with no GTK or X11 runtime dependency. Two gcin source files are minimally modified: `gcin.h` gains a `GCIN_CORE_BUILD` block that defines all needed types as plain C types (no system headers), and `util.cpp` guards one GTK dialog call. `gcin_stubs.cpp` provides extern globals, UI function stubs, and intercepts `send_text()` to fire a callback instead of sending to X11 clients.

### Table-based vs. phonetic engines

gcin has two distinct input paths. **Cangjie** is table-based: keystrokes are packed into a bitmask and binary-searched in a compiled `.gtab` file. **Zhuyin** is phonetic: keys accumulate an initial/medial/final/tone syllable buffer and look up matching characters in a phonetic index. Both paths eventually call `send_text()` to output the selected character.

---

## Implementation Phases

### Phase 1: GNOME/Wayland via IBus (IN PROGRESS)
- ✅ Step 1: Stub layer — compile gcin core with X11/GTK globals stubbed out
- ✅ Step 2: IBus skeleton — GObject subclass, component XML, engine registration
- ✅ Step 3: Cangjie — gtab key routing, preedit, candidate display, commit
- ✅ Step 4: Zhuyin — phonetic key routing, syllable buffer, commit
- ✅ Step 5: Install, enable in GNOME Settings, end-to-end test
- ✅ Step 6: Full-width mode (Shift+Space)
- ✅ Step 7: Alt+Shift / Ctrl phrase tables

### Phase 2: Additional Input Methods (IN PROGRESS)
- ✅ Quick (速成) — `feedkey_gtab_method(g_quick_inmd, ...)`; simplex.gtab
- ✅ Array (行列) — `feedkey_gtab_method(g_array_inmd, ...)`; ar30.gtab
- Dayi (大易) — skipped (dayi3.cin absent from gcin snapshot)
- Bu-xie-mi (嘸蝦米) — future
- ✅ Unified switcher — `gcin-everywhere` engine: `Ctrl+Alt+digit` switches method in place (mirrors gcin's native hotkeys); panel property shows the live method

### Phase 3: Cross-Platform (FUTURE)
- Windows via Text Services Framework (TSF)
- macOS via Input Method Kit (IMKit)

---

## Development Repository

**Working Directory:** `sources/gcin-everywhere/` (relative to claudebugzilla root)
**Git Branch:** master
**gcin upstream:** `sources/gcin-everywhere/gcin/` (git submodule: github.com/pkg-ime/gcin)
**New engine code:** `sources/gcin-everywhere/ibus-engine/`

---

## Related Projects

- [gcin (Arch Linux Wiki)](https://wiki.archlinux.org/title/Gcin) — Original project documentation

---

## Documentation Maintenance

### Documentation as a Web

**Core Principle:** This project directory is maintained as a **web of interconnected documents**, not isolated files.

- Documents are connected through **hyperlinks** (both markdown and HTML)
- Every document includes **navigation sections** at the top
- Cross-references point to **specific sections** using anchor links (#section-name)

### Agent Responsibilities

The agent (Claude) must actively maintain both **content and connections** in this documentation web:

**Content updates:**
- **Progress tracking**: Update status and milestone achievements
- **Implementation details**: Document design decisions, code structure, and technical approaches
- **Technical findings**: Record measurements, results, and key learnings
- **Architecture evolution**: Update design documents as the design evolves
- **Log maintenance**: Keep HANDOFF.md current with development activities

**Link maintenance:**
- **Add cross-references**: When creating new content, link to related existing content
- **Update navigation**: Add new documents to navigation bars on all pages
- **Verify links**: Ensure links remain valid as documents evolve

### Handoff as Complete Package

**Philosophy:** HANDOFF.md should serve as a **complete handoff package** that enables anyone to pick up the task and push forward without asking questions.

**Handoff quality test:** "Could a new team member read this and implement the next phase without asking clarifying questions?"

---

**Last Updated:** 2026-06-21
