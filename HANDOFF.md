# Handoff: gcin-everywhere

**Project:** gcin-everywhere
**Started:** 2026-05-04

---

## Navigation

**Project Docs:** [README](README.md) | [SPEC](SPEC.md) | [DESIGN](DESIGN.md) | [IMPLEMENTATION-GUIDE](IMPLEMENTATION-GUIDE.md) | [HANDOFF](HANDOFF.md) *(you are here)*

**Quick Jump:** [Current Status](#current-status) | [Next Actions](#next-actions) | [Session Logs](#session-logs)

---

## Current Status

**Phase:** Ready to code — all planning docs complete and audited
**Progress:** SPEC approved; DESIGN complete; IMPLEMENTATION-GUIDE fully revised after source audit
**Next Milestone:** Phase 1 — build libgcin-core.a (gcin-core/ directory, compat headers, gcin_stubs.cpp, one gcin source modification)
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

1. **Phase 1 — libgcin-core.a (NEXT)** — Modify 4 gcin files: `gcin.h` (GCIN_CORE_BUILD block with 6 types + `#ifndef` guards on unused externs/decls), `IC.h` (guard PreeditAttributes/StatusAttributes), `util.cpp` (guard GTK dialog in p_err), `gcin-conf.cpp` (guard get_gcin_atom). Create `gcin-core/` with `gcin_stubs.cpp`, `gcin-core.h`, and `Makefile`. Build until zero errors.
2. **Phase 2 — IBus skeleton** — Create `ibus-engine/gcin_engine.c` (IBus GObject, passes all keys through), `component/gcin.xml`, and `ibus-engine/Makefile` (links libgcin-core.a). Verify `ibus list-engine | grep gcin` shows both engines.
3. **Phase 3 — Cangjie** — Wire `gcin_core_feedkey_cangjie()` → `feedkey_gtab()`. Expose preedit via `get_DispInArea_str()` and candidates via `disp_gtab_sel()` stub. Test: type `di` → commit 大人.
4. **Phase 4 — Zhuyin** — Wire `gcin_core_feedkey_zhuyin()` → `feedkey_pho()`. Expose preedit from `poo.typ_pho[]` via `phokey_to_str()`. Test: type `vu4` → commit 住.
5. **Phase 5 — Install** — Compile data tables, `make install`, enable in GNOME Settings, end-to-end test in gedit and a Qt6 app.

**Deferred:**
- Windows (TSF) and macOS (IMKit) ports — future phases after Phase 1 is working.
- Fcitx5 engine — not planned for Phase 1.

---

## Session Logs

1. **Session 1: Project kickoff + full planning + source audit** (2026-05-04) — Defined goals; approved SPEC.md; drafted DESIGN.md; audited gcin source tree (confirmed entry points `feedkey_gtab`/`feedkey_pho`, IBus/X11 keyval compatibility, compat-header strategy, one required source modification); fully revised IMPLEMENTATION-GUIDE.md with concrete Phase 1 plan for `libgcin-core.a`; initialized both git repos.

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
