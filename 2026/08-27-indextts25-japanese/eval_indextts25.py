"""IndexTTS-2.5 日本語検証 — RunPod (RTX 4090) 上で実行する self-contained スクリプト。

前提 (Pod 側で一度だけ):
    git clone https://github.com/index-tts/index-tts.git /workspace/index-tts
    cd /workspace/index-tts
    pip install -U uv && uv sync --all-extras
    uv tool install huggingface-hub
    hf download IndexTeam/IndexTTS-2.5 --local-dir=checkpoints
    # 類似度・ASR 用 (webrtcvad が pkg_resources を要求するので setuptools<81)
    uv pip install resemblyzer faster-whisper "setuptools<81"

実行:
    cd /workspace/index-tts && uv run python eval_indextts25.py

やること:
  1. IndexTTS2 を bf16 でロードし、infer() のシグネチャを inspect で記録
     (seed パラメータの有無をコードでなく実体で確認する)
  2. 生成 17 本:
     - B: 同一テキストを 5 回 (クローン一貫性)
     - B-seed: 同一テキストを torch.manual_seed(42) 固定で 2 回 → MD5 比較 (決定性)
     - C: 読み指定なしの誤読しやすい漢字 5 文
     - D: <漢字|かな> 読み指定 5 文 (異読強制 <東雲|とうめ> 含む)
  3. resemblyzer で ref vs 各生成 / B 5 本相互のコサイン類似度
  4. faster-whisper large-v3 で全生成を文字起こし (聴取の代替ではない一次シグナル)
  5. 結果を JSON で /eval/results/ に保存
"""

import hashlib
import inspect
import json
import random
import time
from pathlib import Path

import numpy as np
import torch

from indextts.infer_v2_5 import IndexTTS2

REF_WAV = "/eval/ref.wav"  # クローン元 (任意の日本語音声 10〜20 秒程度)
OUT_DIR = Path("/eval/out")
RESULTS_DIR = Path("/eval/results")

TEXT_B = "本日は晴天なり。マイクのテスト中です。この音声は、ゼロショット音声合成のサンプルです。"

TEXTS_C = {  # 読み指定なし: 誤読しやすい漢字
    "c1": "了解しました。明日の朝、東雲駅で待ち合わせましょう。",
    "c2": "雰囲気のいい店で、代替案について早急に検討した。",
    "c3": "彼は人気のない道を歩いた。",
    "c4": "一日中、日本橋で過ごした。",
    "c5": "今日は八日、明後日は十日です。",
}

TEXTS_D = {  # <漢字|かな> 読み指定
    "d1": "明日の朝、<東雲|しののめ>駅で待ち合わせましょう。",
    "d2": "彼は料理が<上手|じょうず>だが、囲碁では<上手|うわて>に負けた。",
    "d3": "<人気|ひとけ>のない道を歩いた。",
    "d4": "<人気|にんき>のない道を歩いた。",
    "d5": "明日の朝、<東雲|とうめ>駅で待ち合わせましょう。",  # 異読の強制
}


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def audio_seconds(path: Path) -> float:
    import wave

    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def set_seed(seed: int) -> None:
    """infer() に seed 引数は無いので、呼び出し直前に外部から全 RNG を固定する。"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # --- 1. load + signature ---
    t0 = time.time()
    tts = IndexTTS2(
        cfg_path="checkpoints/config.yaml",
        model_dir="checkpoints",
        use_bf16=True,
        use_cuda_kernel=True,
    )
    load_seconds = time.time() - t0
    print(f"model load: {load_seconds:.1f}s")

    sig = str(inspect.signature(IndexTTS2.infer))
    has_seed = "seed" in inspect.signature(IndexTTS2.infer).parameters
    print(f"HAS_SEED_PARAM: {has_seed}")
    (RESULTS_DIR / "signature.json").write_text(
        json.dumps(
            {"IndexTTS2.infer": sig, "has_seed_param": has_seed},
            ensure_ascii=False,
            indent=2,
        )
    )

    # --- 2. generate ---
    results = []

    def gen(tag: str, text: str, seed: int | None = None) -> None:
        if seed is not None:
            set_seed(seed)
        out = OUT_DIR / f"{tag}.wav"
        t = time.time()
        tts.infer(
            spk_audio_prompt=REF_WAV,
            text=text,
            output_path=str(out),
            lang="ja",
            verbose=True,  # かな置換後のトークン列がログに出る (読み指定機構の確認用)
        )
        gen_seconds = time.time() - t
        dur = audio_seconds(out)
        rec = {
            "tag": tag,
            "text": text,
            "seed": seed,
            "gen_seconds": round(gen_seconds, 2),
            "audio_seconds": round(dur, 2),
            "rtf": round(gen_seconds / dur, 3),
            "ok": True,
        }
        results.append(rec)
        print("RESULT:", json.dumps(rec, ensure_ascii=False))

    for i in range(1, 6):
        gen(f"b_run{i}", TEXT_B)
    gen("b_seed1", TEXT_B, seed=42)
    gen("b_seed2", TEXT_B, seed=42)
    for tag, text in {**TEXTS_C, **TEXTS_D}.items():
        gen(tag, text)

    (RESULTS_DIR / "gen_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2)
    )

    # --- 2b. determinism check ---
    seed_cmp = {
        "b_seed1_md5": md5(OUT_DIR / "b_seed1.wav"),
        "b_seed2_md5": md5(OUT_DIR / "b_seed2.wav"),
    }
    seed_cmp["identical"] = seed_cmp["b_seed1_md5"] == seed_cmp["b_seed2_md5"]
    (RESULTS_DIR / "seed_compare.json").write_text(json.dumps(seed_cmp, indent=2))
    print("SEED_COMPARE:", seed_cmp)

    # --- 3. speaker similarity (resemblyzer) ---
    from itertools import combinations

    from resemblyzer import VoiceEncoder, preprocess_wav

    encoder = VoiceEncoder()
    embeds = {"ref": encoder.embed_utterance(preprocess_wav(REF_WAV))}
    for rec in results:
        f = OUT_DIR / f"{rec['tag']}.wav"
        embeds[rec["tag"]] = encoder.embed_utterance(preprocess_wav(f))

    def cos(a: str, b: str) -> float:
        return round(float(np.dot(embeds[a], embeds[b])), 4)  # L2 正規化済み

    similarity = {
        "ref_vs": {r["tag"]: cos("ref", r["tag"]) for r in results},
        "b_pairwise": {
            f"b_run{a}~b_run{b}": cos(f"b_run{a}", f"b_run{b}")
            for a, b in combinations(range(1, 6), 2)
        },
    }
    (RESULTS_DIR / "similarity.json").write_text(
        json.dumps(similarity, ensure_ascii=False, indent=2)
    )
    print("SIMILARITY:", json.dumps(similarity, indent=2))

    # --- 4. ASR (faster-whisper large-v3) ---
    from faster_whisper import WhisperModel

    asr_model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    asr = {}
    for name in ["ref"] + [r["tag"] for r in results]:
        f = Path(REF_WAV) if name == "ref" else OUT_DIR / f"{name}.wav"
        segments, _ = asr_model.transcribe(str(f), language="ja", beam_size=5)
        asr[name] = "".join(s.text for s in segments).strip()
        print(f"ASR {name} -> {asr[name]}")
    (RESULTS_DIR / "asr.json").write_text(json.dumps(asr, ensure_ascii=False, indent=2))

    print("DONE")


if __name__ == "__main__":
    main()
