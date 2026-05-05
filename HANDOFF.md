# Handoff: gcin-everywhere

**Project:** gcin-everywhere
**Started:** 2026-05-04

---

## Navigation

**Project Docs:** [README](README.md) | [SPEC](SPEC.md) | [DESIGN](DESIGN.md) | [IMPLEMENTATION-GUIDE](IMPLEMENTATION-GUIDE.md) | [HANDOFF](HANDOFF.md) *(you are here)*

**Quick Jump:** [Current Status](#current-status) | [Next Actions](#next-actions) | [Session Logs](#session-logs)

---

## Current Status

**Phase:** Design phase — architecture defined, ready for implementation guide
**Progress:** SPEC.md approved (all open questions resolved); DESIGN.md complete
**Next Milestone:** Draft IMPLEMENTATION-GUIDE.md, then begin porting
**Blockers:** None

> **Phase checklist:**
> - ✅ Spec drafted
> - ✅ Spec finalized (open questions resolved)
> - ✅ Design complete
> - ⬜ Implementation guide ready
> - ⬜ Prototype working
> - ⬜ Tests passing
> - ⬜ End-to-end demo

### What We Have

*(Empty — no code yet. Project is in spec phase.)*

### Key Design Decisions

*(Empty — to be filled after DESIGN.md.)*

---

## Next Actions

1. **Draft IMPLEMENTATION-GUIDE.md (NEXT)** — Build environment prereqs, planned file structure for `ibus-engine/`, step-by-step porting plan (stub layer → gtab integration → pho integration → IBus wiring → registration).
2. **Clone gcin source** — `git clone https://github.com/pkg-ime/gcin` into working directory; audit which source files are needed for Cangjie and Zhuyin.
3. **Build environment setup** — Verify build dependencies: `libibus-1.0-dev`, `libglib2.0-dev`, gcin's existing build deps.
4. **Begin porting** — Follow IMPLEMENTATION-GUIDE.md phase steps.

**Deferred:**
- Windows (TSF) and macOS (IMKit) ports — future phases after Phase 1 is working.
- Fcitx5 engine — not planned for Phase 1.

---

## Session Logs

1. **Session 1: Project kickoff + design** (2026-05-04) — Defined project goals: port gcin engine + data tables as an IBus engine for GNOME/Wayland. Cangjie and Zhuyin Phase 1 priorities. Drafted and approved SPEC.md; drafted DESIGN.md with full architecture (adapter pattern, IBus GObject subclass, data flow for Cangjie and Zhuyin).

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
