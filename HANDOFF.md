# Handoff: gcin-everywhere

**Project:** gcin-everywhere
**Started:** 2026-05-04

---

## Navigation

**Project Docs:** [README](README.md) | [SPEC](SPEC.md) | [DESIGN](DESIGN.md) | [IMPLEMENTATION-GUIDE](IMPLEMENTATION-GUIDE.md) | [HANDOFF](HANDOFF.md) *(you are here)*

**Quick Jump:** [Current Status](#current-status) | [Next Actions](#next-actions) | [Session Logs](#session-logs)

---

## Current Status

**Phase:** Phase 2 complete — CJ5, Quick, Array all added; 5 IBus engines total
**Progress:** `gcin_core_feedkey_cj5/quick/array()` via shared `feedkey_gtab_method()`; 5 IBus engines (Cangjie, Zhuyin, Quick, Array, CJ5); 23/23 unit tests pass
**Next Milestone:** Phase 3 — Windows TSF port
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
> - ✅ Phase 6 — full-width mode (Shift+Space), `fullchar[]`, `full_char_proc()`
> - ✅ Phase 7 — Alt+Shift phrase.table + Ctrl phrase-ctrl.table; `gcin_core_feed_phrase()`
> - ✅ Phase 2 (additional engines) — Quick (速成) and Array (行列) via `feedkey_gtab_method()`
> - ✅ Phase 2 (CJ5) — CJ5 (倉頡五代) via `feedkey_gtab_method()`; 23/23 tests pass

### What We Have

- `gcin-core/libgcin-core.a` — 26 source files compiled with `-DGCIN_CORE_BUILD -DUSE_TSIN=1`
- `ibus-engine/ibus-engine-gcin` — links against libgcin-core.a + libibus-1.0
- `ibus-engine/component/gcin.xml` — IBus component descriptor (gcin-cangjie, gcin-zhuyin, gcin-quick, gcin-array, gcin-cj5)
- `process_key_event` routes via `switch(mode)` to `gcin_core_feedkey_cangjie/zhuyin/quick/array/cj5()`; preedit and candidates wired to IBus APIs
- **Cangjie working end-to-end** — `ko` → preedit shows 大, candidates appear, select commits 大人
- **Zhuyin preedit/candidates wired** — `gcin_core_get_preedit_zhuyin()` / `gcin_core_get_candidates_zhuyin()` implemented; engine detects mode from IBus engine name
- **Quick, Array, and CJ5 added** — share `feedkey_gtab` path via `feedkey_gtab_method(inmd_idx, ...)`; same preedit/candidates functions as Cangjie
- **Tests:** `gcin-core/test_feedkey.c` — 23 unit tests pass; `make test` skips cleanly without tables
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
- **`IBUS_space` not `XK_space` in IBus engine** — `XK_space` is undefined in `gcin_engine.c`; use IBus constants (`IBUS_space`, `IBUS_SHIFT_MASK`) for key checks in the engine layer
- **Half-width mode: non-component keys not consumed** — `feedkey_gtab` returns 0 for keys like `,`; IBus passes them to the app. Only full-width mode routes them through `send_text()` via `full_char_proc()`
- **`feed_phrase()` already compiled** — `phrase.cpp` is in GCIN_SRCS with no X11/GTK deps; just needs an `extern` declaration wrapper in `gcin_stubs.cpp`, no copy
- **`watch_fopen` must prepend `TableDir`** — `phrase.cpp` calls `load_phrase("phrase.table")` with a bare filename; real `watch_fopen` (win-sym.cpp) falls back to `TableDir + "/" + filename`; our stub was missing this so phrase tables were silently unfound
- **`cj.gtab` `zx__` codes** — `、`=`zxac`, `…`=`zxal`, `—`=`zxay` etc. already work; Cangjie users can type these directly
- **Zhuyin candidates from `ch_pho[]` not `disp_pho_sel` string** — `poo.start_idx + poo.cpg` gives page start; `poo.maxi` gives count; both set before `disp_pho_sel()` returns, so reading after `feedkey_pho()` is safe
- **ㄨ is implicit after ㄓ/ㄔ/ㄕ in Daqian** — pressing `u` after `j` does not change `poo.typ_pho[]`'s phokey representation; the tone press is what grows the preedit
- **Engine mode detected in `enable()` not `init()`** — GObject properties are not set when `_init()` runs; `ibus_engine_get_name()` returns NULL there. Mode is set in `gcin_engine_enable()` which fires on each engine switch when the name is valid.
- **`pho_load()` checks `getenv("GCIN_TABLE_DIR")` not `TableDir`** — `gcin_core_init()` must call `setenv("GCIN_TABLE_DIR", table_dir, 1)` in addition to setting `TableDir`; otherwise pho_load takes the "copy to ~/.gcin/" branch and fails
- **`gcin_core_init()` must run before `ibus_bus_new()`** — table loading blocks the event loop; if called after `ibus_bus_request_name`, IBus daemon times out waiting for "CreateEngine" response
- **GNOME Shell doesn't auto-spawn user-local IBus engines** — `~/.local/share/ibus/component/` works for `ibus list-engine` but GNOME only exec's engines from `/usr/share/ibus/component/`; fix is a systemd user service that starts the engine at login
- **Systemd service uses `%h` not a hardcoded path** — `ExecStart=%h/.local/lib/ibus-gcin/ibus-engine-gcin`; `%h` is the systemd unit specifier for the user's home directory, making the service file portable across users
- **Quick and Array share `feedkey_gtab` — only the `.gtab` table differs** — switching `cur_inmd` and calling `init_gtab(inmd_idx)` before `feedkey_gtab()` is sufficient; preedit and candidates functions are identical to Cangjie
- **Quick candidates are sorted by tsin use-count, not `.cin` order** — compiled binary orders candidates by frequency data; tests for multi-match cases must use `EXPECT_COMMITTED_NONEMPTY` rather than asserting a specific character
- **Array `%endkey 1234567890` means digits are combined endkey+selkey** — after a full code, pressing a digit auto-commits the single match in one step without needing space first; pressing space triggers a different but equivalent code path
- **`find_inmd("cj5")` is safe alongside `find_inmd("cj")`** — `strstr("cj.gtab","cj5")` = NULL, so the CJ3 entry is never confused with CJ5; gtab.list lists them in order: cj.gtab before cj5.gtab
- **CJ5 has 74,944 characters** vs 13,209 in CJ3 — larger table, same code path

---

## Next Actions

1. **Phase 3: Windows TSF port** — platform layer for Windows using Text Services Framework. `libgcin-core.a` links as-is; only the platform integration layer changes (analogous to `ibus-engine/` but for TSF).

**Deferred / absent from snapshot:**
- Buxiemi (嘸蝦米) — `noseeing.gtab` and source `.cin` absent from gcin snapshot
- Dayi (大易) — `dayi3.cin` absent from snapshot

**Deferred:**
- macOS (IMKit) port — future phase.
- Fcitx5 engine — not planned for current phase.

---

## Session Logs

1. **[Session 15: Phase 2 — CJ5 (倉頡五代)](logs/2026-05-05-session-15-phase2-cj5.md)** (2026-05-05) — Added CJ5 engine via `feedkey_gtab_method()`; 5 IBus engines; 23/23 tests pass.
2. **[Session 14: Phase 2 — Quick and Array Input Methods](logs/2026-05-05-session-14-phase2-quick-array.md)** (2026-05-05) — Added Quick (速成) and Array (行列) engines via shared `feedkey_gtab_method()`; 4 IBus engines; 20/20 tests pass.
3. **[Session 13: Phase 7 — Alt+Shift / Ctrl Phrase Tables](logs/2026-05-05-session-13-phase7-phrase-tables.md)** (2026-05-05) — `gcin_core_feed_phrase()` wraps `feed_phrase()`; Alt+Shift→phrase.table, Ctrl→phrase-ctrl.table; fixed `watch_fopen` stub to prepend TableDir; 15/15 tests pass.
4. **[Session 12: Phase 6 — Full-Width Mode; Phase 7 Planned](logs/2026-05-05-session-12-phase6-fullwidth-phase7-plan.md)** (2026-05-05) — Implemented Shift+Space full-width toggle; copied `half_char_to_full_char`+`full_char_proc`; 11/11 tests; investigated Alt+Shift/Ctrl phrase tables; Phase 7 designed.
5. **[Session 11: GitHub Setup and Top-Level Makefile](logs/2026-05-05-session-11-github-and-makefile.md)** (2026-05-05) — Forked gcin to ThinkerYzu/gcin; created ThinkerYzu/gcin-everywhere; top-level Makefile handles full pipeline; `make test && make install` is the complete workflow.

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

**Last Updated:** 2026-05-05 (Session 15 — Phase 2 complete: CJ5 added; 5 engines total)
