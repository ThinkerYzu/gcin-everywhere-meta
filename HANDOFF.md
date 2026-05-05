# Handoff: gcin-everywhere

**Project:** gcin-everywhere
**Started:** 2026-05-04

---

## Navigation

**Project Docs:** [README](README.md) | [SPEC](SPEC.md) | [DESIGN](DESIGN.md) | [IMPLEMENTATION-GUIDE](IMPLEMENTATION-GUIDE.md) | [HANDOFF](HANDOFF.md) *(you are here)*

**Quick Jump:** [Current Status](#current-status) | [Next Actions](#next-actions) | [Session Logs](#session-logs)

---

## Current Status

**Phase:** Ready to code — planning fully locked down
**Progress:** Implementation guide deeply audited; all GCIN_CORE_BUILD decisions final; 4 gcin files to modify; stub list corrected
**Next Milestone:** Write code — modify 4 gcin files, create gcin-core/, build libgcin-core.a
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

- Fully audited implementation plan for `libgcin-core.a`
- GCIN_CORE_BUILD type list locked: 5 types (`gboolean`, `gint64`, `KeySym`, `GtkWidget`, `unich_t`)
- 4 gcin files to modify: `gcin.h`, `IC.h`, `util.cpp`, `gcin-conf.cpp`
- Corrected stub list (13 duplicate symbols removed)

### Key Design Decisions

- **No compat/ directory** — `gcin.h` modified with `GCIN_CORE_BUILD` block instead
- **`gcin-common.cpp` excluded** — actual GTK/X11 calls; `case_inverse`/`current_time` re-implemented in stubs
- **`typedef void GtkWidget` kept** — eliminating it costs 4 more file modifications for zero practical benefit
- **`GTK_WIDGET_VISIBLE(w)` defined as `(0)`** — called in `feedkey_gtab:985` / `feedkey_pho:844`; always-NULL pointers in core build

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

1. **[Session 2: Implementation Guide Deep Audit](logs/2026-05-05-session-02-impl-guide-deep-audit.md)** (2026-05-05) — Per-file GTK/X11 audit: only 2 files call GTK (util.cpp, gcin-conf.cpp); eliminated compat/ directory; reduced GCIN_CORE_BUILD to 5 types; found 13 duplicate symbol conflicts in stub list; decided to keep `typedef void GtkWidget`; deleted INIT-GUIDE.md.
2. **Session 1: Project kickoff + full planning** (2026-05-04) — Defined goals; approved SPEC.md; drafted DESIGN.md; audited gcin source tree (entry points, IBus/X11 keyval compatibility); drafted IMPLEMENTATION-GUIDE.md with Phase 1 plan for `libgcin-core.a`; initialized both git repos.

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

**Last Updated:** 2026-05-05
