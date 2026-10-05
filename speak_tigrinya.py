"""Narrates a Tigrinya text file (speech_ti.txt) and writes speech_ti.mp3 + speech_ti.srt + speech_ti.clean.txt.

  python speak_tigrinya.py --dry-run                 only clean the text and show the sentences (nothing is spoken)
  python speak_tigrinya.py --engine mms              Meta MMS Tigrinya voice (free, robotic, NON-COMMERCIAL licence)
  python speak_tigrinya.py --engine mms --lower 3    same, pitch lowered by 3 semitones (to sound deeper / more male)
  python speak_tigrinya.py --engine amharic          EXPERIMENT: Amharic male voice reading Tigrinya letters (often mispronounced)

Engines are listed honestly: no free Tigrinya voice with a selectable gender exists.
"""
import argparse, asyncio, os, re, subprocess, sys, textwrap, wave
import numpy as np

LIMIT = 150   # longest chunk sent to the voice (also keeps subtitles short)

def clean(raw):
    t = raw.replace("\ufeff", "")
    t = re.sub(r"\*+", "", t)                       # stray markdown asterisks
    t = re.sub(r"\.{2,}|…", " ", t)                 # ellipses left by broken text
    t = re.sub(r"[—–]+", "፣ ", t)                  # dashes become a short pause
    t = re.sub(r"\s+", " ", t)                      # join lines that were broken mid-sentence
    t = re.sub(r"\s+([።፣፤፧.!?,;])", r"\1", t)
    return t.strip()

def chunks(text, limit=LIMIT):
    out = []
    for s in re.split(r"(?<=[።፧!?.])\s+", text):
        s = s.strip()
        while len(s) > limit:
            cut = max(s.rfind(c, 0, limit) for c in "፣፤,;")
            if cut < 60: cut = s.rfind(" ", 0, limit)
            if cut <= 0: cut = limit
            out.append(s[:cut + 1].strip()); s = s[cut + 1:].strip()
        if s: out.append(s)
    return out

def warnings(text, sents):
    w = []
    if re.search(r"[A-Za-z]", text): w.append("Latin letters found (the voice may skip or mispronounce them): " + ", ".join(sorted(set(re.findall(r"[A-Za-z][A-Za-z'’-]*", text)))[:8]))
    if not re.search(r"[።]", text): w.append("no Ge'ez full stop (።) in the text: sentences were split at '.', '?' and by length, so pauses may fall in odd places")
    if any(len(s) < 12 for s in sents): w.append("some very short fragments (probably broken lines): check the .clean.txt file")
    return w

def read_wav(path):
    with wave.open(path, "rb") as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    return (a.reshape(-1, ch).mean(axis=1) if ch > 1 else a), sr

def synth_mms(sents):
    import torch
    from transformers import AutoTokenizer, VitsModel
    name = "facebook/mms-tts-tir"
    tok, model = AutoTokenizer.from_pretrained(name), VitsModel.from_pretrained(name); model.eval()
    uro = None
    if getattr(tok, "is_uroman", False):               # some MMS voices want romanised input
        try: import uroman as ur; uro = ur.Uroman()
        except ImportError: sys.exit("This voice needs the 'uroman' package: pip install uroman")
    waves = []
    for s in sents:
        inp = tok(uro.romanize_string(s) if uro else s, return_tensors="pt")
        if inp["input_ids"].shape[1] == 0: waves.append(np.zeros(0, dtype=np.float32)); continue
        with torch.no_grad(): waves.append(model(**inp).waveform[0].numpy())
    return waves, int(model.config.sampling_rate)

def synth_amharic(sents, voice="am-ET-AmehaNeural"):
    import edge_tts
    waves, sr = [], 24000
    for i, s in enumerate(sents):
        mp3, wav = f"_tmp{i}.mp3", f"_tmp{i}.wav"
        for attempt in range(4):
            try: asyncio.run(edge_tts.Communicate(s, voice).save(mp3)); break
            except Exception as e: print("retry:", e); asyncio.run(asyncio.sleep(2 * (attempt + 1)))
        else: sys.exit("speech failed for: " + s[:40])
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ar", str(sr), "-ac", "1", wav], check=True)
        waves.append(read_wav(wav)[0]); os.remove(mp3); os.remove(wav)
    return waves, sr

def synth_test(sents):   # tones, only to test the pipeline offline
    sr = 16000
    return [(0.2 * np.sin(2 * np.pi * 220 * np.arange(int(sr * max(0.5, len(s) / 14))) / sr)).astype(np.float32) for s in sents], sr

def stamp(t):
    ms = int(round(t * 1000)); return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"

def write_srt(path, timing):
    cues, n = [], 1
    for s, a, b in timing:
        pieces = textwrap.wrap(s, 84) or [s]; tot = sum(len(p) for p in pieces); t = a
        for p in pieces:
            e = t + (b - a) * len(p) / tot
            cues.append(f"{n}\n{stamp(t)} --> {stamp(e)}\n{textwrap.fill(p, 42)}\n"); n += 1; t = e
    open(path, "w", encoding="utf-8").write("\n".join(cues))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["mms", "amharic", "test"], default="mms")
    ap.add_argument("--lower", type=float, default=0, help="lower the pitch by this many semitones (try 2 to 4)")
    ap.add_argument("--pause", type=float, default=0.6, help="seconds of silence after each sentence")
    ap.add_argument("--input", default="speech_ti.txt")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    text = clean(open(a.input, encoding="utf-8").read())
    sents = chunks(text)
    open("speech_ti.clean.txt", "w", encoding="utf-8").write("\n".join(sents) + "\n")
    print(f"{len(sents)} sentences, {len(text)} characters")
    for w in warnings(text, sents): print("WARNING:", w)
    if a.dry_run: [print(f"{i+1:3}. {s}") for i, s in enumerate(sents)]; sys.exit(0)

    waves, sr = {"mms": synth_mms, "amharic": synth_amharic, "test": synth_test}[a.engine](sents)
    gap = np.zeros(int(sr * a.pause), dtype=np.float32); parts, timing, cur = [], [], 0.0
    for s, w in zip(sents, waves):
        timing.append((s, cur, cur + len(w) / sr)); parts += [w, gap]; cur += len(w) / sr + a.pause
    audio = np.concatenate(parts[:-1]); audio = audio / max(1e-9, float(np.abs(audio).max())) * 0.9
    with wave.open("speech_ti.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((audio * 32767).astype(np.int16).tobytes())
    af = []
    if a.lower:   # deeper voice: drop the pitch, then restore the speed so timings stay valid
        f = 2 ** (-a.lower / 12); af = ["-af", f"asetrate={int(sr * f)},aresample={sr},atempo={1 / f:.5f}"]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "speech_ti.wav", *af, "-codec:a", "libmp3lame", "-q:a", "3", "speech_ti.mp3"], check=True)
    write_srt("speech_ti.srt", timing)
    print(f"Wrote speech_ti.mp3 ({cur/60:.1f} min), speech_ti.srt, speech_ti.clean.txt")
