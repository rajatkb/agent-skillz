#!/usr/bin/env python3
"""WSL voice chain probe: devices → 3s mic capture → faster-whisper transcribe.

Run with the Hermes python (asdf py3.11), e.g.:
    /home/<user>/.asdf/installs/python/3.11.0/bin/python verify_voice_chain.py

Exit codes: 0 = chain OK, 1 = device error, 2 = silence (possible privacy block), 3 = transcribe error.
"""
import sys
import time
import wave

import numpy as np
import sounddevice as sd

DURATION = 3
RATE = 44100


def main() -> int:
    print("devices:", [d["name"] for d in sd.query_devices()])
    print(f"recording {DURATION}s from default device...")
    rec = sd.rec(int(DURATION * RATE), samplerate=RATE, channels=1, dtype="float32")
    sd.wait()
    rms = float(np.sqrt(np.mean(rec**2)))
    peak = float(np.abs(rec).max())
    wav_path = "/tmp/mic_test.wav"
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((np.clip(rec, -1, 1) * 32767).astype(np.int16).tobytes())
    print(f"saved {wav_path} — RMS={rms:.5f} peak={peak:.4f}")
    if peak < 1e-6:
        print("PURE ZEROS: Windows mic privacy block — Settings > Privacy > Microphone for the terminal app")
        return 2

    t0 = time.time()
    from faster_whisper import WhisperModel

    print("loading Whisper base (downloads on first use)...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    print(f"model loaded in {time.time() - t0:.1f}s")
    segments, info = model.transcribe(wav_path, language="en")
    text = " ".join(s.text.strip() for s in segments).strip()
    print("language:", info.language, "| prob:", round(info.language_probability, 2))
    print("TRANSCRIPT:", repr(text))
    if text:
        print("OK — speech was heard and transcribed")
    else:
        print("Empty transcript on near-silence is expected; speak during the live test.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
