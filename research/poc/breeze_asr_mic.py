#!/usr/bin/env python3
"""
POC: press-to-talk Taiwanese dictation with MediaTek Breeze-ASR-26.

This is the voice-input-method prototype: speak Taigi into the mic, get
Mandarin Han characters back. It records from the default input device,
transcribes locally via 🤗 Transformers (NOT Ollama), and prints the text.

Flow (interactive):
    1. Model loads once at startup (~3 GB on first ever run).
    2. Press ENTER to start recording, press ENTER again to stop.
    3. The transcript (Mandarin Han characters) is printed.
    4. Repeat. Ctrl+C (or empty 'q') to quit.

Usage:
    python3 breeze_asr_mic.py                 # interactive press-to-talk
    python3 breeze_asr_mic.py --seconds 5     # fixed 5s capture per turn
    python3 breeze_asr_mic.py --list-devices  # show input devices and exit
    python3 breeze_asr_mic.py --device-index 3 --language chinese

Requires a microphone + PortAudio:  pip install sounddevice  (sudo apt install libportaudio2)
"""

import argparse
import sys
import threading
import time

MODEL_ID = "MediaTek-Research/Breeze-ASR-26"
TARGET_SR = 16000  # Whisper works at 16 kHz mono


def parse_args():
    p = argparse.ArgumentParser(description="Press-to-talk Taigi dictation (Breeze-ASR-26)")
    p.add_argument("--seconds", type=float, default=None,
                   help="fixed capture length per turn; default = press ENTER to start/stop")
    p.add_argument("--language", default="chinese", help="Whisper decode language hint")
    p.add_argument("--task", default="transcribe", choices=["transcribe", "translate"])
    p.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"],
                   help="model inference device")
    p.add_argument("--device-index", type=int, default=None,
                   help="audio input device index (see --list-devices)")
    p.add_argument("--list-devices", action="store_true",
                   help="list audio input devices and exit")
    return p.parse_args()


def list_devices():
    import sounddevice as sd
    print(sd.query_devices())


def record_fixed(seconds, device_index):
    """Record a fixed number of seconds; return float32 mono @ TARGET_SR."""
    import sounddevice as sd
    print(f"[*] Recording {seconds:.1f}s... speak now", file=sys.stderr)
    frames = sd.rec(int(seconds * TARGET_SR), samplerate=TARGET_SR,
                    channels=1, dtype="float32", device=device_index)
    sd.wait()
    return frames.reshape(-1)


def record_until_enter(device_index):
    """Record from ENTER press to ENTER press; return float32 mono @ TARGET_SR."""
    import sounddevice as sd
    import numpy as np
    chunks = []
    stop = threading.Event()

    def cb(indata, _frames, _t, status):
        if status:
            print(status, file=sys.stderr)
        chunks.append(indata.copy())

    input("    [ENTER] to start recording...")
    with sd.InputStream(samplerate=TARGET_SR, channels=1, dtype="float32",
                        device=device_index, callback=cb):
        print("[*] Recording... [ENTER] to stop", file=sys.stderr)
        # block until user hits ENTER again, on a side thread so the stream runs
        t = threading.Thread(target=lambda: (input(), stop.set()))
        t.daemon = True
        t.start()
        while not stop.is_set():
            time.sleep(0.05)
    if not chunks:
        return np.zeros(0, dtype="float32")
    return np.concatenate(chunks).reshape(-1)


def main():
    args = parse_args()

    try:
        import sounddevice  # noqa: F401
    except Exception as e:
        sys.exit(f"sounddevice unavailable ({e}). pip install sounddevice; "
                 f"sudo apt install libportaudio2")

    if args.list_devices:
        list_devices()
        return

    # Pick inference device.
    try:
        import torch
    except ImportError:
        sys.exit("Missing dependency: pip install torch")
    if args.device == "auto":
        dev = 0 if torch.cuda.is_available() else -1
    elif args.device == "cuda":
        dev = 0 if torch.cuda.is_available() else sys.exit("no CUDA device")
    else:
        dev = -1

    from transformers import pipeline
    print(f"[*] Loading {MODEL_ID} ({'cuda:0' if dev == 0 else 'cpu'})...", file=sys.stderr)
    asr = pipeline("automatic-speech-recognition", model=MODEL_ID,
                   device=dev, chunk_length_s=30)
    gen = {"language": args.language, "task": args.task}
    print("[*] Ready. Speak Taigi; you get Mandarin characters. Ctrl+C to quit.\n",
          file=sys.stderr)

    try:
        while True:
            if args.seconds:
                audio = record_fixed(args.seconds, args.device_index)
            else:
                audio = record_until_enter(args.device_index)
            if audio.size < TARGET_SR * 0.2:
                print("[!] Too short, skipping.\n", file=sys.stderr)
                continue
            t0 = time.time()
            text = asr(audio, generate_kwargs=gen)["text"].strip()
            print(f"[*] ({time.time() - t0:.1f}s)  ->  {text}\n", file=sys.stderr)
            print(text)  # transcript to stdout
    except KeyboardInterrupt:
        print("\n[*] Bye.", file=sys.stderr)


if __name__ == "__main__":
    main()
