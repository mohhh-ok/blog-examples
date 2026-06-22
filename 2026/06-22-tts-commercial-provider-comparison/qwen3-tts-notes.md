# Qwen3-TTS 検証ノート (2026-06-22)

本ベンチで Qwen3-TTS 0.6B-Base を Mac MPS (M2 24GB) で実走した結果のまとめ。
**「voice clone を CER だけで測ると見えない、声質保持の軸」が浮かび上がった**ので、
事実関係に加えて質的観察を残す。

CosyVoice 2/3 の詳細は [`cosyvoice-notes.md`](./cosyvoice-notes.md) を参照。
本書は **Qwen3-TTS 専用ノート**。

## TL;DR

- **Apache 2.0 + 10 言語 + Mac MPS で動く + 前処理不要** の四条件を満たす初の voice clone モデル
- 7 言語中 **5 言語で CER 0.000、JA で 0.045** — CosyVoice 3 の致命的な JA kanji 経路バグが無い
- 唯一の弱点が **zh CER 0.20** ("功能" → "新货" の置換)。voice clone 由来の音響バイアス疑い
- **声質保持が圧倒的に強い** — 全 7 言語で F0 差 ±34Hz、ja/en/de で ±10Hz 以内。
  ElevenLabs のように「英語ネイティブ風」に矯正されず、**元話者の音響特徴を保ったまま** 多言語化する
- 商用採用判定: 本ベンチの基準 (1)(2)(3)(4) すべてクリア。**JA 主体の SaaS なら採用候補筆頭**

## 実測サマリ

ref.wav の F0 中央値 = 104.9Hz (男性低音域)。

### Qwen3-TTS 0.6B-Base, 7 言語

| lang | CER | F0 | F0 差 | 評価 |
|---|---:|---:|---:|---|
| ja | **0.045** | 99.6Hz | −5.3 | ★ |
| en | **0.000** | 105.5Hz | +0.6 | ★ |
| zh | 0.200 | 102.8Hz | −2.1 | ⚠ CER のみ問題 |
| ko | **0.024** | 100.1Hz | −4.7 | ★ |
| fr | **0.000** | 111.1Hz | +6.2 | ★ |
| es | **0.000** | 138.4Hz | +33.5 | F0 やや高 (女性化なし) |
| de | **0.000** | 97.9Hz | −7.0 | ★ |

### 全モデル横断 (CER)

| lang | cosyvoice2 | cosyvoice3 | **qwen3_tts** | openvoice_v2 |
|---|---:|---:|---:|---:|
| ja | **0.023** | 0.250 ✕ | **0.045** ★ | 0.114 |
| en | 0.000 | 0.000 | **0.000** | 0.000 |
| zh | 0.000 | 0.000 | **0.200** ⚠ | 0.080 |
| ko | 0.024 | 0.024 | **0.024** | 0.049 |
| fr | 0.324 ✕ | 0.000 | **0.000** | 0.000 |
| es | 0.165 | 0.047 | **0.000** | 0.000 |
| de | 0.875 ✕ | 0.125 | **0.000** | n/a |

Qwen3-TTS は **7 言語中 6 言語で実用品質 (CER ≤ 0.05)**、CosyVoice 2 (de/fr/zh で破綻) や
CosyVoice 3 (JA で破綻) のように「特定言語が崩れる」現象が無い。zh のみ要再検証。

## 「声質保持 / 話者愛着」軸の発見

CER と bigram 類似度だけ見ていると、ElevenLabs (06-19 で 1 位) と Qwen3-TTS は同等に見える。
しかし**聴感上は別物**:

| モデル | EN を喋らせた時の聴感 | 質的特徴 |
|---|---|---|
| ElevenLabs (06-19 IVC) | 英語ネイティブ話者風に滑らか化、**元の声の癖が薄まる** | 自然さ最優先、accent neutralization 強い |
| Qwen3-TTS | **元話者の音色を保ったまま英語を喋る**、若干カタコト寄り | 声質保持最優先、accent retention |

**multi-tenant SaaS で「ユーザー自身の声」を売りにする場合は Qwen3-TTS の方が向いている**。
ユーザーから見て「これ私の声だ」と感じられる再現性は、accent neutralization で失われる方向に動く。
逆に「accent の無い綺麗な英語ナレーション」が欲しいなら ElevenLabs。

設計思想の差なので、用途で使い分けるべき軸。本ベンチでは F0 差で間接的に測れるが、
本当は voice similarity (ECAPA-TDNN cosine 等) の追加計測が望ましい。

### F0 から見た声質保持

| モデル | ja | en | de | fr | es | ko | zh | 備考 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| ref.wav | 104.9 | - | - | - | - | - | - | 基準 (男性低音) |
| **qwen3_tts F0 差** | −5 | +1 | −7 | +6 | **+34** | −5 | −2 | es だけやや高、他は完璧 |
| cosyvoice2 F0 差 | −8 | +4 | **+185** ⚠ | (重複) | (長尺) | −30 | **+187** ⚠ | zh/de で女性化 |
| cosyvoice3 F0 差 | +1 | +7 | +2 | +1 | +4 | +3 | −8 | 全部安定だが JA は別問題 (CER 0.25) |
| openvoice_v2 F0 差 | 0 | +29 | n/a | +5 | +2 | −2 | +2 | en で +29、JA は安定 |

Qwen3-TTS は **es 以外の 6 言語で F0 差 ±10Hz 以内**。CosyVoice 3 と並んで「全言語で声質保持」を
達成している希少なモデル。

