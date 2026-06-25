# Breeze-ASR-26 POC — Taiwanese speech → text

Minimal proof-of-concept that transcribes a **WAV or MP3** file with
[MediaTek Breeze-ASR-26](https://huggingface.co/MediaTek-Research/Breeze-ASR-26)
(Whisper-large-v2 fine-tuned on Taiwanese Hokkien). Runs locally via 🤗 Transformers
— **not Ollama** (see [../breeze3-taiwanese-asr.md](../breeze3-taiwanese-asr.md) for why).

Output is **Mandarin Han characters**, not Tâi-lô/POJ romanization.

## Setup

```bash
cd proj_docs/gcin-everywhere/research/poc
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

## Run

### File transcription — `breeze_asr_transcribe.py`

```bash
python3 breeze_asr_transcribe.py sample.wav
python3 breeze_asr_transcribe.py sample.mp3 --language chinese
python3 breeze_asr_transcribe.py clip.wav --timestamps --device cuda
```

### Live press-to-talk dictation — `breeze_asr_mic.py`

The voice-input-method prototype: speak Taigi into the mic, get Mandarin characters.

```bash
python3 breeze_asr_mic.py --list-devices        # find your mic's index
python3 breeze_asr_mic.py --device-index 4       # press ENTER to start/stop
python3 breeze_asr_mic.py --seconds 5            # fixed 5s capture per turn
```

Needs a microphone + PortAudio (`sudo apt install libportaudio2`, `pip install sounddevice`).
The transcript goes to stdout; prompts/timing go to stderr. Ctrl+C to quit.

- First run downloads ~3 GB of weights to `~/.cache/huggingface`.
- The transcript is printed to **stdout**; progress + timestamps go to **stderr**,
  so `... > out.txt` captures just the text.
- Long files are handled automatically via 30 s chunking (`--chunk-length`).
- CPU works (slow, RTF ~1–3×); add a CUDA `torch` build for speed.

## Verified run (2026-06-24)

Confirmed working end-to-end on an RTX 3090. Test audio: 3 clips from the open
[`TaigiSpeech/TaigiSpeech`](https://huggingface.co/datasets/TaigiSpeech/TaigiSpeech)
test split (real Taigi speech, all labeled intent `SOS_CALL`; the dataset ships
intent labels, not reference transcripts, so this shows transcription quality, not CER).
First run downloaded ~3 GB; inference ran at **RTF ≈ 0.30** (5 s audio → 1.5 s).

| clip | Breeze-ASR-26 output (Mandarin Han) |
|------|--------------------------------------|
| taigi_0 | 救命啊 快來救我 幫忙喔 失火了 |
| taigi_1 | 喂 快來 我老公昏倒了 有誰要來幫我 |
| taigi_2 | 警察 遭小偷 誰要來幫我 快點 快點去叫警察 |

Robustness across **distinct intents** (shuffled test split) — each transcript
matches its intent label:

| intent label | Breeze-ASR-26 output |
|--------------|----------------------|
| BREATHING_CHEST_EMERG | 慘了 胸口悶悶的 頭還很暈 快幫我叫救護車 |
| PAIN_GENERAL | 媽媽 我的眼睛好痛 快來幫我 |
| LIGHT_ON | 請麻煩幫我開一下燈 |
| FALL_HELP | 我跌倒撞到頭 好痛 現在爬不起來 |

**Long-audio / chunking:** a 42 s concatenation transcribed coherently end-to-end
at RTF 0.11 (`chunk_length_s=30` sliding window), confirming the long-form path works.

All outputs are coherent Mandarin consistent with the spoken content — the model
transcribes spoken Taigi into Mandarin characters as documented.

To reproduce the test clips (needs `datasets` + `torchcodec`, also in requirements):
```python
import soundfile as sf
from datasets import load_dataset
ds = load_dataset("TaigiSpeech/TaigiSpeech", split="test", streaming=True)
for n, row in enumerate(ds):
    if n >= 3: break
    a = row["audio"]
    sf.write(f"taigi_{n}_{row['intent']}.wav", a["array"], a["sampling_rate"])
```

## Notes / caveats

- **Accuracy:** ~30% CER on the Taigi benchmark + synthetic training data → treat
  as draft/assist quality, not reliable dictation.
- **mp3:** decoded by librosa via `soundfile` (libsndfile ≥ 1.1) or an
  `audioread`/ffmpeg fallback. If mp3 loading fails, `sudo apt install ffmpeg`.
- This is a standalone experiment — it does **not** touch the gtab/IBus engines.
  A native integration would convert the weights to GGML and call whisper.cpp.
