# Handoff: gcin-everywhere

**Project:** gcin-everywhere
**Started:** 2026-05-04

---

## Navigation

**Project Docs:** [README](README.md) | [SPEC](SPEC.md) | [DESIGN](DESIGN.md) | [IMPLEMENTATION-GUIDE](IMPLEMENTATION-GUIDE.md) | [HANDOFF](HANDOFF.md) *(you are here)*

**Quick Jump:** [Current Status](#current-status) | [Next Actions](#next-actions) | [Session Logs](#session-logs)

---

## Current Status

**Phase:** Voice Phase A **complete and confirmed working live** (user dictated into an app end-to-end). Input-method work through Phase 12 complete (7 IBus engines + GNOME Shell extension).
**Progress:** 6 single-method engines (Cangjie, Zhuyin, Quick, Array, CJ5, SimplexPunc) + `gcin-everywhere` unified switcher (Ctrl+Alt+digit, Ctrl+Space English toggle, resets to English on focus-in) + GNOME Shell extension showing the live method; 29/29 unit tests pass. **Voice input (台語語音) Phase A — working:** `gcin-voiced` ASR daemon (Breeze-ASR-26 over a Unix-socket JSON protocol, `--mock` for testing) + voice mode (Ctrl+Alt+0) in the unified engine (Space=PTT, Enter=commit, async preedit, 語/🎤/… panel glyph). Daemon **installed as a systemd `--user` service** (autostarts at login; venv symlinked to the existing CUDA venv to avoid re-download). Confirmed live by the user; model loads on cuda:0 in ~6 s; docs in source README. **Punctuation restoration (Session 21):** the daemon post-processes each transcript through a local LLM (Ollama `qwen3:14b`, `think:false`) to add ，。！？ **without changing the wording** before the `transcript` event — stdlib HTTP, on by default, word-skeleton guard + error fall-back never corrupt/lose the transcript; engine unchanged; `keep_alive:5m` (qwen3:14b co-fits the GPU). `test-punctuator.py` (8 + live) passes. *(A Mandarin→Taiwanese translation variant was tried and reverted — quality insufficient.)*
**Next Milestone:** Phase B (whisper.cpp/GGML native daemon) or Phase 3 (Windows TSF port)
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
> - ✅ Phase 2 (SimplexPunc) — 標點簡易 via `feedkey_gtab_method()`; 25/25 tests pass
> - ✅ Phase 10 — unified `gcin-everywhere` engine: Ctrl+Alt+digit switches method in place; panel property; 29/29 tests pass
> - ✅ Phase 11 — GNOME Shell extension: engine publishes the active method to a state file; extension mirrors the glyph in the top panel, shown only while gcin-everywhere is active
> - ✅ Phase 12 — gcin-everywhere resets to English on focus-in (each newly-focused field starts in English; method preserved for Ctrl+Space resume); confirmed live by the user
> - ✅ Voice Phase A — `gcin-voiced` daemon (socket JSON protocol, `--mock` + protocol test) + voice mode (Ctrl+Alt+0) in the unified engine; builds clean, JSON-parser unit test passes; **confirmed working live** (user dictated end-to-end); daemon installed as a systemd `--user` service (autostart at login)

### What We Have

- `gcin-core/libgcin-core.a` — 26 source files compiled with `-DGCIN_CORE_BUILD -DUSE_TSIN=1`
- `ibus-engine/ibus-engine-gcin` — links against libgcin-core.a + libibus-1.0
- `ibus-engine/component/gcin.xml` — IBus component descriptor (gcin-cangjie, gcin-zhuyin, gcin-quick, gcin-array, gcin-cj5, gcin-simplex-punc, **gcin-everywhere**)
- `process_key_event` routes via `switch(mode)` to `gcin_core_feedkey_cangjie/zhuyin/quick/array/cj5/simplex_punc()`; preedit and candidates wired to IBus APIs
- **gcin-everywhere unified engine** — `Ctrl+Alt+digit` switches `e->mode` in place (1=倉頡 2=倉五 3=注音 4=速成 5=標點簡易 8=行列); `Ctrl+Space` toggles Chinese ↔ English passthrough (panel shows 英); **resets to English on focus-in** (each newly-focused field starts in English; `e->mode` preserved so Ctrl+Space resumes it); panel `IBusProperty` shows the live method; switching gated to this engine only
- **GNOME panel indicator** — `gnome-extension/gcin-everywhere@gcin.dev/` (GNOME 45+ ESM). The engine writes the active method to `$XDG_RUNTIME_DIR/gcin-everywhere/state` (`"<glyph>\t<label>"`, empty when disabled); the extension watches it via `Gio.FileMonitor` and shows the glyph in the top bar, **only** while gcin-everywhere is the active source. Installed **and auto-enabled** by `make install-extension` (user-local; gated on `gnome-shell` detection; appends UUID to `enabled-extensions`). User's only step is a Wayland logout/in so the shell loads it
- **Cangjie working end-to-end** — `ko` → preedit shows 大, candidates appear, select commits 大人
- **Zhuyin preedit/candidates wired** — `gcin_core_get_preedit_zhuyin()` / `gcin_core_get_candidates_zhuyin()` implemented; engine detects mode from IBus engine name
- **Quick, Array, CJ5, SimplexPunc added** — share `feedkey_gtab` path via `feedkey_gtab_method(inmd_idx, ...)`; same preedit/candidates functions as Cangjie
- **Tests:** `gcin-core/test_feedkey.c` — 25 unit tests pass; `make test` skips cleanly without tables
- **Tests:** `ibus-engine/test-registration.sh` — registration check; auto-detects `/tmp/gcin-tables`
- **Table tools built** (not committed): `gcin2tab`, `phoa2d`, `tsa2d32`, `kbmcv` — built with GCIN_CORE_BUILD + libgcin-core.a
- **Voice input Phase A** — `voiced/gcin-voiced.py` (ASR daemon: Breeze-ASR-26 over `$XDG_RUNTIME_DIR/gcin-everywhere/voiced.sock`, newline-JSON `ping/start/stop/cancel/config` ↔ `ready/recording/thinking/transcript/error`; lazy model load, daemon-owned mic, worker-thread transcription, `--mock` backend); `voiced/test-protocol.py` passes; `voiced/{gcin-voiced.service,requirements.txt,README.md}`. Engine: `MODE_VOICE` (mode 6) in `gcin-everywhere` via `Ctrl+Alt+0`; socket client on a GLib `GSource`; Space=PTT, Enter=commit, Esc/Backspace=discard; 語/🎤/… panel glyph through the existing state file. Design + status: [research/VOICE-INPUT-DESIGN.md](research/VOICE-INPUT-DESIGN.md)

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
- **Ctrl+Space = English toggle inside gcin-everywhere; pass-through elsewhere** (Session 17) — in the unified engine, `Ctrl+Space` toggles `chinese_mode` (Chinese ↔ English passthrough, gcin-native `gcin_im_toggle`); `e->mode` is preserved so toggling back resumes the last method; panel shows 英. The handler sits **before** the `if (!chinese_mode) return FALSE` early-return so it can re-enable Chinese. Single-method engines return FALSE for Ctrl+Space (desktop handles it).
- **Plain Ctrl+Space must be free at the desktop level** (Session 17) — GNOME/mutter checks its shortcuts before forwarding keys to the IBus engine, so the in-engine toggle only fires if nothing else binds plain `Ctrl+Space`. Clear all three: `gsettings set org.gnome.desktop.wm.keybindings switch-input-source "['<Shift><Control>space']"`, `... switch-input-source-backward "[]"`, and remove `Control+space` from `org.freedesktop.ibus.general.hotkey trigger`. A **symmetric two-press** to switch input source is the tell-tale of a double-bound Ctrl+Space. `wm.keybindings` apply live; the IBus `trigger` change needs logout/in.
- **`feed_phrase()` already compiled** — `phrase.cpp` is in GCIN_SRCS with no X11/GTK deps; just needs an `extern` declaration wrapper in `gcin_stubs.cpp`, no copy
- **`watch_fopen` must prepend `TableDir`** — `phrase.cpp` calls `load_phrase("phrase.table")` with a bare filename; real `watch_fopen` (win-sym.cpp) falls back to `TableDir + "/" + filename`; our stub was missing this so phrase tables were silently unfound
- **`cj.gtab` `zx__` codes** — `、`=`zxac`, `…`=`zxal`, `—`=`zxay` etc. already work; Cangjie users can type these directly
- **Zhuyin candidates from `ch_pho[]` not `disp_pho_sel` string** — `poo.start_idx + poo.cpg` gives page start; `poo.maxi` gives count; both set before `disp_pho_sel()` returns, so reading after `feedkey_pho()` is safe
- **ㄨ is implicit after ㄓ/ㄔ/ㄕ in Daqian** — pressing `u` after `j` does not change `poo.typ_pho[]`'s phokey representation; the tone press is what grows the preedit
- **Engine mode detected in `enable()` not `init()`** — GObject properties are not set when `_init()` runs; `ibus_engine_get_name()` returns NULL there. Mode is set in `gcin_engine_enable()` which fires on each engine switch when the name is valid.
- **`pho_load()` checks `getenv("GCIN_TABLE_DIR")` not `TableDir`** — `gcin_core_init()` must call `setenv("GCIN_TABLE_DIR", table_dir, 1)` in addition to setting `TableDir`; otherwise pho_load takes the "copy to ~/.gcin/" branch and fails
- **`gcin_core_init()` must run before `ibus_bus_new()`** — table loading blocks the event loop; if called after `ibus_bus_request_name`, IBus daemon times out waiting for "CreateEngine" response
- **GNOME Shell doesn't auto-spawn user-local IBus engines** — fix is a systemd user service that starts the engine at login
- **The component XML MUST be in the system dir `/usr/share/ibus/component/`, NOT `~/.local/share/ibus/component/`** (Session 17) — ibus-daemon scans only the system XDG data dirs, so a user-local component never appears in `ibus list-engine` or the GNOME picker (verified: 973 engines loaded, 0 from `~/.local`). Earlier sessions only seemed to work because a stale 2-engine system file happened to exist. The binary + tables + systemd service stay user-local; the system component just points `<exec>` at the user binary. **Two same-named components collide** (`org.freedesktop.IBus.Gcin`): a stale system file shadows everything, so reinstall must overwrite it, then `ibus write-cache && ibus restart`. The Makefile `install` target now does this via `sudo` (needs a password).
- **Systemd service uses `%h` not a hardcoded path** — `ExecStart=%h/.local/lib/ibus-gcin/ibus-engine-gcin`; `%h` is the systemd unit specifier for the user's home directory, making the service file portable across users
- **Quick and Array share `feedkey_gtab` — only the `.gtab` table differs** — switching `cur_inmd` and calling `init_gtab(inmd_idx)` before `feedkey_gtab()` is sufficient; preedit and candidates functions are identical to Cangjie
- **Quick candidates are sorted by tsin use-count, not `.cin` order** — compiled binary orders candidates by frequency data; tests for multi-match cases must use `EXPECT_COMMITTED_NONEMPTY` rather than asserting a specific character
- **Array `%endkey 1234567890` means digits are combined endkey+selkey** — after a full code, pressing a digit auto-commits the single match in one step without needing space first; pressing space triggers a different but equivalent code path
- **`find_inmd("cj5")` is safe alongside `find_inmd("cj")`** — `strstr("cj.gtab","cj5")` = NULL, so the CJ3 entry is never confused with CJ5; gtab.list lists them in order: cj.gtab before cj5.gtab
- **CJ5 has 74,944 characters** vs 13,209 in CJ3 — larger table, same code path
- **`find_inmd("simplex-punc")` is unambiguous** — `strstr("simplex.gtab","simplex-punc")` = NULL; suffix match `"simplex-punc"` in `enable()` is checked before the cangjie catch-all
- **gcin-everywhere needs zero gcin-core changes** — the core already switches methods per-keypress (each `feedkey_<method>` sets `in_method` + `init_gtab()` on first call); the unified engine just makes the IBus layer's `e->mode` mutable at runtime via a Ctrl+Alt+digit handler in `process_key_event()`
- **Ctrl+Alt+digit handler must run first in `process_key_event`** — before the Shift+Space and Ctrl/Alt phrase intercepts; gated on `e->allow_switch` (TRUE only when engine name ends in `everywhere`) so the 6 single-method engines pass Ctrl+Alt+digit through to the app unchanged
- **IBus clears panel properties on focus change** — the gcin-everywhere `IBusProperty` must be re-registered in a `focus_in` handler, not only in `enable()`; keep an owned ref on both the prop and the prop-list so the pointer stays valid for `ibus_engine_update_property()`
- **Digit map mirrors gcin's gtab.list `key_ch`** (1/2/3/8) and extends it (4=速成 Quick, 5=標點簡易 SimplexPunc) since gcin leaves those on `-`
- **libibus dev headers are re-extractable** — `cd /tmp/ibus-dev-extract && apt-get download libibus-1.0-dev && dpkg-deb -x *.deb .` (IBus 1.5.32); the Makefile falls back to `/tmp/ibus-dev-extract/usr/include/ibus-1.0` when pkg-config has no `ibus-1.0`
- **GNOME Shell ignores IBus property symbol updates** (Session 18) — the top-bar input indicator shows only an engine's **static `symbol` from the component XML**, so a single-engine switcher like gcin-everywhere can only ever show 全. The live property symbol updates *do* work on KDE / the standalone `ibus-ui-gtk3` panel, just not GNOME Shell. The GNOME-native fix is an **external indicator** (a Shell extension), not more property work.
- **GNOME indicator = state file + extension, not D-Bus** (Session 18) — the engine writes `$XDG_RUNTIME_DIR/gcin-everywhere/state` (`"<glyph>\t<label>"`, empty when disabled) in `write_state()`, called from `update_property()` (every switch/enable/focus-in) and cleared in `disable()`. The extension watches it with `Gio.FileMonitor` (inotify, no polling). This needs zero new C deps and **coexists** with the IBus property (both always written; whichever the desktop supports renders). Visibility is tied to enable/disable so it shows only for the unified engine.
- **A stale daemon-spawned engine can keep serving old code** (Session 18) — after `systemctl --user restart`, an engine process spawned the prior day *outside* systemd's cgroup (exe shows `(deleted)`) still owned the bus name `org.freedesktop.IBus.Gcin`; the freshly-restarted process requested the name with flag 0 (no replace) and sat idle, so the **old binary kept handling the engine** (symptom: new state file never appeared). Fix: `kill <stale-pid>`, `systemctl --user restart ibus-engine-gcin`, `ibus restart`. Future hardening: request the name with `IBUS_BUS_NAME_FLAG_REPLACE_EXISTING | ALLOW_REPLACEMENT`.
- **Wayland needs logout/in for a new extension** (Session 18) — GNOME Shell can't be reloaded live on Wayland (Alt+F2 `r` is X11-only), so a newly-installed extension isn't listed by `gnome-extensions` until the next login.
- **The engine does NOT spawn the daemon — it must run independently** (Session 20) — `voiced_connect()` only `connect()`s to an existing socket; there is no fork/exec. If `gcin-voiced` isn't running, `Ctrl+Alt+0` then `Space` is a **silent no-op** (the start command is dropped, nothing recorded) — this was the first live-test failure. Fix/standard setup: run the daemon as a systemd `--user` service. Installed at `~/.local/lib/gcin-voiced/` with `~/.local/lib/gcin-voiced/venv` **symlinked to the existing POC CUDA venv** (`proj_docs/.../research/poc/.venv`) so the stock `gcin-voiced.service` works unchanged and ~6 GB of torch isn't duplicated (trade-off: the service breaks if that checkout moves — a dedicated venv is the robust alternative). Lazy load keeps login cheap (~7 MB idle); model loads on first ping.
- **Voice = mode 6 in the unified engine, ASR out-of-process** (Session 20) — voice is just another `e->mode` (`MODE_VOICE`, `Ctrl+Alt+0`); no new IBus engine, no component-XML change, no GNOME-extension change. The recognizer (Breeze-ASR-26) runs in a separate `gcin-voiced` daemon; the engine is a thin Unix-socket client whose fd is on a GLib `GSource` (`g_io_add_watch`), so transcript events update the preedit **asynchronously and `process_key_event` never blocks**. The socket protocol is the only contract → the Python/Transformers backend can later be swapped for whisper.cpp with zero engine changes. The daemon's `--mock` backend makes the whole contract testable with no GPU/mic.
- **Voice PTT = in-engine `Space`, commit = `Enter`** (Session 20) — choosing Space (handled inside the engine once voice mode is active) sidesteps the desktop-grab problem that forces the `gsettings` clearing for Ctrl+Space; no desktop config needed. Space toggles record / re-records; Enter commits the pending transcript; Esc/Backspace discards. Refines design decisions 5 & 7.
- **Engine parses daemon JSON by hand, no json-glib** (Session 20) — `json_get_str()` is a tiny string-value extractor; safe because the daemon controls the format and dumps `ensure_ascii=False` (literal UTF-8, no `\uXXXX`). Keeps the engine dependency-light. Unit-tested against representative daemon lines.
- **Voice transcripts get punctuation from a local LLM, in the daemon** (Session 21) — Breeze-ASR-26 emits Han text with no punctuation, so `gcin-voiced.py`'s `Punctuator` posts each transcript to Ollama (`qwen3:14b`, `think:false`, stdlib HTTP) which inserts ，。！？ **without changing the wording**, before the `transcript` event. Daemon-side of the socket (engine unchanged); runs in the transcribe worker thread (latency behind "…thinking"; never blocks `process_key_event`). Safety: error/Ollama-down → raw text; output accepted only if its **word skeleton** (punctuation+whitespace stripped) equals the input's (rejects drops/adds/translations). On by default, off in mock; `--no-punctuate`/`--punctuate-model`/`--punctuate-keep-alive`/`{"cmd":"config","punctuate":false}` override.
- **GPU co-tenancy: the LLM must not be resident during transcription** (Session 21, debugged from a live "no-output" wedge) — an LLM resident in VRAM while Breeze runs starves Whisper's `.generate()` and wedges it (worst case the 13–16 GB vision model qwen2.5vl). Fixes: **never pre-warm** the LLM (it loads on demand *after* transcription), and pick `keep_alive` per model. The default `qwen3:14b` (~9.8 GB) **co-fits** Breeze (~6.6 GB) — verified `.generate()` runs with ~7.6 GB free — so default `keep_alive:5m` (resident, ~2–3 s/utterance). Heavier models: `--punctuate-keep-alive 0` (unload after each call).
- **Tried & reverted: Mandarin→Taiwanese translation in the LLM step** (Session 21) — user wanted Taiwanese (台文) output, not the ASR's Mandarin. qwen2.5vl:7b translated poorly; qwen3:14b better but still draft quality (看→睇, leftover Mandarin). User judged it not good enough → reverted to punctuation-only. Future: a 台文-tuned model or ASR that emits Taiwanese directly, not LLM translation after the fact.
- **gcin-everywhere resets to English on focus-in** (Session 19) — `gcin_engine_focus_in()` clears `chinese_mode` (+ `gcin_core_reset()`, hide preedit/lookup, `update_property()`) for `allow_switch` engines, so every newly-focused field starts in English. **IBus exposes focus, not window identity** — the standard `focus_in` carries no window, and even 1.5.27+'s `focus_in_id(object_path, client)` identifies the toolkit/app, not the window — so the reset necessarily fires on *any* focus gain (different window, different field, re-entering one). `e->mode` is preserved (Ctrl+Space resumes); always on (no flag). Single-method engines unaffected (gated on `allow_switch`).

---

## Next Actions

1. ✅ **gcin-everywhere confirmed working end-to-end** (Session 17) — all 7 engines load (component installed to system dir `/usr/share/ibus/component/gcin.xml`); `Ctrl+Alt+1/2/3/4/5/8` switches method in place and `Ctrl+Space` toggles Chinese ↔ English, both confirmed by the user during live typing.
2. ✅ **GNOME panel indicator confirmed working** (Session 18, re-confirmed Session 19) — extension enabled via gsettings + logout/in; the glyph appears and updates live as the method switches, including 英 on the focus-reset to English.
3. ✅ **gcin-everywhere resets to English on focus change** (Session 19) — confirmed live by the user: typing Chinese then switching window/field comes up in English; Ctrl+Space resumes the method.
4. ✅ **Voice Phase A — confirmed working live + packaged** (Session 20) — daemon installed as a systemd `--user` service (autostart at login, venv symlinked to the POC CUDA venv); user dictated speech into an app end-to-end (Ctrl+Alt+0 → Space → speak → Space → Enter). Model loads on cuda:0 in ~6 s. Now reproducible via **`make install-voiced`** (`VOICED_VENV=/path/.venv` to reuse a venv, else builds a fresh one). **Open follow-ups:** confirm mic capture works under the systemd service env (prior live success used the hand-started daemon; PipeWire reached via `$XDG_RUNTIME_DIR`); tune the too-short/silence threshold.
5. ✅ **Voice punctuation restoration** (Session 21) — daemon adds ，。！？ via Ollama `qwen3:14b` (`think:false`, `keep_alive:5m`, no pre-warm) without changing words; guards + GPU-contention fix verified; deployed to the systemd service. **Open follow-up:** user to confirm live that punctuation appears in the preedit. *(Translation to Taiwanese was tried and reverted — quality insufficient.)*
6. **Voice Phase B/C** (future) — B: convert Breeze-ASR-26 to GGML and reimplement the daemon on whisper.cpp (CPU-capable, dependency-light) behind the same socket — zero engine changes. C: N-best correction candidates in the lookup table, streaming partials, idle model unload, optional hold-to-talk + global chord, optional Tâi-lô output; a better Taiwanese-output path (台文-tuned model).
7. **Phase 3: Windows TSF port** — platform layer for Windows using Text Services Framework. `libgcin-core.a` links as-is; only the platform integration layer changes (analogous to `ibus-engine/` but for TSF).

**Deferred / absent from snapshot:**
- Buxiemi (嘸蝦米) — `noseeing.gtab` and source `.cin` absent from gcin snapshot
- Dayi (大易) — `dayi3.cin` absent from snapshot

**Deferred:**
- macOS (IMKit) port — future phase.
- Fcitx5 engine — not planned for current phase.

---

## Session Logs

1. **[Session 21: Voice Input — Punctuation Restoration](logs/2026-06-25-session-21-voice-punctuation.md)** (2026-06-25) — `gcin-voiced` post-processes each transcript through a local LLM (Ollama `qwen3:14b`, `think:false`) to add ，。！？ without changing the wording; stdlib HTTP, on by default, word-skeleton guard + error fall-back; engine unchanged. Fixed a GPU-contention wedge (no pre-warm; `keep_alive:5m` since qwen3:14b co-fits). A Mandarin→Taiwanese translation variant was tried and reverted (quality insufficient). `test-punctuator.py` (8 + live) passes.
2. **[Session 20: Voice Input — Phase A](logs/2026-06-25-session-20-voice-input-phase-a.md)** (2026-06-25) — `gcin-voiced` ASR daemon (Breeze-ASR-26 over a Unix-socket JSON protocol, lazy load, `--mock` + protocol test) + voice mode (Ctrl+Alt+0, mode 6) in the unified engine: async socket client on a GLib GSource, Space=PTT, Enter=commit, 語/🎤/… panel glyph. Builds clean; daemon + JSON-parser tests pass; pending live GPU/mic test.
3. **[Session 19: Phase 12 — Reset to English on Focus Change](logs/2026-06-22-session-19-focus-reset-english.md)** (2026-06-22) — `gcin-everywhere` clears `chinese_mode` on `focus_in` so every newly-focused field starts in English; method preserved for Ctrl+Space resume. IBus exposes focus, not window identity, so it fires on any focus gain. Confirmed live.
4. **[Session 18: Phase 11 — GNOME Panel Indicator](logs/2026-06-22-session-18-gnome-panel-indicator.md)** (2026-06-22) — GNOME Shell extension showing the active gcin-everywhere method in the top bar; engine publishes state to `$XDG_RUNTIME_DIR/gcin-everywhere/state`; shown only while the unified engine is active. GNOME ignores IBus property symbols — hence the external indicator.
5. **[Session 17: Phase 10 — Unified gcin-everywhere Switcher](logs/2026-06-21-session-17-gcin-everywhere-switcher.md)** (2026-06-21) — Added `gcin-everywhere` engine: Ctrl+Alt+digit switches method in place (mirrors gcin `eve.cpp:1240`); panel IBusProperty; switching gated to this engine; no core changes; 29/29 tests pass.

Older logs in [HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md) (Session 16 and earlier).

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

**Last Updated:** 2026-06-25 (Session 21 — voice transcripts get LLM punctuation restoration via Ollama `qwen3:14b`, in the daemon, with fail-safe guards; Mandarin→Taiwanese translation tried and reverted)
