"""第1弾: Irodori-TTS v4.1-Small で 清水寺 / 鹿苑寺 を単語と文で読ませる (6 文 x seed 3 = 18 本)。RunPod 上で実行。
設定は前編 10-07-irodori-tts-japanese/eval_irodori.py と同じ (fp32、num_steps=None でステップ数は両方ともチェックポイント既定、CFG 既定、ref_wav だけ渡し書き起こしは渡さない)。
"""
import json
import time
from pathlib import Path

from irodori_tts.inference_runtime import InferenceRuntime, RuntimeKey, SamplingRequest, download_hf_checkpoint, save_wav

TEXTS = {
    "w1": "清水寺",
    "w2": "鹿苑寺",
    "s1": "京都の清水寺を訪れました。",
    "s2": "清水寺の舞台から、京都の街を見渡せます。",
    "s3": "鹿苑寺は、金閣寺の名前で知られています。",
    "s4": "次は鹿苑寺へ向かいましょう。",
}
SEEDS = (1, 2, 3)
EVAL = Path("/eval")
OUT = EVAL / "out"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    checkpoint = download_hf_checkpoint("Aratako/Irodori-TTS-v4.1-Small")
    runtime = InferenceRuntime.from_key(RuntimeKey(checkpoint=str(checkpoint), model_device="cuda", codec_device="cuda"))
    records = []
    for tid, text in TEXTS.items():
        for seed in SEEDS:
            out = OUT / f"{tid}-s{seed}.wav"
            t = time.time()
            result = runtime.synthesize(
                SamplingRequest(text=text, ref_wav=str(EVAL / "ref" / "r10.wav"), num_steps=None, seed=seed),
                log_fn=None,
            )
            save_wav(out, result.audio, result.sample_rate)
            rec = {"id": tid, "seed": seed, "used_seed": result.used_seed, "text": text,
                   "gen_s": round(time.time() - t, 3), "audio_s": round(result.audio.shape[-1] / result.sample_rate, 3),
                   "messages": result.messages}
            records.append(rec)
            print("GEN", json.dumps(rec, ensure_ascii=False), flush=True)
    (EVAL / "gen.json").write_text(json.dumps(records, ensure_ascii=False, indent=2))
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
