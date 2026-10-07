"""measure.json を条件ごとに集計して results/summary.json と result.md を書き、聴き比べ用の連結音声を作る。ローカルで実行する。

使い方:
  python3 -I make_report.py <RunPod から回収したディレクトリ (measure.json, gen.jsonl, preflight.json, refs.json, out/)> <聴き比べ音声の出力先>

条件 = 声 x 参照品質 x 方式。集計の単位は per-line 方式では 10 行、run 方式では 2.5 秒窓 (2 run の全窓)。
- ref 比: 単位ごとの ref 比類似度の平均・標準偏差 (母標準偏差)・最小・LOW 未満の数
- ペア: 同じ条件の単位どうし全ペアの類似度の平均・最小
- F0: 単位ごとの F0 中央値の最小・最大、参照の F0 中央値
聴き比べ音声: per-line は 10 行を、run は r1・r2 を、間に 0.4 秒の無音を挟んでつなぐ。
"""

import json
import statistics as st
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import texts  # noqa: E402

HERE = Path(__file__).parent
LOW = 0.75
GAP_S = 0.4


def summarize(cond: dict) -> dict:
    rows = cond["rows"]
    units = [w for r in rows for w in r["windows"]] if rows[0]["mode"] == "run" else rows
    sims = [u["ref_sim"] for u in units]
    f0s = [u["f0"] for u in units if u["f0"] is not None]
    pair = cond["pairwise"]
    return {
        "n_units": len(units),
        "ref_mean": round(st.mean(sims), 4),
        "ref_std": round(st.pstdev(sims), 4),
        "ref_min": round(min(sims), 4),
        "ref_max": round(max(sims), 4),
        "n_below_low": sum(s < LOW for s in sims),
        "pair_mean": round(st.mean(pair), 4),
        "pair_min": round(min(pair), 4),
        "f0_min": min(f0s) if f0s else None,
        "f0_max": max(f0s) if f0s else None,
        "run_ref_sim": [r["ref_sim"] for r in rows] if rows[0]["mode"] == "run" else None,
    }


def concat(paths: list[Path], dst: Path) -> None:
    # 生成音声のサンプルレートは全部同じ。最後以外の末尾に GAP_S の無音を足してつなぐ
    n = len(paths)
    args = [a for p in paths for a in ("-i", str(p))]
    chains = [f"[{i}:a]apad=pad_dur={GAP_S}[p{i}]" if i < n - 1 else f"[{i}:a]anull[p{i}]" for i in range(n)]
    graph = ";".join(chains) + ";" + "".join(f"[p{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[out]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", graph, "-map", "[out]", "-c:a", "pcm_s16le", str(dst)], check=True)


def main() -> None:
    src, listen = Path(sys.argv[1]), Path(sys.argv[2])
    measure = json.loads((src / "measure.json").read_text())
    voices = json.loads((src / "refs.json").read_text())
    preflight = json.loads((src / "preflight.json").read_text())
    gen = [json.loads(line) for line in (src / "gen.jsonl").read_text().splitlines()]

    summary = {}
    for key, cond in measure["conditions"].items():
        v, q, m = key.split("|")
        summary[key] = {"voice": v, "quality": q, "mode": m, "ref_f0": measure["refs"][f"{v}-{q}"]["f0"], **summarize(cond)}

    # 品質 x 方式ごとに 11 声をまとめる
    overall = {}
    for q in texts.QUALITIES:
        for m in texts.MODES:
            sel = [s for s in summary.values() if s["quality"] == q and s["mode"] == m]
            overall[f"{q}|{m}"] = {
                "voices": len(sel),
                "ref_mean_avg": round(st.mean(s["ref_mean"] for s in sel), 4),
                "ref_std_avg": round(st.mean(s["ref_std"] for s in sel), 4),
                "ref_min_min": round(min(s["ref_min"] for s in sel), 4),
                "n_below_low_total": sum(s["n_below_low"] for s in sel),
                "n_units_total": sum(s["n_units"] for s in sel),
                "voices_with_below_low": sorted(s["voice"] for s in sel if s["n_below_low"]),
                "pair_mean_avg": round(st.mean(s["pair_mean"] for s in sel), 4),
                "pair_min_min": round(min(s["pair_min"] for s in sel), 4),
            }

    # 同じ声・品質で seed 固定とランダムを対で比べる
    paired = []
    for v in voices:
        for q in texts.QUALITIES:
            r = summary[f"{v['voice']}|{q}|per-line-random"]
            f = summary[f"{v['voice']}|{q}|per-line-fixed"]
            paired.append({"voice": v["voice"], "quality": q, "std_random": r["ref_std"], "std_fixed": f["ref_std"],
                           "pair_mean_random": r["pair_mean"], "pair_mean_fixed": f["pair_mean"]})

    timing = {
        "n": len(gen),
        "gen_s_total": round(sum(g["gen_s"] for g in gen), 1),
        "per_line_gen_s_mean": round(st.mean(g["gen_s"] for g in gen if g["mode"] != "run"), 3),
        "run_gen_s_mean": round(st.mean(g["gen_s"] for g in gen if g["mode"] == "run"), 3),
        "run_audio_s_max": max(g["audio_s"] for g in gen if g["mode"] == "run"),
    }
    results = HERE / "results"
    results.mkdir(exist_ok=True)
    (results / "summary.json").write_text(json.dumps(
        {"overall": overall, "conditions": summary, "fixed_vs_random": paired, "preflight": {k: preflight[k] for k in ("tokens", "run_tokens", "audio_s", "messages")}, "timing": timing},
        ensure_ascii=False, indent=2))

    listen.mkdir(parents=True, exist_ok=True)
    for key in summary:
        v, q, m = key.split("|")
        if m == "run":
            paths = [src / "out" / f"{v}-{q}-run-r{i + 1}.wav" for i in range(len(texts.RUNS))]
        else:
            paths = [src / "out" / f"{v}-{q}-{m}-{i + 1:02d}.wav" for i in range(len(texts.LINES))]
        concat(paths, listen / f"{v}-{q}-{m}.wav")
    print(json.dumps(overall, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
