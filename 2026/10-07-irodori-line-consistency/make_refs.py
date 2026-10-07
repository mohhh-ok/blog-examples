"""JVS から話者 10 人を選び、参照音声 3 条件 (clean / quiet / noisy) を作る。ローカルで実行する。

使い方:
  uv run --with numpy python -I make_refs.py <jvs_ver1 のディレクトリ> <出力ディレクトリ> <mo の R10 ref.wav>

話者の選び方: jvs_ver1/gender_f0range.txt の (minf0, maxf0) の幾何平均を声の高さとし、
男女それぞれで高さ順に並べて 0, 1/4, 1/2, 3/4, 1 の位置の話者を取る (同じ位置に当たったら次の話者)。

clean: nonpara30 ではなく parallel100 の発話を番号順に連結し、CLEAN_MIN_SECONDS を超えた発話で止める (無加工、発話の途中では切らない)
quiet: clean を QUIET_DB 下げる
noisy: clean に白色ノイズ (seed 固定) を足し、最も静かな 0.2 秒 (0.05 秒刻み) の RMS を NOISY_FLOOR_DB にする

出力: <出力>/<voice>-<quality>.wav (pcm_s16le、元のサンプルレート) と <出力>/refs.json
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import texts  # noqa: E402

WIN_S = 0.2
HOP_S = 0.05


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    sr = int(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate", "-of", "csv=p=0", str(path)]
        ).strip()
    )
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-f", "f32le", "-"])
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64), sr


def write_wav(path: Path, x: np.ndarray, sr: int) -> None:
    pcm = np.clip(np.round(x * 32767.0), -32768, 32767).astype("<i2")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(sr), "-ac", "1", "-i", "-", "-c:a", "pcm_s16le", str(path)],
        input=pcm.tobytes(),
        check=True,
    )


def db(v: float) -> float:
    return round(20 * np.log10(max(v, 1e-12)), 2)


def window_rms(x: np.ndarray, sr: int) -> np.ndarray:
    win, hop = int(WIN_S * sr), int(HOP_S * sr)
    return np.array([np.sqrt(np.mean(x[i : i + win] ** 2)) for i in range(0, len(x) - win + 1, hop)])


def stats(x: np.ndarray, sr: int) -> dict:
    w = window_rms(x, sr)
    return {
        "seconds": round(len(x) / sr, 3),
        "sample_rate": sr,
        "peak_db": db(float(np.max(np.abs(x)))),
        "rms_db": db(float(np.sqrt(np.mean(x**2)))),
        "quietest_0.2s_rms_db": db(float(w.min())),
    }


def pick_speakers(jvs: Path) -> list[dict]:
    rows = []
    for line in (jvs / "gender_f0range.txt").read_text().splitlines():
        parts = line.split()
        if len(parts) != 4 or not parts[0].startswith("jvs"):
            continue
        spk, gender, lo, hi = parts[0], parts[1], float(parts[2]), float(parts[3])
        rows.append({"id": spk, "gender": gender, "minf0": lo, "maxf0": hi, "f0_center": round(float(np.sqrt(lo * hi)), 1)})
    picked = []
    for gender in ("F", "M"):
        group = sorted((r for r in rows if r["gender"].upper().startswith(gender)), key=lambda r: (r["f0_center"], r["id"]))
        taken: set[int] = set()
        for q in (0.0, 0.25, 0.5, 0.75, 1.0):
            i = round(q * (len(group) - 1))
            while i in taken:
                i += 1
            taken.add(i)
            picked.append({**group[i], "rank_in_gender": f"{i + 1}/{len(group)}"})
    return picked


def build_clean(jvs: Path, spk: str) -> tuple[np.ndarray, int, list[str]]:
    wav_dir = jvs / spk / "parallel100" / "wav24kHz16bit"
    parts, used, sr0, total = [], [], None, 0.0
    for wav in sorted(wav_dir.glob("*.wav")):
        x, sr = read_wav(wav)
        if sr0 is None:
            sr0 = sr
        assert sr == sr0, (wav, sr, sr0)
        parts.append(x)
        used.append(wav.stem)
        total += len(x) / sr
        if total >= texts.CLEAN_MIN_SECONDS:
            break
    return np.concatenate(parts), sr0, used


def add_noise(x: np.ndarray, sr: int, seed: int) -> tuple[np.ndarray, float]:
    noise = np.random.default_rng(seed).standard_normal(len(x))
    target = 10 ** (texts.NOISY_FLOOR_DB / 20)
    lo, hi = 0.0, 1.0
    for _ in range(60):  # 最も静かな窓の RMS が target になるノイズの振幅を二分探索
        mid = (lo + hi) / 2
        if window_rms(x + mid * noise, sr).min() < target:
            lo = mid
        else:
            hi = mid
    g = (lo + hi) / 2
    return x + g * noise, db(g)


def main() -> None:
    jvs, out, mo_ref = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    voices = []
    sources = [(s["id"], s) for s in pick_speakers(jvs)] + [("mo", {"id": "mo", "note": "リポジトリ所有者 (mo) の R10 (08-26 記事の ref.wav)"})]
    for n, (vid, meta) in enumerate(sources):
        if vid == "mo":
            clean, sr = read_wav(mo_ref)
            used = [str(mo_ref)]
        else:
            clean, sr, used = build_clean(jvs, vid)
        quiet = clean * 10 ** (texts.QUIET_DB / 20)
        noisy, noise_db = add_noise(clean, sr, seed=1000 + n)
        refs = {}
        for q, x in (("clean", clean), ("quiet", quiet), ("noisy", noisy)):
            write_wav(out / f"{vid}-{q}.wav", x, sr)
            y, _ = read_wav(out / f"{vid}-{q}.wav")  # 16bit に量子化した後の実物で測る
            refs[q] = stats(y, sr)
        refs["noisy"]["noise_rms_db"] = noise_db
        voices.append({**meta, "voice": vid, "source_utterances": used, "refs": refs})
        print(vid, json.dumps(refs), flush=True)
    (out / "refs.json").write_text(json.dumps(voices, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
