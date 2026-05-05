# Handoff: gcin-everywhere

**Project:** gcin-everywhere
**Started:** 2026-05-04

---

## Navigation

**Project Docs:** [README](README.md) | [SPEC](SPEC.md) | [DESIGN](DESIGN.md) | [IMPLEMENTATION-GUIDE](IMPLEMENTATION-GUIDE.md) | [HANDOFF](HANDOFF.md) *(you are here)*

**Quick Jump:** [Current Status](#current-status) | [Next Actions](#next-actions) | [Session Logs](#session-logs)

---

## Current Status

**Phase:** Phase 1 complete — Cangjie and Zhuyin working end-to-end in GNOME
**Progress:** Both engines install, autostart via systemd, and accept input correctly in GNOME; 9/9 unit tests pass
**Next Milestone:** Phase 2 — additional input methods (Quick/速成, Array/行列)
**Blockers:** None

> **Phase checklist:**
> - ✅ Spec drafted
> - ✅ Spec finalized (open questions resolved)
> - ✅ Design complete
> - ✅ Implementation guide ready
> - ✅ Phase 1 complete — libgcin-core.a (26 source files, links cleanly)
> - ✅ Phase 2 complete — ibus-engine-gcin skeleton builds
> - ✅ Unit tests pass (9/9) — `GCIN_TABLE_DIR=/tmp/gcin-tables make test`
> - ✅ IBus registration verified (ibus list-engine | grep gcin)
> - ✅ Phase 3 — Cangjie key routing, preedit, candidates
> - ✅ Phase 4 — Zhuyin preedit and candidates API
> - ✅ Phase 5 — Local install (`make install`), systemd autostart, GNOME switching works
> - ✅ Phase 1 complete — Cangjie and Zhuyin confirmed working end-to-end

### What We Have

- `gcin-core/libgcin-core.a` — 26 source files compiled with `-DGCIN_CORE_BUILD -DUSE_TSIN=1`
- `ibus-engine/ibus-engine-gcin` (520KB ELF) — links against libgcin-core.a + libibus-1.0
- `ibus-engine/component/gcin.xml` — IBus component descriptor (gcin-cangjie + gcin-zhuyin)
- `process_key_event` routes to `gcin_core_feedkey_cangjie/zhuyin()`; preedit and candidates wired to IBus APIs
- **Cangjie working end-to-end** — `ko` → preedit shows 大, candidates appear, select commits 大人
- **Zhuyin preedit/candidates wired** — `gcin_core_get_preedit_zhuyin()` / `gcin_core_get_candidates_zhuyin()` implemented; engine detects mode from IBus engine name
- **Tests:** `gcin-core/test_feedkey.c` — 9 unit tests pass; `make test` skips cleanly without tables
- **Tests:** `ibus-engine/test-registration.sh` — registration check; auto-detects `/tmp/gcin-tables`
- **Table tools built** (not committed): `gcin2tab`, `phoa2d`, `tsa2d32`, `kbmcv` — built with GCIN_CORE_BUILD + libgcin-core.a

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
- **`gcin_core_init()` must call `load_setttings()` + `load_gtab_list()` + `init_gtab()`** — without these, `pho_kbm_name` is NULL (segfault) and `cur_inmd` is NULL (no key processing)
- **`current_CS->tsin_pho_mode = 1` required** — without it, `feedkey_gtab` hits the ASCII passthrough branch for all printable keys
- **`gtab_auto_select_by_phrase = GTAB_OPTION_NO`** — phrase buffering must be disabled; otherwise `putstr_inp` routes single characters to the phrase buffer instead of `send_utf8_ch`
- **Cangjie cj.gtab uses `GTAB_space_auto_first_nofull`** — space alone does NOT auto-select; correct input is key(s) + space (spc_pressed=1) + selection key (1-9)
- **Table tools built without GTK2** — `gcin2tab`, `phoa2d`, `tsa2d32`, `kbmcv` compile with `GCIN_CORE_BUILD + libgcin-core.a + gtk_init() stub`. GTK2 not required.
- **Candidates read from `seltab[]` directly** — not parsed from `disp_gtab_sel` HTML string; `seltab` defined in `gtab-init.cpp`, declared extern in `gcin_stubs.cpp`
- **Commit callback re-registered per keypress** — `gcin_core_set_commit_cb(on_commit, iengine)` called in `process_key_event` to always target the active engine instance
- **Zhuyin candidates from `ch_pho[]` not `disp_pho_sel` string** — `poo.start_idx + poo.cpg` gives page start; `poo.maxi` gives count; both set before `disp_pho_sel()` returns, so reading after `feedkey_pho()` is safe
- **ㄨ is implicit after ㄓ/ㄔ/ㄕ in Daqian** — pressing `u` after `j` does not change `poo.typ_pho[]`'s phokey representation; the tone press is what grows the preedit
- **Engine mode detected in `enable()` not `init()`** — GObject properties are not set when `_init()` runs; `ibus_engine_get_name()` returns NULL there. Mode is set in `gcin_engine_enable()` which fires on each engine switch when the name is valid.
- **`pho_load()` checks `getenv("GCIN_TABLE_DIR")` not `TableDir`** — `gcin_core_init()` must call `setenv("GCIN_TABLE_DIR", table_dir, 1)` in addition to setting `TableDir`; otherwise pho_load takes the "copy to ~/.gcin/" branch and fails
- **`gcin_core_init()` must run before `ibus_bus_new()`** — table loading blocks the event loop; if called after `ibus_bus_request_name`, IBus daemon times out waiting for "CreateEngine" response
- **GNOME Shell doesn't auto-spawn user-local IBus engines** — `~/.local/share/ibus/component/` works for `ibus list-engine` but GNOME only exec's engines from `/usr/share/ibus/component/`; fix is a systemd user service that starts the engine at login

---

## Next Actions

1. **Phase 6 — Full-width character mode (NEXT)** — Un-stub `half_char_to_full_char()` and `full_char_proc()` in `gcin_stubs.cpp`; add `gcin_core_toggle_full_width()` API; handle Shift+Space in `gcin_engine.c`. Matches gcin's own mechanism exactly. See [IMPLEMENTATION-GUIDE.md Phase 6](IMPLEMENTATION-GUIDE.md#phase-6-full-width-character-mode-cangjie--zhuyin-punctuation) for the full plan.
2. **Phase 2 — Additional input methods** — Quick (速成), Array (行列), Dayi (大易). Same adapter pattern as Cangjie; each gets its own `<engine>` in gcin.xml and a mode constant.

**Deferred:**
- Windows (TSF) and macOS (IMKit) ports — future phases after Phase 1 is working.
- Fcitx5 engine — not planned for Phase 1.

---

## Session Logs

1. **[Session 11: GitHub Setup and Top-Level Makefile](logs/2026-05-05-session-11-github-and-makefile.md)** (2026-05-05) — Forked gcin to ThinkerYzu/gcin; created ThinkerYzu/gcin-everywhere; top-level Makefile handles full pipeline; `make test && make install` is the complete workflow.
2. **[Session 10: Mode Detection Fix — Phase 1 Complete](logs/2026-05-05-session-10-mode-fix-and-e2e-confirmed.md)** (2026-05-05) — Moved mode detection from `init()` to `enable()`; Cangjie and Zhuyin both confirmed working end-to-end.
2. **[Session 9: Phase 5 — Local Install and Systemd Autostart](logs/2026-05-05-session-09-install-and-autostart.md)** (2026-05-05) — `make install` deploys to `~/.local/`; fixed 3 bugs (setenv, init ordering, GNOME spawn); systemd user service auto-starts engine; GNOME switching works.
2. **[Session 8: Phase 4 — Zhuyin Preedit and Candidates](logs/2026-05-05-session-08-zhuyin-phase4.md)** (2026-05-05) — Added gcin_core_get_preedit_zhuyin/get_candidates_zhuyin API; wired update_ui() to branch on Cangjie vs Zhuyin mode; mode detected from IBus engine name; 3 new Zhuyin unit tests (9/9 pass).
2. **[Session 7: Phase 3 — Cangjie Working End-to-End](logs/2026-05-05-session-07-cangjie-phase3.md)** (2026-05-05) — Added gcin_core_get_preedit/get_candidates_cangjie API; wired process_key_event with preedit + lookup table; commit callback; ko → 大人 confirmed working.
2. **[Session 6: GCIN_TABLE_DIR Support + System-Wide IBus Registration](logs/2026-05-05-session-06-table-dir-and-registration.md)** (2026-05-05) — Engine reads GCIN_TABLE_DIR env var; test script auto-detects /tmp/gcin-tables; silenced mv error (no-op update_table_file stub); ibus list-engine confirms gcin-cangjie + gcin-zhuyin registered.
3. **[Session 5: Data Tables Compiled; All Unit Tests Pass](logs/2026-05-05-session-05-tables-and-tests.md)** (2026-05-05) — Built gcin2tab/phoa2d/tsa2d32/kbmcv without GTK2; compiled tables to /tmp/gcin-tables/; fixed 6 gcin_core_init() bugs (load_setttings, load_gtab_list, init_gtab, tsin_pho_mode, phrase buffer, reset); all 6 unit tests pass.
4. **[Session 4: Phase 2 — IBus Engine Skeleton Builds](logs/2026-05-05-session-04-ibus-skeleton.md)** (2026-05-05) — Created gcin_engine.c, gcin.xml, ibus-engine/Makefile; fixed 8 more duplicate stubs; added 5 files to libgcin-core.a; added g_strdup_printf/_()/GError/F-keys to GCIN_CORE_BUILD; added -DUSE_TSIN=1. Binary (520KB) links cleanly.
5. **[Session 3: Phase 1 Complete — libgcin-core.a Builds](logs/2026-05-05-session-03-libgcin-core-build.md)** (2026-05-05) — Modified 4 gcin files; created gcin-core/ (API, stubs, Makefile); libgcin-core.a (930KB) builds clean. Discoveries: compile as C not C++; pho-sym.cpp and unix-exec.cpp needed; box_warn() needs guarding too.

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

**Last Updated:** 2026-05-05 (Phase 6 plan finalized: copy convention and comment format specified in IMPLEMENTATION-GUIDE.md)
