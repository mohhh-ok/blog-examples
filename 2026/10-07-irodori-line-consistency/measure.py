"""生成音声の話者類似度と F0 を測る。RunPod 上で gen_lines.py の後に実行する (CPU で動く)。

実行:
    cd /workspace/Irodori-TTS && uv run --no-sync python /eval/measure.py

測り方は、以前 Fish Audio で 1 行ずつ合成して行の境目で声が別人に入れ替わったときの調査と同じ:
- resemblyzer (VoiceEncoder、256 次元の utterance embedding) のコサイン類似度
- (1) 各行の ref 比 (2) 同じ条件の行どうしのペア (3) run は 2.5 秒窓 / 1.0 秒ホップごとの ref 比と窓どうしのペア
- (4) F0: Praat の自己相関法 (parselmouth の to_pitch_ac、16kHz、0.016 秒刻み、floor 50Hz / ceiling 800Hz) の有声フレームの中央値。参照音声も同じ方法で測る
  (librosa.pyin は pod の numba 0.63.1 + numpy 2.2.6 で Segmentation fault になったため使わない)

出力: /eval/measure.json (行・窓ごとの生の値)
"""

import json
from itertools import combinations
from pathlib import Path

import librosa
import numpy as np
import parselmouth
from resemblyzer import VoiceEncoder, preprocess_wav

EVAL = Path("/eval")
OUT = EVAL / "out"
SR = 16000
WIN_S = 2.5
HOP_S = 1.0


F0_STEP_S = 0.016


def f0_track(y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(フレームの時刻, F0)。無声フレームは NaN。"""
    pitch = parselmouth.Sound(y.astype(np.float64), sampling_frequency=SR).to_pitch_ac(time_step=F0_STEP_S, pitch_floor=50.0, pitch_ceiling=800.0)
    f0 = pitch.selected_array["frequency"].astype(float)
    f0[f0 == 0] = np.nan
    return pitch.xs(), f0


def median(f0: np.ndarray) -> float | None:
    v = f0[~np.isnan(f0)]
    return round(float(np.median(v)), 1) if len(v) else None


def main() -> None:
    gen = [json.loads(line) for line in (EVAL / "gen.jsonl").read_text().splitlines()]
    voices = json.loads((EVAL / "refs.json").read_text())

    encoder = VoiceEncoder()
    ref_paths = {f"{v['voice']}-{q}": EVAL / "ref" / f"{v['voice']}-{q}.wav" for v in voices for q in ("clean", "quiet", "noisy")}

    refs = {}
    for key, path in ref_paths.items():
        refs[key] = {"embed": encoder.embed_utterance(preprocess_wav(path)), "f0": median(f0_track(librosa.load(path, sr=SR)[0])[1])}
    print("refs done", flush=True)

    lines = []
    for n, rec in enumerate(gen):
        path = OUT / f"{rec['voice']}-{rec['quality']}-{rec['mode']}-{rec['idx']}.wav"
        ref = refs[f"{rec['voice']}-{rec['quality']}"]
        wav = preprocess_wav(path)
        # 行は元の信号で F0 を測る。run は resemblyzer の前処理 (16kHz、無音除去) 後の信号で測り、窓と時刻を揃える
        times, f0 = f0_track(wav) if rec["mode"] == "run" else f0_track(librosa.load(path, sr=SR)[0])
        e = encoder.embed_utterance(wav)
        row = {k: rec[k] for k in ("voice", "quality", "mode", "idx", "text", "used_seed", "audio_s")}
        row |= {"ref_sim": round(float(np.dot(e, ref["embed"])), 4), "f0": median(f0), "embed": e}
        if rec["mode"] == "run":
            win, hop = int(WIN_S * SR), int(HOP_S * SR)
            windows = []
            for i, s in enumerate(range(0, max(len(wav) - win, 0) + 1, hop)):
                ew = encoder.embed_utterance(wav[s : s + win])
                wf0 = median(f0[(times >= s / SR) & (times < (s + win) / SR)])
                windows.append({"i": i, "start_s": round(s / SR, 2), "ref_sim": round(float(np.dot(ew, ref["embed"])), 4), "f0": wf0, "embed": ew})
            row["windows"] = windows
        lines.append(row)
        if n % 50 == 0:
            print(f"measured {n}/{len(gen)}", flush=True)

    conditions = {}
    for row in lines:
        key = f"{row['voice']}|{row['quality']}|{row['mode']}"
        conditions.setdefault(key, []).append(row)

    out = {"refs": {k: {"f0": v["f0"]} for k, v in refs.items()}, "conditions": {}}
    for key, rows in conditions.items():
        if rows[0]["mode"] == "run":
            units = [w for r in rows for w in r["windows"]]
        else:
            units = rows
        pair = [round(float(np.dot(a["embed"], b["embed"])), 4) for a, b in combinations(units, 2)]
        for r in rows:
            r.pop("embed")
            for w in r.get("windows", []):
                w.pop("embed")
        out["conditions"][key] = {"rows": rows, "pairwise": pair}
    (EVAL / "measure.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
