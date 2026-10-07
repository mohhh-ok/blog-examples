"""第2〜5弾: 短い入力 8 本 x 参照 x seed 2 を生成する。RunPod 上で実行。
設定は第1弾と同じ (fp32、num_steps=None、CFG 既定、ref_wav だけ渡し書き起こしは渡さない)。
参照は /eval/ref/<名前>.wav に置く (r10・r26 は手元の録音、それ以外は make_refs.sh で作る)。
usage: python gen.py <回>   回 = short | ref | 2x | len
"""
import json
import sys
import time
from pathlib import Path

from irodori_tts.inference_runtime import InferenceRuntime, RuntimeKey, SamplingRequest, download_hf_checkpoint, save_wav

TEXTS = {"k1": "はい", "k2": "ありがとう", "k3": "金閣寺", "k4": "嵐山", "k5": "伏見稲荷大社",
         "k6": "こんにちは。", "k7": "京都へようこそ。", "k8": "次は嵐山です。"}
# 回ごとの参照。条件名は記事の A〜F (R10 は別録音)
REFS = {
    "short": ("r10", "r26"),            # 第2弾: R10 / A
    "ref": ("r26t15", "r26pipe"),       # 第3弾: B / C
    "2x": ("r26pipe2x",),               # 第4弾: D
    "len": ("r26t1287", "r26long-pipe"),  # 第5弾: E / F
}
EVAL = Path("/eval")
OUT = EVAL / "out"


def main() -> None:
    refs = REFS[sys.argv[1]]
    OUT.mkdir(parents=True, exist_ok=True)
    checkpoint = download_hf_checkpoint("Aratako/Irodori-TTS-v4.1-Small")
    runtime = InferenceRuntime.from_key(RuntimeKey(checkpoint=str(checkpoint), model_device="cuda", codec_device="cuda"))
    records = []
    for tid, text in TEXTS.items():
        for ref in refs:
            for seed in (1, 2):
                out = OUT / f"{tid}-{ref}-s{seed}.wav"
                t = time.time()
                result = runtime.synthesize(
                    SamplingRequest(text=text, ref_wav=str(EVAL / "ref" / f"{ref}.wav"), num_steps=None, seed=seed),
                    log_fn=None,
                )
                save_wav(out, result.audio, result.sample_rate)
                rec = {"id": tid, "ref": ref, "seed": seed, "used_seed": result.used_seed, "text": text,
                       "gen_s": round(time.time() - t, 3), "audio_s": round(result.audio.shape[-1] / result.sample_rate, 3),
                       "messages": result.messages}
                records.append(rec)
                print("GEN", json.dumps(rec, ensure_ascii=False), flush=True)
    (EVAL / "gen.json").write_text(json.dumps(records, ensure_ascii=False, indent=2))
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
