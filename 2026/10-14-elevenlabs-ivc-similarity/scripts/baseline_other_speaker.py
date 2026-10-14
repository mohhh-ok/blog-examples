"""基準: クローンではない別人の声 (ElevenLabs のライブラリ音声・日本語男性) で同一文を生成し、
ref との類似度を測る。「ref とどこまで下がると別人の水準か」の目安を取るため。

- voice: Shohei (library voice, Japanese male)。読み上げに使うだけで声の設定は変えない
- 文: common.SAME_TEXT、モデル: common.MODEL (eleven_v4)、1 本
- 出力: output/baseline/eleven_v4.wav, output/baseline/results.json
- ref との類似度は measure.py でも計算し直して output/results.json の baseline_other_speaker に入れる

usage: ELEVENLABS_API_KEY=... python scripts/baseline_other_speaker.py
"""

import json

from resemblyzer import VoiceEncoder, preprocess_wav

from common import MODEL, OUT, REF_WAV, SAME_TEXT
from generate import tts

VOICE_ID = "NO5A3b3sSzDyJQF7MiNS"  # Shohei - Serious, Clear and Measured
D = OUT / "baseline"


def main() -> None:
    recs = [tts(VOICE_ID, MODEL, SAME_TEXT, D / f"{MODEL}.wav")]
    enc = VoiceEncoder()
    ref = enc.embed_utterance(preprocess_wav(REF_WAV))
    for rec in recs:
        e = enc.embed_utterance(preprocess_wav(OUT / rec["file"]))
        rec["ref_similarity"] = round(float(ref @ e), 4)
    res = {"voice": "Shohei (ElevenLabs library, Japanese male)", "records": recs}
    (D / "results.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
