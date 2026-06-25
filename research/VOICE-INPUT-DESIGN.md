# Design: gcin-everywhere Voice Input (Taiwanese ASR)

**Project:** gcin-everywhere
**Feature:** Voice dictation method — speak Taiwanese (Taigi)/Mandarin, commit Mandarin Han characters
**Status:** Phase A implemented (daemon + engine voice mode build & unit-test clean; pending live GPU/mic test) — Phases B/C future
**Created:** 2026-06-24
**Last Updated:** 2026-06-25 (Phase A implementation — Session 20)
**Depends on:** [breeze3-taiwanese-asr.md](breeze3-taiwanese-asr.md) (feasibility) · [poc/](poc/) (validated transcription + mic capture)
**Code:** `sources/gcin-everywhere/voiced/` (daemon) · `sources/gcin-everywhere/ibus-engine/gcin_engine.c` (voice mode)

---

## Navigation

**Project Docs:** [README](../README.md) | [SPEC](../SPEC.md) | [DESIGN](../DESIGN.md) | [IMPLEMENTATION-GUIDE](../IMPLEMENTATION-GUIDE.md) | [HANDOFF](../HANDOFF.md)
**Research:** [Breeze 3 feasibility](breeze3-taiwanese-asr.md) | [POC](poc/README.md) | **Voice Input Design** *(you are here)*

