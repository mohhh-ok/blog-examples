# Qwen3-TTS セットアップ

Apache 2.0 ライセンス、商用可。Alibaba Cloud Qwen チーム、2026-01 リリース。
voice clone (3秒の参照音声) + 10 言語 (zh / en / ja / ko / de / fr / ru / pt / es / it) を公式サポート。
公式論文値で WER 1.835% / SIM 0.789、MiniMax / ElevenLabs を上回るとされる ([Qwen3-TTS blog](https://qwen.ai/blog?id=qwen3tts-0115))。

本リポでは **0.6B-Base から検証開始** → 余裕があれば 1.7B-Base に上げる方針。

## 環境

- 公式 README は Python 3.12 推奨。**本リポは pyenv の 3.11.8 で動作確認済み** (CosyVoice 3 と同じ)
- Mac (Apple Silicon, MPS バックエンド) で動作する。**本リポは M2 24GB Mac MPS のみ前提**。CUDA / CPU-only は別プロジェクトのスコープ
- ディスク **~2.3GB** (0.6B-Base のみで完結。speech_tokenizer は base に同梱されており、別 repo `Qwen3-TTS-Tokenizer-12Hz` は推論には不要)
- 1.7B-Base を追加 DL する場合は別途 +~6GB
- **weights は `/Volumes/UGREEN_1TB/models/qwen3-tts/` に集約**し、プロジェクト側からは `envs/pretrained_models/` 配下の symlink で参照する (内蔵 SSD 温存。実行前にマウントガード必須)

## モデル選定 (本リポ)

| モデル | サイズ | 用途 | 本リポでの位置づけ |
|---|---|---|---|
| `Qwen/Qwen3-TTS-Tokenizer-12Hz` | 664MB | speech codec (standalone) | **推論には不要** (Base 配下の speech_tokenizer/ で完結)。analysis 用途のみ |
| `Qwen/Qwen3-TTS-12Hz-0.6B-Base` | **2.3GB** | **voice clone foundation** (軽量) | **本リポのメイン**。MPS で安定。load ~3s / JA 50 char 生成 ~48s |
| `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | ~6GB | voice clone foundation (高品質) | 0.6B で品質不足の場合に追加検証 |
| `Qwen/Qwen3-TTS-12Hz-*-CustomVoice` | - | プリセット話者 | 本リポは clone のみなので未使用 |
| `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` | - | テキスト記述から声を設計 | 本リポは clone のみなので未使用 |

## Mac MPS で動かす要件

公式 README は NVIDIA + FlashAttention 2 前提だが、以下の組み合わせで Mac MPS でも動く
(複数フォーク / ブログで実証: [esendjer/Q3-TTS](https://github.com/esendjer/Q3-TTS),
[myByways: Qwen3-TTS with MLX-Audio on macOS](https://mybyways.com/blog/qwen3-tts-with-mlx-audio-on-macos),
[tumf: Qwen3-TTS Surprised by JA Quality on M3](https://dev.to/tumf/qwen3-tts-surprised-by-the-quality-of-japanese-on-apple-silicon-m3-creating-rights-free-voices-k1d)):

```python
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    device_map="mps",                # Apple GPU
    dtype=torch.float32,             # voice clone は float16 で NaN logits 既知バグ (#333)
    attn_implementation="sdpa",      # FlashAttention2 は Mac で動かない
)
```

3 つの設定すべてが必須:

- **`device_map="mps"`** — `cuda:0` のままだと当然落ちる
- **`dtype=torch.float32`** — `bfloat16` / `float16` は NaN logits になる ([issue #333](https://github.com/QwenLM/Qwen3-TTS/issues/333))。voice clone で必須
- **`attn_implementation="sdpa"`** — FlashAttention 2 は CUDA 専用、Mac は PyTorch SDPA fallback

## 手順

```bash
cd envs

# pyenv で Python 3.11.8 を有効化 (本リポでの動作確認 version)
pyenv local 3.11.8
python -m venv qwen3-tts-venv
source qwen3-tts-venv/bin/activate

# 0. 基本ツール (numpy 2.x は torch 系の一部依存と衝突するので pin)
pip install --upgrade pip wheel
pip install 'numpy<2'

# 1. qwen-tts (公式 PyPI パッケージ、torch 2.12 / transformers 4.57 / librosa / accelerate を引きずる)
pip install -U qwen-tts

# 2. 推論ユーティリティ + HF DL CLI
pip install soundfile 'huggingface_hub[cli]'

# 3. HuggingFace から weights を取得 (modelscope より日本からは速い、CosyVoice 検証で実証済み)
#    weights は UGREEN_1TB に集約し、プロジェクト側からは symlink で参照する。
#    内蔵 SSD を温存するため。マウント前提を満たさない場合は ext storage を mount してから走らせる。
[ -d /Volumes/UGREEN_1TB/models ] || { echo "UGREEN_1TB not mounted"; exit 1; }
mkdir -p /Volumes/UGREEN_1TB/models/qwen3-tts pretrained_models

#    0.6B-Base のみで OK。speech_tokenizer は同梱されている。
huggingface-cli download Qwen/Qwen3-TTS-12Hz-0.6B-Base \
  --local-dir /Volumes/UGREEN_1TB/models/qwen3-tts/Qwen3-TTS-12Hz-0.6B-Base
ln -sf /Volumes/UGREEN_1TB/models/qwen3-tts/Qwen3-TTS-12Hz-0.6B-Base \
  pretrained_models/Qwen3-TTS-12Hz-0.6B-Base

# 1.7B-Base は 0.6B で品質不足だった場合に DL する
# huggingface-cli download Qwen/Qwen3-TTS-12Hz-1.7B-Base \
#   --local-dir /Volumes/UGREEN_1TB/models/qwen3-tts/Qwen3-TTS-12Hz-1.7B-Base
# ln -sf /Volumes/UGREEN_1TB/models/qwen3-tts/Qwen3-TTS-12Hz-1.7B-Base \
#   pretrained_models/Qwen3-TTS-12Hz-1.7B-Base

cd ..
```

## 実行

```bash
source envs/qwen3-tts-venv/bin/activate
python scripts/generate_qwen3_tts.py
```

スクリプトは `prompts.py` の 7 言語 (zh / en / ja / ko / de / es / fr) を
`reference/ref.wav` を参照に clone 合成し `output/qwen3_tts/` に書き出す。

## サポート言語

公式 10 言語: zh / en / ja / ko / de / fr / ru / pt / es / it

06-19 / 本ベンチの 7 言語 (zh / en / ja / ko / de / es / fr) は全て公式カバー範囲内。
CosyVoice 3 (9 言語) と公式サポート言語がほぼ重なる。

## CosyVoice 3 で見つかった JA 劣化バグについて

CosyVoice 3 は `contains_chinese()` が kanji を中国語と誤判定して JA を中国語前処理パスに乗せる
バグが原因で kanji 直入力時に CER 0.25 まで崩壊した (`cosyvoice-notes.md` 参照)。

Qwen3-TTS は **frontend / 正規化ロジックの実装が異なる**ため同じバグは無いはずだが、
本ベンチで kanji 直入力 / kana 前処理の両方を回して挙動を確認する。
[tumf の記事](https://dev.to/tumf/qwen3-tts-surprised-by-the-quality-of-japanese-on-apple-silicon-m3-creating-rights-free-voices-k1d) では M3 + Qwen3-TTS で JA 品質が高評価とされている。

## 既知の落とし穴

- **float16 / bfloat16 NaN logits**: MPS では必ず `dtype=torch.float32`。
  公式 README のサンプルコードはそのまま使うと NaN になる ([issue #333](https://github.com/QwenLM/Qwen3-TTS/issues/333))。
- **FlashAttention 2 を install しようとして compile が落ちる**: 公式 README の `pip install flash-attn`
  は実行しない。Mac には FlashAttention 2 が存在しない (CUDA 専用)。SDPA で十分動く。
- **numpy 2.x で依存の一部が壊れる**: `numpy<2` で pin する。CosyVoice 検証時と同じ罠。
- **MPS memory 圧迫**: M2 24GB で 1.7B-Base は ~10GB 使う。他アプリ閉じてから走らせる。
  0.6B-Base なら 2-3GB なので余裕。
- **modelscope より HuggingFace が速い**: CosyVoice 3 検証で実証済み (250kB/s vs 5-7MB/s、25 倍差)。
  日本からは HF 経由を選ぶ。
- **`sox: command not found` warning は無害**: `sox` Python パッケージが import 時に CLI を探して
  失敗する println を吐くが、推論には影響しない (本リポの smoke test で確認済み)。
  気になるなら `brew install sox` で消える。
- **`flash-attn is not installed` warning も無害**: SDPA fallback で正常に動く。Mac では入れない。

## ライセンス

Apache 2.0。code (GitHub `QwenLM/Qwen3-TTS`) / weights (HF `Qwen/Qwen3-TTS-12Hz-*` 全 7 モデル)
ともに Apache 2.0 を確認済み。生成音声を SaaS で配信して問題なし。
NOTICE / LICENSE の同梱を忘れない。

CosyVoice 3 と並んで「商用 OK + JP 動く + 多言語」を満たす数少ない選択肢。
06-19 / 本ベンチの判定基準 (商用 license / slot 上限無し / 単価) の (2)(3)(4) は全部クリア。
あとは (1) JP WER が ElevenLabs +3pt 以内に収まるかを本ベンチで実測する。
