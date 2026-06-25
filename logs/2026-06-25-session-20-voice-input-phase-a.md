# Session 20: Voice Input — Phase A (gcin-voiced daemon + engine voice mode)

**Date:** 2026-06-25
**Phase:** Voice Phase A (MVP) — implementation
**Branch:** master

---

## Goals

- Continue the voice-input track: turn the [VOICE-INPUT-DESIGN.md](../research/VOICE-INPUT-DESIGN.md)
  proposal into a working Phase A — the `gcin-voiced` ASR daemon and a voice mode in the
  unified `gcin-everywhere` engine.

## What Was Done

### `gcin-voiced` daemon — `sources/gcin-everywhere/voiced/`

- **`gcin-voiced.py`** — Unix-domain-socket server implementing the design's newline-JSON
  protocol verbatim (`ping/start/stop/cancel/config` → `ready/recording/thinking/transcript/error`).
  - Backend abstraction: `AsrBackend` wraps the validated POC Transformers path (Breeze-ASR-26,
    lazy load, daemon-owned `sounddevice` mic capture); `MockBackend` returns a canned transcript
    with no model/mic.
  - Lazy model load on `ping` in a background thread (emits `ready` when up); transcription runs
    in a worker thread so the accept/read loop stays responsive to `cancel`. One engine client at
    a time; model persists across reconnects. State machine `idle→recording→thinking→idle`.
- **`--mock`** mode + **`test-protocol.py`** — drives a full exchange (ping→start→stop→transcript,
  cancel, unknown-cmd error) with **zero ML/audio deps**. Passes.
- **`gcin-voiced.service`** (systemd `--user`, `%h`-relative, deferred load), **`requirements.txt`**,
  **`README.md`**.

### Voice mode in `ibus-engine/gcin_engine.c`

- Voice is **mode 6 inside the existing unified engine** — no new IBus engine, no component-XML
  change, no GNOME-extension change. `Ctrl+Alt+0` → `MODE_VOICE`.
- Socket client: `voiced_connect/disconnect/send`; the fd is attached to the GLib main loop via
  `g_io_add_watch` (a `GSource`). Transcript events update the preedit **asynchronously**, so
  `process_key_event` never blocks on inference.
- Keys in voice mode: `Space` = PTT toggle (start/stop / re-record when pending), `Enter` =
  commit, `Esc`/`Backspace` = discard, `Esc` during recording = cancel.
- Panel glyph via the existing state file: `active_symbol()` returns 語 / 🎤 / … by voice sub-state;
  `write_state()`/`update_property()` refactored to use it (and `active_label()`). The GNOME
  extension renders it unchanged.
- Minimal hand-rolled JSON string extractor (`json_get_str`) — avoids a `json-glib` dependency;
  relies on the daemon's `ensure_ascii=False` literal-UTF-8 output. Unit-tested standalone.
- Entering/leaving voice and the focus-in English reset all cancel any live recording cleanly.
- Builds clean under `-Wall -Wextra` (fixed a `sun_path` truncation warning by bounding the path
  and detecting truncation).

## Key Findings

- **Space as the in-engine PTT key sidesteps the desktop-grab problem** that forces the
  `gsettings` dance for Ctrl+Space (HANDOFF decision, Session 17). Once voice mode is active,
  Space already reaches the engine, so PTT works with no desktop config.
- **Voice fits the unified engine as a pure mode** — the per-keypress `switch(e->mode)` and the
  state-file panel indicator already generalize; voice needed zero changes to the component XML
  or the GNOME extension.
- The daemon's `--mock` backend makes the whole engine↔daemon contract testable without a GPU or
  microphone — valuable for CI and for developing the C side here.

## Decisions Made

- **PTT = `Space` (in-engine), commit = `Enter`** — refines design decisions 5 & 7 (original draft
  had Space as a commit alternative). Documented in the design doc.
- **Hand-rolled JSON extraction, no json-glib** — keeps the engine dependency-light (consistent
  with the project's minimal-deps stance); safe because the daemon controls the output format and
  emits literal UTF-8.
- **Voice = mode 6 in `gcin-everywhere`, not a separate engine** — reuses mutable `e->mode`,
  the panel state file, and the `$XDG_RUNTIME_DIR/gcin-everywhere/` IPC dir.

## Status at End of Session

- ✅ Daemon builds/runs; `test-protocol.py` passes against `--mock`.
- ✅ Engine compiles clean (`-Wall -Wextra`); `json_get_str` unit test passes.
- ✅ **Real-mode model load verified over the socket** — daemon (real backend, POC venv) loads
  Breeze-ASR-26 on `cuda:0` in ~6 s on the RTX 3090 and emits `ready` to `ping`.
- ✅ **Confirmed working live by the user** — Ctrl+Alt+0 → Space → speak → Space → Enter committed
  the transcript into a real app. First attempt failed only because the daemon wasn't running.
- ✅ **Daemon deployed as a systemd `--user` service** — `~/.local/lib/gcin-voiced/` with the venv
  symlinked to the POC CUDA venv; `gcin-voiced.service` enabled (autostart at login, ~7 MB idle).
- No regression to the 6 existing methods (voice path gated on `e->mode == MODE_VOICE`).

## Post-session: live debug + deployment

- **Root cause of "Space does nothing":** the daemon was never started. The engine connects to the
  socket but does not spawn the daemon, so with nothing listening the `start` command is silently
  dropped. Documented as a key decision + in the source README troubleshooting.
- Installed the daemon as a systemd user service (autostart at login); venv symlinked to the
  existing POC CUDA venv to avoid duplicating ~6 GB of torch (trade-off: breaks if that checkout
  moves — dedicated venv is the portable option).
- Documented end-user voice usage (Ctrl+Alt+0 + Space/Enter/Esc, daemon setup) in the **source repo
  `README.md`**.

## Next Steps

- ✅ Live dictate→commit confirmed; daemon deployed as a systemd user service (done post-session).
- Confirm mic capture under the systemd service environment (prior live success used the
  hand-started daemon); tune the too-short/silence threshold.
- Optionally add a `make install-voiced` target (and an `install-voiced` variant that builds a
  dedicated, non-symlinked venv).
- Phase B (whisper.cpp/GGML native daemon) and Phase C (N-best lookup, hold-to-talk, idle unload,
  optional Tâi-lô) remain future.
