"""Irodori-TTS v4.1-Small で台本を 3 方式 x 参照 3 品質 x 11 声で合成する。RunPod (RTX 4090) 上で実行する。

前提 (Pod 側で一度だけ。前編の 10-07-irodori-tts-japanese と同じ commit):
    git clone https://github.com/Aratako/Irodori-TTS.git /workspace/Irodori-TTS
    cd /workspace/Irodori-TTS && git checkout 89f9d8fbd4d51ea019867ee1197725ede1df13c5 && uv sync --extra cu128
    # measure.py 用。webrtcvad はビルド済みの webrtcvad-wheels を入れて resemblyzer は依存なしで入れる (前編と同じ)
    uv pip install webrtcvad-wheels librosa "setuptools<81" praat-parselmouth && uv pip install --no-deps resemblyzer
    /eval/ に ref/<voice>-<quality>.wav、refs.json、このスクリプトと texts.py を置く

実行:
    cd /workspace/Irodori-TTS && PYTHONPATH=/workspace/Irodori-TTS uv run --no-sync python /eval/gen_lines.py

設定は前編と同じ (fp32、num_steps・CFG はチェックポイントの既定、ref_wav だけ渡し書き起こしなし)。
- per-line-random: 1 行ずつ、seed=None (used_seed を記録)
- per-line-fixed: 1 行ずつ、全行 seed=FIXED_SEED
- run: texts.RUNS の範囲をつなげた文を 1 回で、seed=None
preflight: 10 行を 1 回にした文のトークン数と予測尺を、最初の声の clean で 1 本だけ生成して記録する (run を分けた理由の記録)。

出力: /eval/out/<voice>-<quality>-<mode>-<NN>.wav (NN は行番号 01〜10、run は r1, r2)、/eval/gen.jsonl
既に出力がある組は飛ばす (途中から再開できる)。
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import texts  # noqa: E402

from irodori_tts.inference_runtime import (  # noqa: E402
    InferenceRuntime,
    RuntimeKey,
    SamplingRequest,
    download_hf_checkpoint,
    save_wav,
)
from irodori_tts.text_normalization import normalize_text  # noqa: E402

EVAL = Path("/eval")
OUT = EVAL / "out"


def jobs(voices: list[str]) -> list[dict]:
    out = []
    for v in voices:
        for q in texts.QUALITIES:
            for i, line in enumerate(texts.LINES):
                out.append({"voice": v, "quality": q, "mode": "per-line-random", "idx": f"{i + 1:02d}", "text": line, "seed": None})
            for i, line in enumerate(texts.LINES):
                out.append({"voice": v, "quality": q, "mode": "per-line-fixed", "idx": f"{i + 1:02d}", "text": line, "seed": texts.FIXED_SEED})
            for r, (s, e) in enumerate(texts.RUNS):
                out.append({"voice": v, "quality": q, "mode": "run", "idx": f"r{r + 1}", "lines": [s + 1, e], "text": texts.run_text(s, e), "seed": None})
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    voices = [v["voice"] for v in json.loads((EVAL / "refs.json").read_text())]
    checkpoint = download_hf_checkpoint("Aratako/Irodori-TTS-v4.1-Small")
    runtime = InferenceRuntime.from_key(RuntimeKey(checkpoint=str(checkpoint), model_device="cuda", codec_device="cuda"))

    def n_tokens(text: str) -> int:
        return int(runtime.tokenizer.encode(normalize_text(text).strip()).numel())

    def synth(job: dict, path: Path) -> dict:
        t = time.time()
        result = runtime.synthesize(
            SamplingRequest(text=job["text"], ref_wav=str(EVAL / "ref" / f"{job['voice']}-{job['quality']}.wav"), num_steps=None, seed=job["seed"]),
            log_fn=None,
        )
        save_wav(path, result.audio, result.sample_rate)
        return {
            **job,
            "tokens": n_tokens(job["text"]),
            "used_seed": result.used_seed,
            "gen_s": round(time.time() - t, 3),
            "audio_s": round(result.audio.shape[-1] / result.sample_rate, 3),
            "sample_rate": result.sample_rate,
            "messages": result.messages,
        }

    pre = OUT.parent / "preflight"
    pre.mkdir(exist_ok=True)
    full = {"voice": voices[0], "quality": "clean", "mode": "preflight-10lines", "idx": "all", "text": texts.run_text(0, 10), "seed": texts.FIXED_SEED}
    rec = synth(full, pre / f"{voices[0]}-clean-10lines.wav")
    rec["run_tokens"] = [n_tokens(texts.run_text(s, e)) for s, e in texts.RUNS]
    (EVAL / "preflight.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    print("PREFLIGHT", json.dumps(rec, ensure_ascii=False), flush=True)

    log = (EVAL / "gen.jsonl").open("a")
    all_jobs = jobs(voices)
    t0 = time.time()
    for n, job in enumerate(all_jobs, 1):
        path = OUT / f"{job['voice']}-{job['quality']}-{job['mode']}-{job['idx']}.wav"
        if path.exists():
            continue
        rec = synth(job, path)
        log.write(json.dumps(rec, ensure_ascii=False) + "\n")
        log.flush()
        print(f"GEN {n}/{len(all_jobs)} {time.time() - t0:.0f}s {path.name} gen={rec['gen_s']} audio={rec['audio_s']}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
