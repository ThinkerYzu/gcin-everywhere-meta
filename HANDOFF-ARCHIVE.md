# Handoff Archive: gcin-everywhere

Older session logs moved here from [HANDOFF.md](HANDOFF.md) when the active list exceeded 5 entries.

---

## Archived Session Logs

1. **Session 1: Project kickoff + full planning** (2026-05-04) — Defined goals; approved SPEC.md; drafted DESIGN.md; audited gcin source tree (entry points, IBus/X11 keyval compatibility); drafted IMPLEMENTATION-GUIDE.md with Phase 1 plan for `libgcin-core.a`; initialized both git repos.
2. **[Session 2: Implementation Guide Deep Audit](logs/2026-05-05-session-02-impl-guide-deep-audit.md)** (2026-05-05) — Per-file GTK/X11 audit: only 2 files call GTK (util.cpp, gcin-conf.cpp); eliminated compat/ directory; reduced GCIN_CORE_BUILD to 5 types; found 13 duplicate symbol conflicts in stub list; decided to keep `typedef void GtkWidget`; deleted INIT-GUIDE.md.
3. **[Session 15: Phase 2 — CJ5 (倉頡五代)](logs/2026-05-05-session-15-phase2-cj5.md)** (2026-05-05) — Added CJ5 engine via `feedkey_gtab_method()`; 5 IBus engines; 23/23 tests pass.