## zh 劣化の謎

zh の got 文字列を見ると、原文の意味が一部置換されている:

```
expected: 大家好,今天我将为大家介绍一项新功能,感谢您的参与
got:      大家好,今天我再为大家介绍一款新货的感谢您的参与
                      ^^      ^^^^^^^
                  「将」→「再」    「一项新功能」→「一款新货」
```

「新機能」が「新商品」に化けている。Whisper hallucination というより、
**生成音声側で 「功能 (機能)」を 「新货 (新商品)」と発音してしまっている** 可能性が高い。
voice clone で元話者の **日本訛りの中国語** を再現してしまい、Whisper がそれを別単語として
聞き取った、というシナリオが整合する。

### 検証すべきこと

1. **サンプリング揺れ**: CosyVoice 3 で確認された「同入力で CER 0.125〜0.458 変動」が
   Qwen3-TTS にもあるか。3 回試走して中央値を取れば 0.20 が安定するか確認
2. **1.7B-Base での再走**: 大きい LLM で中国語の固有名詞 / 専門語の bias が改善するか
3. **ref.wav の影響**: 中国語ネイティブの参照音声で同じテキストを clone したら CER 0 になるか
   (= 元話者バイアスが原因か、モデル本体の zh 弱さか の切り分け)

## CosyVoice 3 との比較で見える Qwen3-TTS の優位

| 観点 | CosyVoice 3 | Qwen3-TTS | 勝ち |
|---|---|---|---|
| JA 直入力 (kanji) | CER 0.25 ✕ | **CER 0.045** | Qwen3 |
| JA 前処理込み | CER 0.045 (kana 変換 + は→わ) | **CER 0.045 (前処理不要)** | Qwen3 |
| 多言語 (en/de/fr/es) | 全部 CER ≤ 0.125 | **全部 CER ≤ 0.000** | Qwen3 |
| zh | CER 0.000 | CER 0.200 ⚠ | CosyVoice 3 |
| 声質保持 (F0) | 全言語安定 | 全言語安定 | 同等 |
| ライセンス | Apache 2.0 | Apache 2.0 | 同等 |
| Mac MPS 動作 | CPU のみ | **MPS 動作** | Qwen3 |
| 公式サポート言語 | 9 言語 | 10 言語 (ru 追加) | Qwen3 |
| `<\|endofprompt\|>` 必須 | あり | **不要** | Qwen3 |

**JA + 欧州語の voice clone 用途では Qwen3-TTS が CosyVoice 3 の上位互換**。
zh が必要な場合のみ CosyVoice 3 を併用する。

## 既知の制約 / 開いた疑問

### 制約

- **MPS 上 float16 / bfloat16 で NaN logits** ([issue #333](https://github.com/QwenLM/Qwen3-TTS/issues/333))。
  voice clone は必ず float32。M2 24GB で 0.6B 推論 ~3GB、1.7B は ~10GB で他アプリ閉じる前提
- **FlashAttention 2 は CUDA 専用**。Mac では `attn_implementation="sdpa"` を明示
- **`sox: command not found` warning** が import 時に出るが、推論には影響しない (本ベンチで確認)

### 開いた疑問

1. zh CER 0.20 がサンプリング揺れか、モデル本体の bias かの切り分け
2. 1.7B-Base が 0.6B-Base に対してどの言語で改善するか (特に zh / JA)
3. CustomVoice / VoiceDesign モデルの品質と clone 系との比較
4. `temperature` / `top_p` / `repetition_penalty` を制御することで zh が安定するか
5. ElevenLabs vs Qwen3-TTS の声質保持の差を ECAPA-TDNN cosine similarity で定量化できるか
6. 06-19 で見た「ElevenLabs 英語ペラペラ化」現象を Whisper 以外の指標で再現性高く測れるか

## ファイル

### スクリプト

- `scripts/generate_qwen3_tts.py` — 7 言語生成 (`mps` + `float32` + `sdpa` 固定)
- `scripts/verify_with_whisper.py` — CER / bigram 計測 (MODELS に `qwen3_tts` 追加)
- `scripts/pitch_compare_all.py` — F0 比較 (CER で見えない声質崩壊検出)

### 環境

- `envs/qwen3_tts.md` — Python 3.11.8 + qwen-tts PyPI + 0.6B-Base DL 手順

### 出力

- `output/qwen3_tts/{ja,en,zh,ko,fr,es,de}.wav` — 7 言語生成物 (24kHz mono float32)

### 結果

- `results/qwen3_tts.json` — Whisper large-v3 評価 (CER / WER / bigram)
- `results/summary.{csv,md}` — 全モデル × 全言語サマリ (qwen3_tts 行追加済み)

## 結論 (本ベンチの判定基準照合)

1. ✓ **JP CER 0.045** — ElevenLabs +3pt 以内ライン超え (主指標クリア)
2. ✓ **Apache 2.0 商用 OK** — License 解釈リスク無し
3. ✓ **slot 無制限** (self-host)
4. ✓ **単価** = 自社 GPU/CPU コストのみ (Mac MPS で 1 言語 ~20 秒 / 0.6B)

**zh を主要 言語に含めない限り、本ベンチで採用候補筆頭**。
CosyVoice 3 (前処理必要) / CosyVoice 2 (他言語崩壊) の弱点をどちらも持たない。
ElevenLabs より声質保持が強いので、「自分の声を多言語で使いたい」用途では本モデルの方が
ユーザー体験的に優れる可能性がある (要 voice similarity 計測で裏付け)。