**This Document:**
- [Goal & Scope](#goal--scope)
- [Design Philosophy](#design-philosophy)
- [Architecture Overview](#architecture-overview)
- [Key Design Decisions](#key-design-decisions)
- [Socket Protocol](#socket-protocol)
- [Engine State & Interaction Flow](#engine-state--interaction-flow)
- [Risks & Open Questions](#risks--open-questions)
- [Phasing](#phasing)

---

## Goal & Scope

Add a **voice input method** to the `gcin-everywhere` unified engine: the user speaks
Taigi (or Mandarin, or code-switched speech) into a microphone and the recognized text —
**Mandarin Han characters** — is committed to the focused application, exactly as the
table/phonetic methods commit their output.

The recognizer is **MediaTek Breeze-ASR-26** (Whisper-large-v2 fine-tuned on Taigi),
run **fully locally**. The POC ([poc/](poc/README.md)) already proved transcription
quality (coherent Mandarin across varied intents), long-audio chunking, and mic capture.

**In scope:** push-to-talk dictation, per-utterance batch recognition, review-before-commit,
integration into the Ctrl+Alt+digit switcher and the panel indicator.
**Out of scope (this phase):** real-time streaming partials, Taiwanese romanization (Tâi-lô)
output, training/fine-tuning, non-Linux platforms.

### SPEC alignment

This extends the input-method surface; it does **not** change the existing engines. It
reuses the project's established mechanisms — the unified switcher's mutable `e->mode`,
the panel `IBusProperty`, and the `$XDG_RUNTIME_DIR/gcin-everywhere/` IPC directory —
so it is additive and gated to `gcin-everywhere` (like decisions 8–10 in [DESIGN.md](../DESIGN.md)).

---

## Design Philosophy

1. **Reuse, don't reinvent.** Recognition is Breeze-ASR-26 as-is; no model changes. The
   IBus integration reuses the unified-engine plumbing already shipped.
2. **Local-only, private by default.** Audio never leaves the machine; no network calls.
   This is a core selling point versus cloud dictation.
3. **Keep the engine thin and never block it.** The IBus engine is a C process driving
   GNOME's input loop. The heavy ML runtime lives in a **separate daemon**; the engine
   talks to it asynchronously and must never stall `process_key_event`.
4. **A stable socket boundary.** The engine⇄daemon protocol is the contract. The daemon's
   internals can start as Python/Transformers (validated) and later become native
   whisper.cpp without the engine changing.
5. **Accuracy-aware UX.** At ~30% CER, recognition is draft quality. Transcripts land in
   the **preedit** for review/commit, never silently auto-committed.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│            GNOME / Wayland focused application            │
└───────────────────────────┬──────────────────────────────┘
                            │ commit text (Mandarin Han)
┌───────────────────────────▼──────────────────────────────┐
│   ibus-engine-gcin  (gcin-everywhere mode = VOICE)        │
│   - Ctrl+Alt+0 enters voice mode; panel shows 語/🎤       │
│   - push-to-talk key → start/stop control messages        │
│   - GLib GSource on socket: async transcript → preedit    │
│   - Enter = commit preedit, Esc = discard                 │
└───────────────────────────┬──────────────────────────────┘
                            │ Unix domain socket (newline JSON)
                            │ $XDG_RUNTIME_DIR/gcin-everywhere/voiced.sock
┌───────────────────────────▼──────────────────────────────┐
│   gcin-voiced  (ASR daemon, systemd --user)               │
│   - owns mic capture (PortAudio/PipeWire)                 │
│   - holds Breeze-ASR-26 in memory (GPU or CPU)            │
│   - start → record; stop → transcribe → {transcript}      │
│   ┌────────────────────────────────────────────────────┐ │
│   │ Backend (swappable behind the socket):             │ │
│   │  Phase A: Python + 🤗 Transformers  (validated)    │ │
│   │  Phase B: whisper.cpp + GGML Breeze-ASR-26 (native)│ │
│   └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### Component Roles

| Component | New/Existing | Role |
|-----------|--------------|------|
| `gcin_engine.c` voice path | Extend existing | Voice mode, PTT key, socket client, async preedit/commit |
| `gcin-voiced` daemon | **New** | Audio capture + Breeze-ASR-26 inference; one socket server |
| Socket protocol | **New** | Newline-delimited JSON control/result channel |
| Breeze-ASR-26 weights | **New asset** | HF safetensors (Phase A) or GGML (Phase B) |
| systemd user unit | **New** | `gcin-voiced.service`, lazy model load |
| Panel indicator | Reuse | Shows 語/🎤 via the existing state file + extension |

---

## Key Design Decisions

### 1. Separate ASR daemon, not in-process

**Decision.** Recognition runs in a standalone `gcin-voiced` daemon, not linked into the
IBus engine.

**Rationale.** Breeze-ASR-26 is ~2B params (≈1.5 GB GGML, ~3 GB safetensors) and wants a
CUDA context. Loading that into `ibus-engine-gcin` would bloat a process that today starts
fast and only loads gcin tables, tie GPU init to engine startup, and waste memory whenever
voice is unused. A daemon loads the model once, lazily, and survives engine focus churn.
It also mirrors the project's existing out-of-process IPC (the `$XDG_RUNTIME_DIR/gcin-everywhere/`
state file).

### 2. The daemon owns audio capture

**Decision.** `gcin-voiced` captures the microphone; the engine sends only `start`/`stop`.

**Rationale.** Keeps PortAudio/PipeWire dependencies out of the C engine entirely. The
daemon already links the audio-capable runtime (the POC's `sounddevice` path). The engine
stays a pure control client — no PCM ever crosses the socket in the MVP. (A later streaming
phase may push PCM, but the boundary already allows it.)

### 3. Stable socket protocol = swappable backend

**Decision.** Engine⇄daemon speak newline-delimited JSON over a Unix domain socket at
`$XDG_RUNTIME_DIR/gcin-everywhere/voiced.sock`. See [Socket Protocol](#socket-protocol).

**Rationale.** The protocol is the only contract. **Phase A** ships the daemon as the
already-validated Python/Transformers code (reuse `poc/breeze_asr_mic.py` logic as a server).
**Phase B** swaps in a native whisper.cpp + GGML daemon for a dependency-light, CPU-capable
build — with **zero engine changes**. Breeze-ASR-26 is a standard HF Whisper checkpoint, so
whisper.cpp's `convert-h5-to-ggml.py` conversion path applies.

### 4. Voice is a mode in the unified switcher

**Decision.** Add a voice slot to the Ctrl+Alt+digit map: **`Ctrl+Alt+0` → 台語語音 (voice)**.
The panel property/state file shows **語** (or 🎤 while recording). Gated on `allow_switch`,
so only `gcin-everywhere` exposes it.

**Rationale.** Reuses decision 8's mutable `e->mode` dispatch and the panel indicator
(decision 9) verbatim — voice becomes "just another method", consistent UX. `0` is free in
the current map (1/2/3/4/5/8 used).

| Hotkey | `e->mode` | Method |
|--------|-----------|--------|
| `Ctrl+Alt+0` | (new) VOICE | 台語語音 Voice (Breeze-ASR-26) |

### 5. Push-to-talk interaction, toggle-style

**Decision.** In voice mode, a **push-to-talk key toggles recording**: press to start
(panel → 🎤, daemon `start`), press again to stop (daemon `stop`, transcribe).
**Phase A uses `Space` as the in-engine PTT key** — not a global desktop chord.

**Rationale.** Toggle is robust under IBus (no reliable key-*release* semantics for true
hold-to-talk across all apps). Per-utterance batch matches Whisper's 30 s window and the POC's
proven path. **Choosing Space (handled inside the engine while in voice mode) sidesteps the
desktop-grab caveat that afflicts Ctrl+Space (decision 8)**: once voice mode is active, Space
already reaches `process_key_event`, so no `gsettings` clearing is needed and it works out of
the box. In voice mode Space has no other meaning (utterances commit whole), so the overload is
free. Hold-to-talk and an optional global chord (`Super+grave`-style) move to Phase C.

### 6. Asynchronous, non-blocking transcript delivery

**Decision.** The engine attaches the socket fd to the GLib main loop as a `GSource`
(`g_io_add_watch`). `start`/`stop` are fire-and-forget writes. The `transcript` event arrives
later on the GLib callback, which updates the preedit — `process_key_event` **never blocks**.

**Rationale.** Transcription takes 100 ms–several seconds. Blocking the IBus engine loop would
freeze the user's keyboard everywhere. IBus already runs on GLib, so a `GSource` is the natural,
zero-extra-thread mechanism. While recognition is in flight the panel shows a "…thinking" glyph.

### 7. Commit-to-preedit with explicit confirmation

**Decision.** A returned transcript is placed in the **preedit buffer** (underlined,
uncommitted). `Enter` commits it via `ibus_engine_commit_text()`; `Esc`/`Backspace` discards;
`Space` (the PTT key) re-records, replacing the pending text. (Phase A change from the original
draft: commit is `Enter` only — `Space` is reserved for the PTT toggle per decision 5, so it
re-records rather than commits.) Optionally, alternative hypotheses (Whisper beam search N-best)
populate the IBus lookup table for quick swap (Phase C).

**Rationale.** At ~30% CER, silent auto-commit would scatter errors into documents. Review
fits IBus's existing preedit/lookup model (decision 5) and gives a correction point at no UI cost.

### 8. Output is Mandarin Han characters (documented, by design)

**Decision.** Voice mode commits Mandarin Han characters — Breeze-ASR-26 maps spoken Taigi →
中文漢字, not Tâi-lô/POJ. This is surfaced in UI help text.

**Rationale.** Consistent with every other gcin method (all emit Han characters) and convenient
for a Traditional-Chinese IME. Romanized-Taigi output is a possible future toggle, not MVP.

### 9. Daemon lifecycle: systemd user service, lazy load

**Decision.** `gcin-voiced.service` (systemd `--user`, `%h`-relative like the engine unit)
starts the daemon at login but **defers model loading until the first `start`**, so idle cost
is just the socket. The engine auto-starts/pings the daemon when voice mode is first entered.

**Rationale.** Most sessions never use voice; paying ~3 GB + CUDA init at every login is
unacceptable. Lazy load keeps non-voice users at zero cost while keeping first-use latency to
one model load.

---

## Socket Protocol

Unix domain socket `$XDG_RUNTIME_DIR/gcin-everywhere/voiced.sock`, newline-delimited JSON,
one object per line. Engine is the client; daemon is the server.

**Engine → daemon (commands):**
```json
{"cmd":"ping"}                      → liveness / trigger lazy model load
{"cmd":"start"}                     → begin mic capture
{"cmd":"stop"}                      → end capture, transcribe, return transcript
{"cmd":"cancel"}                    → drop capture, no transcription
{"cmd":"config","language":"chinese","task":"transcribe"}
```

**Daemon → engine (events):**
```json
{"event":"ready","model":"Breeze-ASR-26","device":"cuda:0"}
{"event":"recording"}               → mic is live (engine shows 🎤)
{"event":"thinking"}                → transcription started (engine shows …)
{"event":"transcript","text":"救命啊 快來救我","alts":["…"],"rtf":0.3}
{"event":"error","msg":"no input device"}
```

State machine (daemon): `idle → recording → thinking → idle`. `cancel` returns to `idle`
from `recording`. The engine mirrors this to the panel glyph (語 → 🎤 → … → 語).

---

## Engine State & Interaction Flow

### Added engine state (`GcinEngine`)

```c
int   voice_mode;        /* e->mode == VOICE */
int   voice_recording;   /* toggle state for the PTT key */
int   voiced_fd;         /* Unix socket to gcin-voiced, -1 if unconnected */
guint voiced_watch;      /* GSource id for async event delivery */
```

### Push-to-talk dictation flow

```
User: Ctrl+Alt+0                → e->mode = VOICE; connect socket; ping daemon; panel 語
User: press PTT key             → write {"cmd":"start"}; voice_recording=1
Daemon                          → {"event":"recording"}; panel 🎤
User: speaks Taigi
User: press PTT key again        → write {"cmd":"stop"}; voice_recording=0
Daemon                          → {"event":"thinking"}; panel …
Daemon (async, ~0.1–2s)         → {"event":"transcript","text":"…"}
Engine GSource callback         → set preedit = text (underlined); panel 語
User: Enter                     → ibus_engine_commit_text(text); clear preedit
   (or Esc to discard / PTT to re-record)
```

All daemon events arrive on the GLib `GSource`, so the keyboard is never blocked while
recording or transcribing.

---

## Risks & Open Questions

| Risk / Question | Notes / Mitigation |
|-----------------|--------------------|
| **CPU latency** | RTF 0.1–0.3 on RTX 3090; CPU is far slower. Phase A targets GPU boxes; Phase B (whisper.cpp) adds quantized CPU. May offer a smaller Whisper fallback. |
| **~30% CER** | Mitigated by review-before-commit (decision 7) + N-best alternatives. Set user expectations in help text. |
| **PTT key grabbed by mutter** | Same class as the Ctrl+Space issue (decision 8); pick an unbound chord and document the gsettings clear. |
| **Mic under Wayland/PipeWire** | Daemon uses PipeWire via PortAudio; device selection config like POC's `--device-index`. |
| **GPU memory shared with other apps** | Lazy load + a configurable `cpu`/`cuda` setting; daemon can unload after idle timeout. |
| **First-use latency (model load)** | `ping` on entering voice mode warms the model before the first utterance. |
| **Romanized Taigi (Tâi-lô) demand** | Out of scope now; protocol's `task`/`config` leaves room for an output-format flag later. |
| **Streaming partials** | Whisper is batch; chunked/streaming decoding is a later enhancement over the same socket (PCM push). |

---

## Implementation Status (Phase A)

Implemented in Session 20 (2026-06-25); builds and unit-tests clean, **pending a live
GPU/microphone end-to-end test**.

**Daemon — `sources/gcin-everywhere/voiced/`**
- `gcin-voiced.py` — Unix-socket server, newline-JSON protocol exactly as specified above.
  Lazy model load on `ping` (background thread → `ready`); daemon owns the mic; transcription
  runs in a worker thread so the accept loop stays responsive to `cancel`. One engine client at
  a time; the model stays loaded across reconnects.
- `--mock` backend (no model, no mic; canned transcript) lets the engine + protocol be developed
  and tested with **zero ML/audio dependencies**.
- `test-protocol.py` drives a full `ping → start → stop → transcript` + cancel + error exchange
  against `--mock`; **passes**.
- `gcin-voiced.service` (systemd `--user`, `%h`-relative, deferred model load), `requirements.txt`,
  `README.md`.

**Engine — `ibus-engine/gcin_engine.c`**
- Voice is **mode 6 inside the unified `gcin-everywhere` engine** (no new IBus engine, no
  component-XML change). `Ctrl+Alt+0` enters it (`digit_to_mode('0') → MODE_VOICE`), connects the
  socket and pings to warm the model.
- Socket client attached to the GLib main loop via `g_io_add_watch` (a `GSource`); transcript
  events update the preedit asynchronously — `process_key_event` never blocks.
- Keys: `Space` = PTT toggle (start/stop / re-record), `Enter` = commit pending, `Esc`/`Backspace`
  = discard, `Esc` while recording = cancel.
- Panel glyph via the existing state file + `active_symbol()`: 語 (idle) → 🎤 (recording) → … (thinking).
  The GNOME extension shows it unchanged — it just renders whatever glyph the state file holds.
- A minimal hand-rolled JSON string extractor (`json_get_str`, no `json-glib` dependency; relies on
  the daemon's `ensure_ascii=False` UTF-8 output) — unit-tested separately against representative
  daemon lines.
- Builds clean (`-Wall -Wextra`, no warnings).

**Still to do for Phase A:** install the daemon venv on a GPU box, run end-to-end into a real app,
tune the too-short/silence threshold, confirm panel glyph transitions live.

## Phasing

- **Phase A — MVP (GPU, Python daemon).** ✅ Implemented (above), pending live hardware test.
  `gcin-voiced` wraps the validated Transformers path as a socket server; engine voice mode
  (Ctrl+Alt+0), PTT toggle, async preedit, commit/discard, panel 語/🎤. Reuses [poc/](poc/)
  wholesale. Goal: end-to-end dictation into any app.
- **Phase B — Native runtime.** Convert Breeze-ASR-26 to GGML; reimplement the daemon on
  whisper.cpp (C/C++), CPU-capable and dependency-light. No engine changes (stable socket).
- **Phase C — UX polish.** N-best correction candidates in the lookup table, streaming partial
  results, idle model unload, optional hold-to-talk and a global shortcut, optional Tâi-lô output.

---

**Last Updated:** 2026-06-25 (Phase A implemented — daemon + engine voice mode; Session 20)
