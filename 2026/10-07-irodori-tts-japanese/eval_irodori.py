"""Irodori-TTS v4.1-Small の生成と、両モデルの話者類似度 — RunPod (RTX 4090) 上で実行する。

前提 (Pod 側で一度だけ):
    git clone https://github.com/Aratako/Irodori-TTS.git /workspace/Irodori-TTS
    cd /workspace/Irodori-TTS && uv sync --extra cu128
    # webrtcvad はソースビルドに Python.h が要るので、ビルド済みの webrtcvad-wheels を入れて resemblyzer は依存なしで入れる
    uv pip install webrtcvad-wheels librosa "setuptools<81" && uv pip install --no-deps resemblyzer
    /eval/ に ref/{r10,r26}.wav、out/fish/*.wav、このスクリプト・texts.py・data/ を置く

実行:
    cd /workspace/Irodori-TTS && PYTHONPATH=/workspace/Irodori-TTS uv run --no-sync python /eval/eval_irodori.py

やること:
  1. InferenceRuntime をロード (fp32, 40 RF steps, text CFG 3.0 / speaker CFG 5.0 = モデルカードのベンチと同じ既定)
  2. texts.jobs() の 125 本 + seed 実験 4 本 (seed=42 を R10 / R26 で各 2 回) を生成し、RTF と used_seed を記録
  3. resemblyzer で、Irodori / Fish の全生成と生成に使った参照音声とのコサイン類似度、B 5 本の相互類似度を出す
  4. 結果を /eval/results/ に JSON で保存

env: STEPS (既定はチェックポイントの既定 = 40), ONLY (カンマ区切りの tag に絞る。動作確認用)
"""

import hashlib
import json
import os
import sys
import time
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import texts  # noqa: E402

from irodori_tts.inference_runtime import (  # noqa: E402
    InferenceRuntime,
    RuntimeKey,
    SamplingRequest,
    download_hf_checkpoint,
    save_wav,
)

HF_CHECKPOINT = "Aratako/Irodori-TTS-v4.1-Small"
EVAL = Path("/eval")
REF_DIR = EVAL / "ref"
OUT = EVAL / "out" / "irodori"
FISH_OUT = EVAL / "out" / "fish"
RESULTS = EVAL / "results"
STEPS = int(os.environ["STEPS"]) if os.environ.get("STEPS") else None
ONLY = set(os.environ["ONLY"].split(",")) if os.environ.get("ONLY") else None
SEED = 42


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def all_jobs() -> list[dict]:
    jobs = [dict(j, seed=None) for j in texts.jobs()]
    for ref in ("r10", "r26"):
        for i in (1, 2):
            jobs.append({"exp": "seed", "tag": f"seed_{ref}_{i}", "ref": ref, "text": texts.TEXT_B, "seed": SEED})
    return [j for j in jobs if ONLY is None or j["tag"] in ONLY]


def generate() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    checkpoint = download_hf_checkpoint(HF_CHECKPOINT)
    download_seconds = time.time() - t0
    t0 = time.time()
    runtime = InferenceRuntime.from_key(
        RuntimeKey(checkpoint=str(checkpoint), model_device="cuda", codec_device="cuda")
    )
    load_seconds = time.time() - t0
    print(f"download {download_seconds:.1f}s, load {load_seconds:.1f}s, watermark={runtime.watermarker.ready}", flush=True)

    records = []
    log = (RESULTS / "gen_irodori.jsonl").open("w")
    for job in all_jobs():
        out = OUT / f"{job['tag']}.wav"
        t = time.time()
        result = runtime.synthesize(
            SamplingRequest(
                text=job["text"],
                ref_wav=str(REF_DIR / f"{job['ref']}.wav"),
                num_steps=STEPS,
                seed=job["seed"],
            ),
            log_fn=None,
        )
        save_wav(out, result.audio, result.sample_rate)
        gen_seconds = time.time() - t
        audio_seconds = result.audio.shape[-1] / result.sample_rate
        rec = {
            **job,
            "used_seed": result.used_seed,
            "gen_s": round(gen_seconds, 3),
            "audio_s": round(audio_seconds, 3),
            "rtf": round(gen_seconds / audio_seconds, 4),
            "sample_rate": result.sample_rate,
            "md5": md5(out),
            "messages": result.messages,
        }
        records.append(rec)
        log.write(json.dumps(rec, ensure_ascii=False) + "\n")
        log.flush()
        print("GEN", json.dumps({k: rec[k] for k in ("tag", "gen_s", "audio_s", "rtf", "used_seed")}), flush=True)
    return {
        "checkpoint": HF_CHECKPOINT,
        "download_s": round(download_seconds, 1),
        "load_s": round(load_seconds, 1),
        "watermark": runtime.watermarker.ready,
        "num_steps": STEPS,
        "records": records,
    }


def similarity(jobs: list[dict]) -> dict:
    from resemblyzer import VoiceEncoder, preprocess_wav

    encoder = VoiceEncoder()
    embeds = {f"ref:{name}": encoder.embed_utterance(preprocess_wav(REF_DIR / f"{name}.wav")) for name in texts.REF_TEXTS}
    for model, root in (("irodori", OUT), ("fish", FISH_OUT)):
        for job in jobs:
            path = root / f"{job['tag']}.wav"
            if path.exists():
                embeds[f"{model}:{job['tag']}"] = encoder.embed_utterance(preprocess_wav(path))

    def cos(a: str, b: str) -> float:
        return round(float(np.dot(embeds[a], embeds[b])), 4)  # L2 正規化済み

    ref_vs = {}
    for job in jobs:
        for model in ("irodori", "fish"):
            name = f"{model}:{job['tag']}"
            if name in embeds:
                ref_vs[name] = cos(f"ref:{job['ref']}", name)
    b_pairwise = {}
    for model in ("irodori", "fish"):
        for ref in texts.REF_TEXTS:
            names = [f"{model}:b_{ref}_run{i}" for i in range(1, 6)]
            if all(n in embeds for n in names):
                b_pairwise[f"{model}:{ref}"] = {f"{a}~{b}": cos(a, b) for a, b in combinations(names, 2)}
    return {"ref_vs": ref_vs, "b_pairwise": b_pairwise}


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    gen = generate()
    (RESULTS / "gen_irodori.json").write_text(json.dumps(gen, ensure_ascii=False, indent=2))
    seed_md5 = {
        ref: {
            "md5_1": md5(OUT / f"seed_{ref}_1.wav"),
            "md5_2": md5(OUT / f"seed_{ref}_2.wav"),
        }
        for ref in texts.REF_TEXTS
        if (OUT / f"seed_{ref}_1.wav").exists()
    }
    for v in seed_md5.values():
        v["identical"] = v["md5_1"] == v["md5_2"]
    (RESULTS / "seed_md5.json").write_text(json.dumps(seed_md5, indent=2))
    print("SEED_MD5", json.dumps(seed_md5), flush=True)
    sim = similarity(all_jobs())
    (RESULTS / "similarity.json").write_text(json.dumps(sim, ensure_ascii=False, indent=2))
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
