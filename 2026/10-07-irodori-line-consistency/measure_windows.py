"""3 方式を同じ単位 (2.5 秒窓) で比べる。ローカルの CPU で実行する。

measure.py は per-line を 1 行まるごと、run を 2.5 秒窓で測っており、測る長さが違う。ここでは方式によらず、
条件ごとに音声を resemblyzer の前処理 (16kHz、無音除去) にかけてから順につなぎ、2.5 秒窓 / 1.0 秒ホップで
ref 比と窓どうしのペア類似度を出す。per-line は 10 行、run は r1・r2 をつなぐので、行の境目をまたぐ窓も入る。
参照の埋め込みも同じ環境で計算し直す (pod の GPU の値と混ぜない)。

使い方 (resemblyzer は 08-26 記事の .venv のものを使う):
  ../08-26-fish-voice-clone-consistency/.venv/bin/python -I measure_windows.py <回収したディレクトリ>
出力: results/windows.json
"""

import json
import statistics as st
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

sys.path.insert(0, str(Path(__file__).parent))
import texts  # noqa: E402

SR = 16000
WIN_S = 2.5
HOP_S = 1.0
LOW = 0.75


def main() -> None:
    src = Path(sys.argv[1])
    voices = [v["voice"] for v in json.loads((src / "refs.json").read_text())]
    encoder = VoiceEncoder(device="cpu")
    win, hop = int(WIN_S * SR), int(HOP_S * SR)
    out = {}
    for v in voices:
        for q in texts.QUALITIES:
            ref = encoder.embed_utterance(preprocess_wav(src / "ref" / f"{v}-{q}.wav"))
            for m in texts.MODES:
                idxs = [f"r{i + 1}" for i in range(len(texts.RUNS))] if m == "run" else [f"{i + 1:02d}" for i in range(len(texts.LINES))]
                wav = np.concatenate([preprocess_wav(src / "out" / f"{v}-{q}-{m}-{i}.wav") for i in idxs])
                embeds = [encoder.embed_utterance(wav[s : s + win]) for s in range(0, len(wav) - win + 1, hop)]
                sims = [round(float(np.dot(e, ref)), 4) for e in embeds]
                pair = [float(np.dot(a, b)) for a, b in combinations(embeds, 2)]
                out[f"{v}|{q}|{m}"] = {
                    "voice": v, "quality": q, "mode": m,
                    "seconds_after_vad": round(len(wav) / SR, 2),
                    "n_windows": len(sims),
                    "ref_mean": round(st.mean(sims), 4),
                    "ref_std": round(st.pstdev(sims), 4),
                    "ref_min": round(min(sims), 4),
                    "n_below_low": sum(s < LOW for s in sims),
                    "pair_mean": round(st.mean(pair), 4),
                    "pair_min": round(min(pair), 4),
                    "window_ref_sims": sims,
                }
            print(v, q, flush=True)
    (Path(__file__).parent / "results" / "windows.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
