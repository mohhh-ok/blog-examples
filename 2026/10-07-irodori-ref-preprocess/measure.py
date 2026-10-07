"""生成音声と参照音声の長さ・RMS (dBFS) を測り、results/measurements.json と results/report.md を書く。
usage: python measure.py <生成 wav のディレクトリ> <参照 wav のディレクトリ> <結果ディレクトリ>
生成 wav は <文>-<参照>-s<seed>.wav (第2〜5弾) と <文>-s<seed>.wav (第1弾)。予測長は結果ディレクトリの gen.json / gen-words.json から読む。
"""
import json
import math
import sys
import wave
from pathlib import Path

import numpy as np

# 記事の条件名と参照ファイル名
CONDS = {"R10": "r10", "A": "r26", "B": "r26t15", "C": "r26pipe", "D": "r26pipe2x", "E": "r26t1287", "F": "r26long-pipe"}
REF_NOTE = {
    "R10": ("別録音の本人の声", "なし"),
    "A": ("R26 そのまま", "なし"),
    "B": ("R26 の先頭 15 秒", "なし"),
    "C": ("R26 の先頭 15 秒", "あり"),
    "D": ("C を 2 回つないだもの", "あり"),
    "E": ("R26 の先頭 12.87 秒", "なし"),
    "F": ("R26 の先頭 18 秒", "あり"),
}
PAD_S = {"C": 0.5, "D": 0.5, "F": 0.5}  # 下処理で末尾に足した無音
THRESHOLD_DB = -60.0


def read(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path)) as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if sw == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    elif sw == 4:
        x = np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"sampwidth {sw}")
    return x.reshape(-1, ch).mean(axis=1), sr


def db(x: np.ndarray) -> float | None:
    r = math.sqrt(float(np.mean(x**2))) if len(x) else 0.0
    return round(20 * math.log10(r), 1) if r > 0 else None


def quietest(x: np.ndarray, sr: int, win_s: float = 0.2) -> float | None:
    """先頭から 0.2 秒ずつ区切った区間のうち、最も静かな区間の RMS。"""
    win = int(win_s * sr)
    vals = [db(x[i:i + win]) for i in range(0, len(x) - win + 1, win)]
    vals = [v for v in vals if v is not None]
    return min(vals) if vals else None


def predicted(messages: list[str]) -> float | None:
    for m in messages:
        if "predicted duration" in m:
            return float(m.split("(")[-1].rstrip(").").rstrip("s"))
    return None


def fmt(v: float | None) -> str:
    return "-inf" if v is None else f"{v}"


def main() -> None:
    wav_dir, ref_dir, res = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    gen = {f"{r['id']}-{r['ref']}-s{r['seed']}": r for r in json.loads((res / "gen.json").read_text())}
    words = {f"{r['id']}-s{r['seed']}": r for r in json.loads((res / "gen-words.json").read_text())}
    ref_name = {v: k for k, v in CONDS.items()}

    rows = []
    for name, r in list(gen.items()) + list(words.items()):
        x, sr = read(wav_dir / f"{name}.wav")
        rows.append({
            "file": name, "round": "words" if name in words else "short", "cond": ref_name.get(r.get("ref"), "R10"),
            "id": r["id"], "seed": r["seed"], "text": r["text"],
            "seconds": round(len(x) / sr, 2), "predicted_s": predicted(r["messages"]),
            "head_0_2s_db": db(x[: int(0.2 * sr)]), "tail_0_4s_db": db(x[-int(0.4 * sr):]), "overall_db": db(x),
        })
    refs = []
    for cond, fname in CONDS.items():
        x, sr = read(ref_dir / f"{fname}.wav")
        if cond == "D":  # C を 2 回つないだだけなので、1 回分 (= C) で測る
            x1 = x[: len(x) // 2]
        else:
            x1 = x
        body = x1[: len(x1) - int(PAD_S.get(cond, 0) * sr)]
        refs.append({"cond": cond, "file": fname, "seconds": round(len(x) / sr, 2), "sample_rate": sr,
                     "quietest_0_2s_db_without_pad": quietest(body, sr), "overall_db": db(x)})
    (res / "measurements.json").write_text(json.dumps({"outputs": rows, "refs": refs}, ensure_ascii=False, indent=2) + "\n")

    short = [r for r in rows if r["round"] == "short"]
    L = ["# 測定結果", "", "RMS は dBFS (0 dB = フルスケール)。生成音声は 48kHz mono。", "",
         "## 参照音声", "",
         "| 条件 | 中身 | 下処理 | 長さ (秒) | サンプルレート | 最も静かな 0.2 秒の RMS (dB、末尾 pad を除く) |", "|---|---|---|---|---|---|"]
    for r in refs:
        what, pre = REF_NOTE[r["cond"]]
        L.append(f"| {r['cond']} | {what} | {pre} | {r['seconds']} | {r['sample_rate']} | {fmt(r['quietest_0_2s_db_without_pad'])} |")
    L += ["", f"## まとめ (先頭 0.2 秒の RMS が {THRESHOLD_DB:.0f} dB より大きい本数)", "",
          "| 条件 | 本数 | 先頭の範囲 (dB) | 超えたファイル |", "|---|---|---|---|"]
    for cond in CONDS:
        sub = [r for r in short if r["cond"] == cond]
        hit = [r for r in sub if r["head_0_2s_db"] is not None and r["head_0_2s_db"] > THRESHOLD_DB]
        heads = [r["head_0_2s_db"] for r in sub]
        names = "全部" if len(hit) == len(sub) else ", ".join(f"{r['id']} s{r['seed']}" for r in hit) or "なし"
        L.append(f"| {cond} | {len(hit)} / {len(sub)} | {min(heads)}〜{max(heads)} | {names} |")
    L += ["", "## 各音声 (第2〜5弾)", "",
          "| 条件 | 文 | 入力 | seed | 長さ (秒) | 予測長 (秒) | 先頭 0.2 秒 (dB) | 末尾 0.4 秒 (dB) | 全体 (dB) |", "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(short, key=lambda r: (list(CONDS).index(r["cond"]), r["id"], r["seed"])):
        L.append(f"| {r['cond']} | {r['id']} | {r['text']} | {r['seed']} | {r['seconds']:.2f} | {r['predicted_s']:.2f} | {fmt(r['head_0_2s_db'])} | {fmt(r['tail_0_4s_db'])} | {fmt(r['overall_db'])} |")
    L += ["", "## 第1弾 (参照 R10、清水寺・鹿苑寺)", "",
          "| 文 | 入力 | seed | 長さ (秒) | 先頭 0.2 秒 (dB) | 末尾 0.4 秒 (dB) |", "|---|---|---|---|---|---|"]
    for r in [r for r in rows if r["round"] == "words"]:
        L.append(f"| {r['id']} | {r['text']} | {r['seed']} | {r['seconds']:.2f} | {fmt(r['head_0_2s_db'])} | {fmt(r['tail_0_4s_db'])} |")
    (res / "report.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
