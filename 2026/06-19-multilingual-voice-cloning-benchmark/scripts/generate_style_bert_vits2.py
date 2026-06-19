"""Style-Bert-VITS2 JP-Extra で日本語のみ生成。

SBV2 はゼロショットクローンではなく fine-tune ベース。
事前手順 (envs/sbv2.md):
1. Style-Bert-VITS2 を clone
2. reference/ref.wav を 1分以上の素材で再録音
3. slice → 文字起こし → 学習 → モデルファイル出力
4. このスクリプトは学習済みモデルを呼ぶだけ

注: このベンチでは「日本語の上限を示す参考値」として ja のみ動かす。
他言語は SBV2 JP-Extra 非対応。
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prompts import PROMPTS  # noqa: E402

# Style-Bert-VITS2 の repo パス
SBV2_ROOT = Path(__file__).resolve().parents[1] / "envs" / "Style-Bert-VITS2"
sys.path.insert(0, str(SBV2_ROOT))

from style_bert_vits2.nlp import bert_models  # noqa: E402
from style_bert_vits2.constants import Languages  # noqa: E402
from style_bert_vits2.tts_model import TTSModel  # noqa: E402

OUT = ROOT / "output" / "sbv2"
OUT.mkdir(parents=True, exist_ok=True)

# 学習で出力されたモデルファイル名に合わせて書き換える
MODEL_NAME = "ref"  # envs/sbv2.md 参照
MODEL_DIR = SBV2_ROOT / "model_assets" / MODEL_NAME


def main() -> None:
    bert_models.load_model(Languages.JP, "ku-nlp/deberta-v2-large-japanese-char-wwm")
    bert_models.load_tokenizer(Languages.JP, "ku-nlp/deberta-v2-large-japanese-char-wwm")

    model = TTSModel(
        model_path=str(MODEL_DIR / f"{MODEL_NAME}.safetensors"),
        config_path=str(MODEL_DIR / "config.json"),
        style_vec_path=str(MODEL_DIR / "style_vectors.npy"),
        device="cpu",
    )

    for lang in ("ja",):
        text = PROMPTS[lang]
        out = OUT / f"{lang}.wav"
        t0 = time.time()
        sr, audio = model.infer(text=text, language=Languages.JP)
        import soundfile as sf

        sf.write(str(out), audio, sr)
        print(f"[{lang}] {out.name} ({time.time() - t0:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
