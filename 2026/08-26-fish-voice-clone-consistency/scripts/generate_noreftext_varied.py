"""Fish Audio voice clone no-ref-text x text-variation test — generation step (第 4 弾).

第 2 弾と同一の異テキスト 5 種を、第 3 弾と同じく reference の書き起こしを
渡さずに (text="") 各 1 回 TTS し、output/noreftext_varied/text1.wav .. text5.wav と
レイテンシ記録を残す。ref_text 有無 × 同一文/異文の 2×2 マトリクスを完成させる。

- model: s2.1-pro (SDK の backend 引数 → `model` ヘッダ)
- reference: inline zero-shot clone (references に wav バイナリのみ。
  SDK の ReferenceAudio.text は必須フィールドのため空文字列 "" を渡す)
- API key: 環境変数 FISH_AUDIO_API_KEY

usage: python scripts/generate_noreftext_varied.py
"""

import json
import os
import sys
import time
from pathlib import Path

import soundfile as sf
from fish_audio_sdk import ReferenceAudio, Session, TTSRequest

ROOT = Path(__file__).resolve().parents[1]
REF_WAV = ROOT / "reference" / "ref.wav"
OUT = ROOT / "output" / "noreftext_varied"
OUT.mkdir(parents=True, exist_ok=True)

MODEL = "s2.1-pro"
SLEEP_BETWEEN_SEC = 2

# reference の書き起こしは渡さない (SDK 上 text は必須のため空文字列)
REF_TEXT = ""

# 生成テキスト 5 種 (第 2 弾 generate_varied.py と完全に同一)
GEN_TEXTS = [
    (
        "駅前の商店街では、朝から新鮮な野菜や果物を求める人々で賑わっています。"
        "店主たちは威勢のよい掛け声で客を迎え、通りには活気があふれていました。"
        "夕方には特売が始まり、さらに多くの買い物客が訪れる見込みです。"
    ),
    (
        "新しい図書館は、静かな環境と豊富な蔵書で多くの利用者に親しまれています。"
        "窓際の閲覧席からは中庭の緑が眺められ、読書に最適な空間となっています。"
        "週末には子ども向けの読み聞かせ会も開かれる予定です。"
    ),
    (
        "今年の夏祭りは、三年ぶりに花火大会が開催されることになりました。"
        "会場周辺では屋台の準備が進み、地元の人々の期待も高まっています。"
        "当日は混雑が予想されるため、公共交通機関の利用が呼びかけられています。"
    ),
    (
        "山頂からの眺めは素晴らしく、遠くの海岸線まではっきりと見渡すことができました。"
        "澄んだ空気の中、登山者たちはしばらく景色に見入っていました。"
        "下山の際には、足元に十分注意するよう案内が出ています。"
    ),
    (
        "料理教室では、旬の食材を使った家庭料理の作り方を学ぶことができます。"
        "講師が丁寧に手順を説明し、参加者は和やかな雰囲気で調理を楽しんでいました。"
        "来月からは初心者向けの新しいコースも始まるそうです。"
    ),
]


def main() -> None:
    api_key = os.environ.get("FISH_AUDIO_API_KEY")
    if not api_key:
        print("error: FISH_AUDIO_API_KEY is not set", file=sys.stderr)
        sys.exit(2)

    session = Session(api_key)
    ref_audio = REF_WAV.read_bytes()
    print(
        f"[init] model={MODEL} ref={REF_WAV.name} ({len(ref_audio)} bytes) ref_text=<empty>",
        flush=True,
    )

    records = []
    consecutive_failures = 0

    for i, gen_text in enumerate(GEN_TEXTS, start=1):
        out_path = OUT / f"text{i}.wav"
        req = TTSRequest(
            text=gen_text,
            references=[ReferenceAudio(audio=ref_audio, text=REF_TEXT)],
            format="wav",
        )
        t0 = time.time()
        try:
            with open(out_path, "wb") as f:
                for chunk in session.tts(req, backend=MODEL):
                    f.write(chunk)
        except Exception as e:  # noqa: BLE001
            consecutive_failures += 1
            print(f"[text{i}] FAILED: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            out_path.unlink(missing_ok=True)
            if consecutive_failures >= 3:
                print("error: 3 consecutive failures — aborting", file=sys.stderr)
                sys.exit(1)
            time.sleep(SLEEP_BETWEEN_SEC)
            continue

        consecutive_failures = 0
        latency = time.time() - t0
        info = sf.info(str(out_path))
        duration = info.frames / info.samplerate
        records.append(
            {
                "text_id": i,
                "file": out_path.name,
                "text": gen_text,
                "text_chars": len(gen_text),
                "latency_sec": round(latency, 3),
                "duration_sec": round(duration, 3),
                "samplerate": info.samplerate,
                "channels": info.channels,
                "bytes": out_path.stat().st_size,
            }
        )
        print(
            f"[text{i}] {out_path.name} latency={latency:.2f}s "
            f"duration={duration:.3f}s sr={info.samplerate}",
            flush=True,
        )
        if i < len(GEN_TEXTS):
            time.sleep(SLEEP_BETWEEN_SEC)

    meta = {
        "model": MODEL,
        "ref_file": REF_WAV.name,
        "ref_text": REF_TEXT,
        "ref_text_note": "SDK の ReferenceAudio.text は必須フィールドのため空文字列を渡した (書き起こし省略条件)",
        "num_texts_requested": len(GEN_TEXTS),
        "num_texts_succeeded": len(records),
        "texts": records,
    }
    (OUT / "generation.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"[done] {len(records)}/{len(GEN_TEXTS)} texts -> {OUT / 'generation.json'}", flush=True)
    if len(records) < len(GEN_TEXTS):
        sys.exit(1)


if __name__ == "__main__":
    main()
