"""OpenVoice v2 で 7 言語生成。

OpenVoice v2 は「MeloTTS でベース音声生成 → ToneColorConverter で参照音声のトーンに変換」の2段階。
公式 demo (demo_part3.ipynb) を Python スクリプトに直したもの。

事前: envs/openvoice.md の手順で git clone + pip install を済ませる
参照音声: reference/ref.wav

サポート言語: en / es / fr / zh / ja / ko  (de は MeloTTS 未対応のためスキップ)
"""

import os
import sys
import time
from pathlib import Path

import torch

# MeloTTS の chinese/japanese BERT は device='cpu' を受け取っても、内部で
# MPS が available なら勝手に MPS に切り替える (melo/text/chinese_bert.py:24)。
# 親モデル本体は CPU のままなので "Placeholder storage has not been allocated
# on MPS device!" で落ちる。MPS を見えなくして CPU 一本に固定する。
torch.backends.mps.is_available = lambda: False
torch.backends.mps.is_built = lambda: False

# mecab-python3 (大文字 MeCab) と python-mecab-ko (小文字 mecab) が
# macOS APFS の case-insensitive FS で同じディレクトリに着地して衝突する。
# ko を動かすため python-mecab-ko だけ残しているが、melo.text.cleaner は
# japanese.py を import するため `import MeCab` が要る。今回 ja は既に生成
# 済みなので、ja で使われないようにスタブを差し込んでおく。
import types  # noqa: E402
_mecab_stub = types.ModuleType("MeCab")
class _StubTagger:  # noqa: D401
    def __init__(self, *a, **kw): pass
    def parse(self, s):
        raise RuntimeError("MeCab stub: regenerate ja with mecab-python3 installed.")
    def parseToNode(self, s):
        raise RuntimeError("MeCab stub: regenerate ja with mecab-python3 installed.")
_mecab_stub.Tagger = _StubTagger
sys.modules["MeCab"] = _mecab_stub

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prompts import PROMPTS  # noqa: E402

# OpenVoice の repo パス (clone した場所を環境変数で渡す)
OPENVOICE_ROOT = Path(os.environ.get("OPENVOICE_ROOT", ROOT / "envs" / "OpenVoice"))
sys.path.insert(0, str(OPENVOICE_ROOT))

from openvoice import se_extractor  # noqa: E402
from openvoice.api import ToneColorConverter  # noqa: E402
from melo.api import TTS as MeloTTS  # noqa: E402

REF = ROOT / "reference" / "ref.wav"
OUT = ROOT / "output" / "openvoice"
OUT.mkdir(parents=True, exist_ok=True)

# checkpoints は公式の HF からダウンロード (envs/openvoice.md 参照)
CKPT_CONVERTER = OPENVOICE_ROOT / "checkpoints_v2" / "converter"

# MeloTTS 言語コード対応
MELO_LANG = {
    "en": "EN", "es": "ES", "fr": "FR",
    "zh": "ZH", "ja": "JP", "ko": "KR",
    # "de": 未対応
}

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def main() -> None:
    if not REF.exists():
        raise SystemExit(f"missing reference: {REF}")

    converter = ToneColorConverter(str(CKPT_CONVERTER / "config.json"), device=DEVICE)
    converter.load_ckpt(str(CKPT_CONVERTER / "checkpoint.pth"))

    target_se, _ = se_extractor.get_se(str(REF), converter, vad=True)

    for lang, text in PROMPTS.items():
        if lang not in MELO_LANG:
            print(f"[{lang}] skip (MeloTTS unsupported)", flush=True)
            continue

        out_exists = (OUT / f"{lang}.wav").exists()
        if out_exists:
            print(f"[{lang}] skip (already generated)", flush=True)
            continue

        melo_lang = MELO_LANG[lang]
        melo = MeloTTS(language=melo_lang, device=DEVICE)
        speaker_id = list(melo.hps.data.spk2id.values())[0]
        # ses/ には en-default.pth / en-us.pth / en-newest.pth / es.pth / fr.pth / jp.pth / kr.pth / zh.pth が入っている。
        # 英語のみ `en-default.pth` を使う。他は `<lang>.pth` 直接。
        ses_name = "en-default" if melo_lang == "EN" else melo_lang.lower()
        source_se_path = OPENVOICE_ROOT / "checkpoints_v2" / "base_speakers" / "ses" / f"{ses_name}.pth"
        source_se = torch.load(str(source_se_path), map_location=DEVICE, weights_only=True)

        tmp = OUT / f"{lang}.tmp.wav"
        out = OUT / f"{lang}.wav"
        t0 = time.time()

        melo.tts_to_file(text, speaker_id, str(tmp), speed=1.0)
        # message は内部の watermark に使う。空だと add_watermark で shape mismatch
        # (envs/openvoice-repo/openvoice/utils.py:61) になるので非空文字列を渡す。
        converter.convert(
            audio_src_path=str(tmp),
            src_se=source_se,
            tgt_se=target_se,
            output_path=str(out),
            message="@MyShell",
        )
        tmp.unlink(missing_ok=True)
        print(f"[{lang}] {out.name} ({time.time() - t0:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
