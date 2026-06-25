# Research: MediaTek Breeze 3 (Taiwanese ASR) for an Input Method

**Date:** 2026-06-24
**Status:** Research / feasibility note — no implementation
**Question studied:** MediaTek released "Breeze 3" which can recognize Taiwanese. Can we use it to build an input method, can it run on Ollama, and how would we use it?

---

## Navigation

**Project Docs:** [README](../README.md) | [SPEC](../SPEC.md) | [DESIGN](../DESIGN.md) | [IMPLEMENTATION-GUIDE](../IMPLEMENTATION-GUIDE.md) | [HANDOFF](../HANDOFF.md)

---

## TL;DR

- **"Breeze 3" is a *speech* series, not a chat/text LLM.** The "recognize Taiwanese" capability is **Breeze-ASR-26**, a Whisper-based speech-to-text (ASR) model. So the only relevant use for us is a **voice input method** (speak Taiwanese → text), which is a different interaction model from gcin-everywhere's keyboard phonetic/table engines.
- **It cannot run on Ollama.** Ollama has no audio-input path; it is built for text/vision LLMs via llama.cpp. Whisper-class ASR models run via **🤗 Transformers** or **whisper.cpp**, not Ollama. The "Whisper + Ollama" stacks online run Whisper *separately* and pipe text into Ollama.
- **Output is Mandarin Han characters** (中文漢字), *not* Tâi-lô/POJ romanization or Taiwanese orthography.
- **~30% Character Error Rate** on its own Taigi benchmark, and trained on *synthetic* speech — usable as draft/assist, not reliable dictation.
- **Verdict:** Not a fit for the current keyboard-IME scope. A plausible **Phase 3+ optional "press-to-talk Taiwanese dictation" mode** built on **whisper.cpp**, separate from the gtab/phonetic engines. Apache-2.0 license is permissive enough to ship.

---

## What "Breeze 3" actually is

Announced March 2026 by MediaTek Research (聯發創新基地). Unlike Breeze 1/2 (text LLMs), the **Breeze 3 series is focused on Taiwanese (台語 / Taigi) speech**:

| Model | Job | Architecture | Notes |
|-------|-----|--------------|-------|
| **Breeze-ASR-26** | Speech → text (ASR) | Fine-tuned **Whisper**, 2B params | Apache 2.0; on Hugging Face |
| **BreezyVoice 26** | Text → speech (TTS) | Based on CosyVoice 2 | Taiwanese voice synthesis |
| **Breeze Guard 26** | Content-safety filter | Built on Breeze 2 8B | Not relevant to an IME |

Only **Breeze-ASR-26** is relevant to an input method, and only as **voice input**.

### Breeze-ASR-26 details

- **Base:** OpenAI Whisper (large multilingual ASR pretrained on 680k hrs), fine-tuned on ~10,000 hrs of **synthetic** Taigi speech with diverse speakers/acoustics and Mandarin/Taigi/English code-switching.
- **Size:** 2B parameters, F32 tensors on HF.
- **Input:** Taiwanese Hokkien speech audio.
- **Output:** **Mandarin Chinese characters** — *not* native Taigi orthography or romanization.
- **Accuracy:** ~30.13% CER on the Taigi ASR benchmark (≈ 1 in 3 characters wrong).
- **License:** Apache 2.0.

---

## Can it run on Ollama?

**No.** Two independent reasons:

1. **Ollama has no audio-input endpoint.** It wraps llama.cpp for text/vision LLM generation; there is no path to feed microphone/wav audio to a Whisper ASR model. The unofficial `whisper` uploads on ollama.com do not actually transcribe through Ollama's API.
2. **The standard "Whisper + Ollama" recipes run Whisper *separately*** (whisper.cpp / faster-whisper) and feed the resulting *text* into Ollama. Ollama is only the LLM half of those stacks.

**Correct runtimes for Breeze-ASR-26:** 🤗 Transformers (official) or **whisper.cpp** (after GGML conversion — best fit for a native C/IBus integration).

> Note: the *Breeze 2 text LLM* (a different model) **does** run on Ollama — GGUF builds exist (e.g. `willqiu/Llama-Breeze2-8B-Instruct`, `ycchen/Breeze2-8B-TextOnly-...`). That would be the model to look at if we ever wanted a *text* task such as Tâi-lô-romanization → Han conversion. It is not an ASR model.

---

## How you'd use it

Official path (Transformers):

```python
from transformers import pipeline
pipe = pipeline("automatic-speech-recognition",
                model="MediaTek-Research/Breeze-ASR-26")
text = pipe("taigi_audio.wav")["text"]   # → Mandarin Han characters
```

For a native, dependency-light integration matching this project's philosophy: convert weights to GGML and call **whisper.cpp**, exposed as an optional press-to-talk dictation mode.

**Working POC:** [`poc/breeze_asr_transcribe.py`](poc/breeze_asr_transcribe.py) transcribes a WAV/MP3 file via Transformers (16 kHz mono, 30 s chunking, CPU or CUDA). See [`poc/README.md`](poc/README.md) for setup.

**Design proposal:** [VOICE-INPUT-DESIGN.md](VOICE-INPUT-DESIGN.md) — full architecture for adding voice dictation to `gcin-everywhere` (separate `gcin-voiced` ASR daemon, Unix-socket protocol, Ctrl+Alt+0 voice mode, push-to-talk, review-before-commit).

---

## Implications for gcin-everywhere

1. **It's voice, not keyboard.** Integrating it adds a mic-capture + audio subsystem — a new component, not an extension of the existing gtab/phonetic engines.
2. **Output is Mandarin Han characters**, which is actually convenient for a Traditional Chinese IME, but means it is not a "Taiwanese script" tool.
3. **~30% CER + synthetic training data** → draft/assist quality, not reliable dictation. Set user expectations accordingly.

### Recommendation

- **Current scope (keyboard IME):** Breeze-ASR-26 does not fit. No action.
- **Future (Phase 3+):** A plausible **optional "press-to-talk Taiwanese dictation" mode** via **whisper.cpp**, completely separate from the gtab engines, gated behind a feature flag. Apache-2.0 makes shipping feasible. Treat as an experiment with explicit accuracy caveats.

---

## Sources

- [MediaTek unveils Breeze 3 series (mashdigi)](https://en.mashdigi.com/mediatek-innovation-center-unveils-breeze-3-series-models-enabling-ai-to-understand-taiwanese-speak-authentic-taiwanese-accents-and-even-present-mandarin-and-taiwanese-scenarios/)
- [Breeze-ASR-26 · Hugging Face](https://huggingface.co/MediaTek-Research/Breeze-ASR-26)
- [MediaTek Research Breeze 3 blog (zh-TW)](https://www.mediatek.com/zh-tw/tek-talk-blogs/mediatek-research-breeze-3)
- [Breeze models on Ollama](https://ollama.com/search?q=breeze)
- [Build a Local Voice Assistant with Whisper + Ollama (2026)](https://www.aimadetools.com/blog/local-voice-assistant-whisper-ollama/)
- [mtkresearch/MR-Models (GitHub)](https://github.com/mtkresearch/MR-Models)
