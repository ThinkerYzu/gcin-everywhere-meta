# Handoff: gcin-everywhere

**Project:** gcin-everywhere
**Started:** 2026-05-04

---

## Navigation

**Project Docs:** [README](README.md) | [SPEC](SPEC.md) | [DESIGN](DESIGN.md) | [IMPLEMENTATION-GUIDE](IMPLEMENTATION-GUIDE.md) | [HANDOFF](HANDOFF.md) *(you are here)*

**Quick Jump:** [Current Status](#current-status) | [Next Actions](#next-actions) | [Session Logs](#session-logs)

---

## Current Status

**Phase:** Phase 2 complete — `ibus-engine-gcin` builds and links
**Progress:** IBus skeleton binary (520KB) builds; `gcin_engine.c`, `component/gcin.xml`, `ibus-engine/Makefile` all created
**Next Milestone:** Compile data tables + install + verify `ibus list-engine | grep gcin`
**Blockers:** None

> **Phase checklist:**
> - ✅ Spec drafted
> - ✅ Spec finalized (open questions resolved)
> - ✅ Design complete
> - ✅ Implementation guide ready
> - ✅ Phase 1 complete — libgcin-core.a (26 source files, links cleanly)
> - ✅ Phase 2 complete — ibus-engine-gcin skeleton builds
> - ⬜ IBus registration verified (ibus list-engine | grep gcin)
> - ⬜ Phase 3 — Cangjie key routing
> - ⬜ End-to-end demo

### What We Have

- `gcin-core/libgcin-core.a` — 26 source files compiled with `-DGCIN_CORE_BUILD -DUSE_TSIN=1`
- `ibus-engine/ibus-engine-gcin` (520KB ELF) — links against libgcin-core.a + libibus-1.0
- `ibus-engine/component/gcin.xml` — IBus component descriptor (gcin-cangjie + gcin-zhuyin)
- `process_key_event` passes all keys through (returns FALSE); engine scaffold is wired up
- **Tests:** `gcin-core/test_feedkey.c` — 6 unit tests (Cangjie + Zhuyin feedkey); `make test` skips cleanly until data tables compiled
- **Tests:** `ibus-engine/test-registration.sh` — Phase 2 registration check; 5/7 checks pass now, 2 need tables/sudo

### Key Design Decisions

- **No compat/ directory** — `gcin.h` modified with `GCIN_CORE_BUILD` block instead
- **`gcin-common.cpp` excluded** — actual GTK/X11 calls; `case_inverse`/`current_time` re-implemented in stubs
- **`typedef void GtkWidget` kept** — eliminating it costs 4 more file modifications for zero practical benefit
- **`GTK_WIDGET_VISIBLE(w)` defined as `(0)`** — called in `feedkey_gtab:985` / `feedkey_pho:844`; always-NULL pointers in core build
- **`pho-sym.cpp` and `unix-exec.cpp` added** — not in original guide list but required (`pho_chars[]`, `unix_exec`)
- **Compile as C not C++** — gcin source uses C `goto`-over-init patterns; `-x c` flag needed
- **`-DUSE_TSIN=1` required** — `add_to_tsin_buf` is inside `#if USE_TSIN`; not in config.h without autoconf build
- **`gcin-settings.cpp` added to library** — defines nearly all `gtab_*`/`tsin_*`/`pho_*` globals; no GTK/X11 calls
- **`locale.cpp` added to library** — all utf8 utilities (`utf8_sz`, `u8cpy`, etc.); no GTK/X11 calls
- **libibus-1.0-dev workaround** — extracted with `apt-get download` + `dpkg-deb -x`; pass runtime `.so.5` directly to linker since extracted `.so` symlink is broken

---

## Next Actions

1. **Compile data tables + install (NEXT)** — From a gcin build dir, run `cintotab data/cj.cin cj.gtab` and `phoconv data/pho.tab2.src pho.tab`, install to `/usr/share/gcin/`. Then run `./test-registration.sh` (handles XML install + ibus restart + verification). Run `GCIN_TABLE_DIR=/usr/share/gcin make test` to confirm unit tests pass.
2. **Phase 3 — Cangjie** — Wire `gcin_core_feedkey_cangjie()` → `feedkey_gtab()`. Expose preedit via `get_DispInArea_str()` and candidates via `disp_gtab_sel()` stub. Test: type `di` → commit 大人.
3. **Phase 4 — Zhuyin** — Wire `gcin_core_feedkey_zhuyin()` → `feedkey_pho()`. Expose preedit from `poo.typ_pho[]` via `phokey_to_str()`. Test: type `vu4` → commit 住.
4. **Phase 5 — Install** — Compile data tables, `make install`, enable in GNOME Settings, end-to-end test in gedit and a Qt6 app.

**Deferred:**
- Windows (TSF) and macOS (IMKit) ports — future phases after Phase 1 is working.
- Fcitx5 engine — not planned for Phase 1.

---

## Session Logs

1. **[Session 4: Phase 2 — IBus Engine Skeleton Builds](logs/2026-05-05-session-04-ibus-skeleton.md)** (2026-05-05) — Created gcin_engine.c, gcin.xml, ibus-engine/Makefile; fixed 8 more duplicate stubs; added 5 files to libgcin-core.a; added g_strdup_printf/_()/GError/F-keys to GCIN_CORE_BUILD; added -DUSE_TSIN=1. Binary (520KB) links cleanly.
2. **[Session 3: Phase 1 Complete — libgcin-core.a Builds](logs/2026-05-05-session-03-libgcin-core-build.md)** (2026-05-05) — Modified 4 gcin files; created gcin-core/ (API, stubs, Makefile); libgcin-core.a (930KB) builds clean. Discoveries: compile as C not C++; pho-sym.cpp and unix-exec.cpp needed; box_warn() needs guarding too.
3. **[Session 2: Implementation Guide Deep Audit](logs/2026-05-05-session-02-impl-guide-deep-audit.md)** (2026-05-05) — Per-file GTK/X11 audit: only 2 files call GTK (util.cpp, gcin-conf.cpp); eliminated compat/ directory; reduced GCIN_CORE_BUILD to 5 types; found 13 duplicate symbol conflicts in stub list; decided to keep `typedef void GtkWidget`; deleted INIT-GUIDE.md.
4. **Session 1: Project kickoff + full planning** (2026-05-04) — Defined goals; approved SPEC.md; drafted DESIGN.md; audited gcin source tree (entry points, IBus/X11 keyval compatibility); drafted IMPLEMENTATION-GUIDE.md with Phase 1 plan for `libgcin-core.a`; initialized both git repos.

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

**Last Updated:** 2026-05-05 (Session 4 addendum — test infrastructure)
