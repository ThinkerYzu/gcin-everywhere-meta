# Session 21: Voice Input — Punctuation Restoration (LLM post-processing)

**Date:** 2026-06-25
**Phase:** Voice Phase A polish
**Branch:** master

---

## Goals

- Breeze-ASR-26 returns Mandarin Han text with **no punctuation**. Add a step that feeds the
  raw transcript to a local LLM to restore punctuation before it reaches the engine preedit.

## What Was Done

### Punctuation restorer in the daemon (`gcin-voiced.py`)

Added a `Punctuator` class that post-processes each transcript through **Ollama**
(`/api/chat`, default `qwen3:14b`, `temperature 0`, `think:false`) with a system prompt that
adds only `，。！？、；：` and changes no characters. It runs inside the existing
`_transcribe_worker` thread, between `transcribe()` and the `transcript` event — so the engine
is **unchanged**; it just receives nicer text. The latency hides behind the "…thinking" glyph.

Design choice: punctuation lives on the **daemon** side of the socket boundary (keeps the engine
thin and the local-only privacy guarantee). Uses **stdlib HTTP only** — no new Python dependency.

### Two safety nets

- **Never lose a transcript** — Ollama down / timeout / any error → fall back to the raw text.
- **Never corrupt words** — accept the LLM output only if its *word skeleton* (text with
  punctuation + whitespace stripped, `_word_skeleton()`) equals the input's. Dropped / added /
  **translated** / changed characters → discard, keep raw. `_clean()` strips `<think>` blocks
  and quote / code-fence wrappers.

### Wiring + config

- On by default in **real** mode, **off** in mock mode (so the dependency-free `test-protocol.py`
  doesn't need Ollama). `--punctuate` / `--no-punctuate` / `--punctuate-model` /
  `--punctuate-keep-alive` override; runtime `{"cmd":"config","punctuate":false}` toggle.
- **No pre-warm** on `ping` (loading the LLM before transcription starves the ASR — see below).

### Tests

- New `voiced/test-punctuator.py`: 8 dependency-free guard tests (skeleton, empty/disabled
  passthrough, valid-edit accept, wording-change reject, dropped-char reject, error fall-back,
  `_clean`) + 1 live Ollama round-trip that skips if Ollama is down. All pass. `test-protocol.py`
  still passes.

## Key Findings

- **`qwen3:14b` punctuates faithfully** (`你好我今天想去台北車站搭高鐵` → `你好，我今天想去台北車站搭高鐵。`),
  doesn't rewrite, and at `think:false` returns in ~2–3 s warm. `qwen2.5vl:7b` punctuates equally
  well but is a 13–16 GB vision model.
- **GPU co-tenancy is load-bearing** (debugged from a live "no output" failure): a punctuation
  LLM resident in VRAM *during* transcription starves Whisper's `.generate()` and **wedges** it
  (all threads sleeping, no output). Root cause was an early `warm()` on `ping` that made the LLM
  resident before the first utterance. Fixes: (1) never pre-warm; (2) the model loads on demand
  after transcription. `qwen3:14b` (~9.8 GB) **co-fits** Breeze (~6.6 GB) — verified Breeze's
  `.generate()` runs to completion with ~7.6 GB free — so the default is `keep_alive: 5m` (stay
  resident, no reload). Heavier models use `--punctuate-keep-alive 0` (unload after each call).

## Decisions Made

- **Punctuation runs in the daemon, not the engine** (design decision 10) — the socket boundary
  stays the contract; the engine never changes; the LLM is swappable.
- **Default model `qwen3:14b`, `keep_alive: 5m`** — co-fits the GPU, fast, no wedge; verified.

### Tried and reverted: Mandarin→Taiwanese translation

A mid-session variant had the LLM also **translate** the Mandarin into written Taiwanese (台文),
since the user wanted Taiwanese output rather than Mandarin. Findings before reverting:
`qwen2.5vl:7b` translated poorly (kept Mandarin words, dropped punctuation, hallucinated
喜歡→知影); `qwen3:14b` was better (`汝有無食飯，按怎遮爾晚才來？`) but still only draft quality
(recurring 看→睇, leftover Mandarin). **The user judged the translation quality not good enough,
so it was reverted** — the post-processing step is now punctuation-only. A future direction would
be a model fine-tuned for 台文, or ASR that outputs Taiwanese directly, rather than LLM
translation after the fact.

## Status at End of Session

- Working: punctuation restoration on by default (qwen3:14b, `think:false`, `keep_alive:5m`);
  guards + GPU-contention fix verified; live round-trip + mock socket path add punctuation
  without altering words; deployed to the systemd service.
- Tests: `test-punctuator.py` (8 + live) + `test-protocol.py` pass.

## Next Steps

- **User to confirm live end-to-end**: dictate (Ctrl+Alt+0 → Space → speak → Space → Enter) and
  check punctuated Mandarin appears in the preedit. Mic→ASR path is unchanged from Phase A; raw
  transcript + punctuation are logged to the journal for diagnosis.
- Optional: a future Taiwanese-output path with a better-suited model (see above).

---

**Files Changed:**
- `sources/gcin-everywhere/voiced/gcin-voiced.py` — `Punctuator` class (Ollama `qwen3:14b`,
  `think:false`, `keep_alive:5m`, no pre-warm), wired into `_transcribe_worker` with
  raw-transcript logging, `config` toggle, CLI flags, docstring
- `sources/gcin-everywhere/voiced/test-punctuator.py` — new unit test (guards + optional live)
- `sources/gcin-everywhere/voiced/README.md` — punctuation section, GPU note, run/test/requires
- `proj_docs/gcin-everywhere/research/VOICE-INPUT-DESIGN.md` — design decision 10, protocol +
  status updates
