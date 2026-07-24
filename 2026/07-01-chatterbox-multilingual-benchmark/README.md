# Chatterbox Multilingual v3 を 06-22 の枠組みで再検証

## やること

Resemble AI 製 **Chatterbox Multilingual v3** (MIT, 500M params, 20+ 言語対応、日本語含む) を、
[06-22 の多言語 voice clone ベンチ](../06-22-tts-commercial-provider-comparison/) と**同じ参照音声・同じ 7 言語プロンプト・同じ計測 (Whisper large-v3 の CER / F0 中央値)** で走らせて、
Qwen3-TTS / CosyVoice 2/3 / OpenVoice v2 と比較可能な数字を出す。

## やらないこと

- **女性 refaudio の再現性検証は本記事のスコープ外**。実運用で発見した「Qwen3-TTS で女声が男声化する drift」を Chatterbox が回避するかどうかは別途社内で検証済みだが、参照音声を公開できない (実話者の声) ため本記事の再現手順には含めない
- MOS / 声質主観評価
- 商用 provider の再計測 (06-22 と同一枠組みなので 06-22 の数字を横に置いて比較する前提)

## 背景

06-22 ベンチ時点では Chatterbox は「EN 中心、JP 弱い」との評価で候補から外れていた。
その後 Resemble AI が **Chatterbox Multilingual v3** (JP を含む 20+ 言語対応、MIT) を公開し、
日本語 + 欧州語主体の voice clone SaaS 用途で新たな候補になった。

現行スタックで採用中の Qwen3-TTS (06-22 で 1 位) に対して、Chatterbox Multilingual が
CER / 声質保持 / 動作要件でどのくらい戦えるかを本記事で計測する。

## セットアップ

```bash
uv sync
```

初回のみ Chatterbox weights (~2GB) を HF hub から DL。以降は `~/.cache/huggingface` に cache。

## 走らせる

```bash
# 生成 (Mac M2 MPS で 7 言語 ~3-5 分)
uv run python scripts/generate_chatterbox.py

# CER 計測 (Whisper large-v3 int8/cpu、7 言語 ~3-5 分)
uv run python scripts/verify_with_whisper.py

# F0 計測
uv run python scripts/pitch_compare.py

# サマリ
uv run python scripts/summarize.py
```

## 参照音声

`reference/ref.wav` は 06-22 の同ファイル (男性、24kHz mono、~10 秒)。
比較の同一性を担保するため、ここでは変更しない。

## 期待される観察点

- **CER**: 06-22 で Qwen3-TTS が 7 言語中 6 言語で ≤ 0.05、zh のみ 0.20 だった。Chatterbox が JA / 欧州語で同等以上を出せるか
- **F0 保持**: Qwen3-TTS は es 以外で ±10Hz 以内。Chatterbox はどうか
- **Mac MPS**: Chatterbox は PyTorch 2.4+ / MPS 動作を確認済み
- **モデルサイズ**: Qwen3-TTS 0.6B → Chatterbox Multilingual 500M。VRAM / cold start への影響

## 参考

- [Chatterbox (GitHub)](https://github.com/resemble-ai/chatterbox)
- [Chatterbox Multilingual (Resemble AI)](https://www.resemble.ai/learn/models/chatterbox-multilingual)
- [06-22 多言語 voice clone ベンチ](../06-22-tts-commercial-provider-comparison/README.md)
- [06-22 Qwen3-TTS 詳細ノート](../06-22-tts-commercial-provider-comparison/qwen3-tts-notes.md)

## 依存関係のセキュリティについて

`uv.lock` は**記事執筆時点 (2026-07) のベンチ環境をそのまま再現するためのスナップショット**であり、意図的に更新していません (torch / transformers / diffusers は chatterbox 側の固定制約と密結合で、更新するとベンチ自体が再現できなくなる)。このため Dependabot が指摘する既知脆弱性が含まれます。ローカルの隔離環境で、信頼できるモデルのみを対象に実行してください。サーバーとして公開する用途を想定したコードではありません。
