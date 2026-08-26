"""第 6 弾 測定: resemblyzer 話者類似度で A (inline) vs B (reference_id) を比較。

- 群: A_same(5) / B_same(5) / A_varied(10) / B_varied(10)
- 各群の (i) 群内発話間ペア類似度 mean/std/min/max、(ii) 各発話 vs ref、(iii) 尺 std
- 同一テキスト対の A vs B 類似度 (15 対)
- ベースライン: 第 1 弾 (inline 同一文×5) の output/results.json を併記
- 補助: 群内ペア類似度の A vs B 差の permutation test (ペア値は独立でないため参考値)

usage: python measure_voiceid_ab.py
"""

import itertools
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common_voiceid_ab import BASELINE_RESULTS, REF_WAV, RESULTS_DIR, WAV_DIR

import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

SAME = [f"same{i}" for i in range(1, 6)]
TEXTS = [f"text{i}" for i in range(1, 11)]


def stats(values) -> dict:
    values = list(values)
    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 4),
        "std": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def main() -> None:
    files = {"ref": REF_WAV}
    for cond in ("a", "b"):
        for name in SAME + TEXTS:
            key = f"{cond}_{name}"
            p = WAV_DIR / f"{key}.wav"
            if not p.exists():
                raise FileNotFoundError(p)
            files[key] = p

    encoder = VoiceEncoder()
    embeds = {}
    durations = {}
    for key, path in files.items():
        wav = preprocess_wav(path)
        embeds[key] = encoder.embed_utterance(wav)
        durations[key] = round(len(wav) / 16000, 3)  # preprocess_wav resamples to 16k

    def sim(k1: str, k2: str) -> float:
        return round(float(np.dot(embeds[k1], embeds[k2])), 4)

    results = {"conditions": {}}
    intra_pairs = {}
    for cond, label in (("a", "A_inline"), ("b", "B_reference_id")):
        block = {}
        for group_label, names in (("same", SAME), ("varied", TEXTS)):
            keys = [f"{cond}_{n}" for n in names]
            pair_sims = {
                f"{k1}-{k2}": sim(k1, k2) for k1, k2 in itertools.combinations(keys, 2)
            }
            ref_sims = {k: sim("ref", k) for k in keys}
            durs = [durations[k] for k in keys]
            block[group_label] = {
                "intra_pair_similarity": pair_sims,
                "intra_pair_stats": stats(pair_sims.values()),
                "ref_similarity": ref_sims,
                "ref_similarity_stats": stats(ref_sims.values()),
                "durations_sec": {k: durations[k] for k in keys},
                "duration_stats": stats(durs),
            }
            intra_pairs[(cond, group_label)] = list(pair_sims.values())
        # 全 15 発話まとめた群内ペア (same+varied 一括)
        all_keys = [f"{cond}_{n}" for n in SAME + TEXTS]
        all_pairs = [sim(k1, k2) for k1, k2 in itertools.combinations(all_keys, 2)]
        block["all15_intra_pair_stats"] = stats(all_pairs)
        intra_pairs[(cond, "all15")] = all_pairs
        results["conditions"][label] = block

    # 同一テキスト対の A vs B (声が同じモデル実体か)
    matched = {n: sim(f"a_{n}", f"b_{n}") for n in SAME + TEXTS}
    results["matched_text_a_vs_b"] = matched
    results["matched_text_a_vs_b_stats"] = stats(matched.values())

    # permutation test (mean difference, B - A)。ペア類似度は独立でないため参考値
    rng = np.random.default_rng(20260826)
    perm = {}
    for group in ("same", "varied", "all15"):
        a = np.array(intra_pairs[("a", group)])
        b = np.array(intra_pairs[("b", group)])
        observed = b.mean() - a.mean()
        pooled = np.concatenate([a, b])
        n_a = len(a)
        count = 0
        n_iter = 10000
        for _ in range(n_iter):
            rng.shuffle(pooled)
            d = pooled[n_a:].mean() - pooled[:n_a].mean()
            if abs(d) >= abs(observed):
                count += 1
        perm[group] = {
            "observed_diff_b_minus_a": round(float(observed), 4),
            "p_two_sided": round(count / n_iter, 4),
            "note": "ペア類似度は発話を共有し独立でないため参考値",
        }
    results["permutation_test"] = perm

    # ベースライン (第 1 弾)
    baseline = json.loads(BASELINE_RESULTS.read_text())
    results["baseline_experiment1"] = {
        "inter_trial_stats": baseline["inter_trial_stats"],
        "ref_vs_trial_stats": baseline["ref_vs_trial_stats"],
        "duration_stats": baseline["duration_stats"],
    }

    out = RESULTS_DIR / "results.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"[done] -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
