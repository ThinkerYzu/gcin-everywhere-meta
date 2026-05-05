# Handoff: gcin-everywhere

**Project:** gcin-everywhere
**Started:** 2026-05-04

---

## Navigation

**Project Docs:** [README](README.md) | [SPEC](SPEC.md) | [DESIGN](DESIGN.md) | [IMPLEMENTATION-GUIDE](IMPLEMENTATION-GUIDE.md) | [HANDOFF](HANDOFF.md) *(you are here)*

**Quick Jump:** [Current Status](#current-status) | [Next Actions](#next-actions) | [Session Logs](#session-logs)

---

## Current Status

**Phase:** Ready to code — all planning docs complete
**Progress:** SPEC approved; DESIGN complete; IMPLEMENTATION-GUIDE drafted; source repo initialized
**Next Milestone:** Phase 1 stub layer — compile gcin core files into ibus-engine-gcin, zero linker errors
**Blockers:** None

> **Phase checklist:**
> - ✅ Spec drafted
> - ✅ Spec finalized (open questions resolved)
> - ✅ Design complete
> - ✅ Implementation guide ready
> - ⬜ Prototype working
> - ⬜ Tests passing
> - ⬜ End-to-end demo

### What We Have

*(Empty — no code yet. Project is in spec phase.)*

### Key Design Decisions

*(Empty — to be filled after DESIGN.md.)*

---

## Next Actions

1. **Phase 1 — Stub layer (NEXT)** — Create `ibus-engine/gcin_stubs.cpp` with X11 global stubs and `send_text()` intercept. Write `ibus-engine/Makefile`. Compile gcin core files (see IMPLEMENTATION-GUIDE.md §gcin Source File Reference). Iterate until zero linker errors.
2. **Phase 2 — IBus skeleton** — Write `gcin_engine.c` (IBus GObject subclass) and `component/gcin.xml`. Verify `ibus list-engine | grep gcin` shows both engines.
3. **Phase 3 — Cangjie** — Wire up `gcin_adapter_init()` + gtab key routing in `process_key_event`. Test: type `di` → commit 大人.
4. **Phase 4 — Zhuyin** — Wire up `pho_load()` + phonetic key routing. Test: type `ㄓㄨˋ` → commit 住.
5. **Phase 5 — Install** — `make install`, enable in GNOME Settings, end-to-end test in gedit and a Qt6 app.

**Deferred:**
- Windows (TSF) and macOS (IMKit) ports — future phases after Phase 1 is working.
- Fcitx5 engine — not planned for Phase 1.

---

## Session Logs

1. **Session 1: Project kickoff + full planning** (2026-05-04) — Defined goals; approved SPEC.md; drafted DESIGN.md (adapter pattern, IBus GObject, Cangjie/Zhuyin data flows); drafted IMPLEMENTATION-GUIDE.md (5-phase plan, stub strategy, file reference); initialized both git repos (`proj_docs/gcin-everywhere/` and `sources/gcin-everywhere/` with gcin submodule).

---

## Document Web

**Related Documents:**
- [SPEC.md](SPEC.md) - Requirements and constraints
- [DESIGN.md](DESIGN.md) - Architecture and design decisions
- [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) - Code-level details
- [README.md](README.md) - Project overview

**When adding new entries:**
- Create new session log in `logs/` directory
- Update [Session Logs](#session-logs) section with link (keep last 5; move older to archive)
- Update [Current Status](#current-status) with progress

---

**Source Repo:** `sources/gcin-everywhere/` — initialized with gcin submodule at `gcin/`, new engine code goes in `ibus-engine/`

**Last Updated:** 2026-05-04
