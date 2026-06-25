#!/usr/bin/env python3
"""
POC: transcribe a WAV or MP3 file with MediaTek Breeze-ASR-26.

Breeze-ASR-26 is a Whisper-large-v2 model fine-tuned on Taiwanese (Taigi)
Hokkien speech. It transcribes spoken Taigi/Mandarin/English (incl. code-switching)
and outputs **Mandarin Han characters** (not Tâi-lô/POJ romanization).

This runs the model locally via 🤗 Transformers — NOT Ollama (Ollama has no
audio-input path; see ../breeze3-taiwanese-asr.md).

Usage:
    python3 breeze_asr_transcribe.py path/to/audio.wav
    python3 breeze_asr_transcribe.py path/to/audio.mp3 --language chinese
    python3 breeze_asr_transcribe.py clip.wav --timestamps --device cuda

First run downloads ~3 GB of weights from Hugging Face into ~/.cache/huggingface.
"""

import argparse
import sys
import time

MODEL_ID = "MediaTek-Research/Breeze-ASR-26"
TARGET_SR = 16000  # Whisper always works at 16 kHz mono


def parse_args():
    p = argparse.ArgumentParser(description="Transcribe WAV/MP3 with Breeze-ASR-26")
    p.add_argument("audio", help="path to a .wav or .mp3 file")
    p.add_argument("--language", default="chinese",
                   help="decode language hint passed to Whisper (default: chinese)")
    p.add_argument("--task", default="transcribe", choices=["transcribe", "translate"],
                   help="transcribe (same language) or translate (to English)")
    p.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"],
                   help="inference device (default: auto-detect)")
    p.add_argument("--chunk-length", type=int, default=30,
                   help="chunk size in seconds for long audio (default: 30)")
    p.add_argument("--timestamps", action="store_true",
                   help="print per-segment timestamps as well as the full text")
    return p.parse_args()


def load_audio(path):
    """Load wav/mp3 as a 16 kHz mono float32 numpy array."""
    try:
        import librosa
    except ImportError:
        sys.exit("Missing dependency: pip install librosa soundfile")
    # librosa resamples to TARGET_SR and downmixes to mono; handles wav + mp3
    # (mp3 via libsndfile>=1.1 or the audioread/ffmpeg fallback).
    audio, _ = librosa.load(path, sr=TARGET_SR, mono=True)
    return audio


def pick_device(choice):
    try:
        import torch
    except ImportError:
        sys.exit("Missing dependency: pip install torch")
    if choice == "auto":
        return 0 if torch.cuda.is_available() else -1
    if choice == "cuda":
        if not torch.cuda.is_available():
            sys.exit("--device cuda requested but no CUDA device is available")
        return 0
    return -1  # cpu


def main():
    args = parse_args()

    try:
        from transformers import pipeline
    except ImportError:
        sys.exit("Missing dependency: pip install transformers")

    print(f"[*] Loading audio: {args.audio}", file=sys.stderr)
    audio = load_audio(args.audio)
    duration = len(audio) / TARGET_SR
    print(f"[*] Audio length: {duration:.1f}s @ {TARGET_SR} Hz mono", file=sys.stderr)

    device = pick_device(args.device)
    dev_name = "cuda:0" if device == 0 else "cpu"
    print(f"[*] Loading model {MODEL_ID} on {dev_name} "
          f"(first run downloads ~3 GB)...", file=sys.stderr)

    asr = pipeline(
        "automatic-speech-recognition",
        model=MODEL_ID,
        device=device,
        chunk_length_s=args.chunk_length,   # enables >30s audio via sliding window
    )

    print("[*] Transcribing...", file=sys.stderr)
    t0 = time.time()
    result = asr(
        audio,
        return_timestamps=args.timestamps,
        generate_kwargs={"language": args.language, "task": args.task},
    )
    elapsed = time.time() - t0
    rtf = elapsed / duration if duration else float("nan")
    print(f"[*] Done in {elapsed:.1f}s (RTF {rtf:.2f})\n", file=sys.stderr)

    # Full transcript to stdout (so it can be piped/redirected cleanly).
    print(result["text"].strip())

    if args.timestamps and result.get("chunks"):
        print("\n--- segments ---", file=sys.stderr)
        for c in result["chunks"]:
            start, end = c["timestamp"]
            start = 0.0 if start is None else start
            end = duration if end is None else end
            print(f"[{start:6.2f} -> {end:6.2f}] {c['text'].strip()}", file=sys.stderr)


if __name__ == "__main__":
    main()
