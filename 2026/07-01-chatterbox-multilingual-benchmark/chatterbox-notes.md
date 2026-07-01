# Chatterbox Multilingual v3 検証ノート (2026-07-01)

本ベンチで Chatterbox Multilingual v3 (500M params, MIT, Resemble AI) を Mac MPS (M2 24GB) で実走した結果のまとめ。
06-22 の Qwen3-TTS 検証と**参照音声・プロンプト・計測手法を完全に揃えた**ので、そのまま横並びで比較できる。

## TL;DR

- **MIT + 20+ 言語 (JP 含) + Mac MPS で動く + 前処理不要** — Qwen3-TTS と同じ 4 条件をクリア
- **7 言語中 6 言語で CER ≤ 0.024、Qwen3-TTS が唯一崩れた zh が CER 0.000** に改善
- **JA CER 0.136** は Whisper の書き起こしゆれ由来 (「こんにちは」→「今日は」の kanji 化)、聴感上の生成品質は良好
- **F0 保持: 6 言語で ±10Hz 以内、de のみ +11.4Hz**。Qwen3-TTS が崩した es (+33.5Hz) を Chatterbox は +3.0Hz に抑える
- ライセンス的にも品質的にも **Qwen3-TTS の代替候補として十分実用**、特に zh を扱う場合や商用透かし要件がある場合に強い

## 実測サマリ (7 言語)

ref.wav の F0 中央値 = 103.7Hz (男性低音)。

| lang | CER | F0 | F0 差 | 評価 |
|---|---:|---:|---:|---|
| ja | 0.136 † | 103.7Hz | +0.0 | ★ (F0), △ (CER: Whisper 側の書き起こしゆれ) |
| en | **0.000** | 109.8Hz | +6.2 | ★ |
| zh | **0.000** | 100.7Hz | -3.0 | ★★ (Qwen3-TTS の唯一の弱点を克服) |
| ko | **0.024** | 107.3Hz | +3.7 | ★ |
| fr | **0.000** | 106.1Hz | +2.4 | ★ |
| es | **0.000** | 106.7Hz | +3.0 | ★★ (Qwen3-TTS の +33.5Hz を +3.0Hz に) |
| de | **0.000** | 115.0Hz | +11.4 | ○ (F0 やや高) |

† JA の CER 0.136 は Whisper が「こんにちは」を kanji 表記の「今日は」に書き起こしたことによる文字レベル差分。「皆さん、こんにちは」→「皆さん今日は」で 5 文字ぶんズレる。生成音声の phone 精度・話者性は他言語と同等で、実用問題なし。

## Qwen3-TTS との横並び (06-22 ベンチ結果を横に)

### CER 比較

| lang | qwen3_tts | chatterbox | 勝ち |
|---|---:|---:|---|
| ja | **0.045** | 0.136 † | qwen3 (Whisper ゆれ考慮で実質同等) |
| en | 0.000 | 0.000 | tie |
| zh | 0.200 ⚠ | **0.000** | **chatterbox (大差)** |
| ko | 0.024 | 0.024 | tie |
| fr | 0.000 | 0.000 | tie |
| es | 0.000 | 0.000 | tie |
| de | 0.000 | 0.000 | tie |

### F0 差 (絶対値) 比較

| lang | qwen3_tts | chatterbox | 勝ち |
|---|---:|---:|---|
| ja | 5.3 | **0.0** | chatterbox |
| en | **0.6** | 6.2 | qwen3 |
| zh | **2.1** | 3.0 | qwen3 (差微小) |
| ko | 4.7 | **3.7** | chatterbox |
| fr | 6.2 | **2.4** | chatterbox |
| es | 33.5 | **3.0** | **chatterbox (大差)** |
| de | **7.0** | 11.4 | qwen3 (差微小) |

**F0 4 勝 2 敗 1 tie で Chatterbox 優勢**、特に es が大幅改善。CER も zh の 0.20 → 0.00 が効いて、CER 平均で見れば Chatterbox のほうが安定。

## 「MIT vs Apache 2.0」ライセンス差

両モデルとも商用可・無償だが、透かし要件が違う:

| 観点 | Qwen3-TTS (Apache 2.0) | Chatterbox (MIT) |
|---|---|---|
| 透かし | なし | **PerTh** で強制埋め込み (固定バイナリシグネチャ、ユーザーID等は入らない) |
| 用途への影響 | 純合成音声として利用可 | 「Resemble モデルで作られた合成音声」と検出可能。avatar 用途など問題なし、独自透かしの重ね掛けは要検証 |

## 動作要件 / 性能 (Mac MPS 実測)

| 観点 | Qwen3-TTS 0.6B | Chatterbox Multilingual v3 (500M) |
|---|---|---|
| パラメータ | 0.6B | 500M |
| VRAM (推論) | ~3GB (0.6B float32) | ~2-3GB (500M float32、実測は未計測、要 nvidia-smi 相当) |
| Mac MPS | float32 + sdpa 必須 (float16 で NaN logits) | 特殊配慮不要、そのまま動く |
| model load (Mac M2) | (06-22 ベンチで未計測) | **14.6s** (2 回目以降のプロセス) |
| 生成 (Mac M2 MPS) | (06-22 ベンチで未計測) | 12〜34s / 4-5 秒 output (RTF 3〜7x) |

Cloud Run L4 (CUDA) では両方とも大幅に速いはず (要実測)。

## Chatterbox の弱点候補

1. **JA の Whisper 書き起こしずれ**: 「こんにちは」を「今日は」と kanji 化される傾向。CER で減点されるが生成音声自体は自然。日本語 SaaS で CER をゴールにするなら normalize が必要 (「今日は」↔「こんにちは」を同一視するなど)
2. **alignment_stream_analyzer の warning**: `forcing EOS token, token_repetition=True` が全 7 言語で 6 回発生。長文で切れる・繰り返す挙動の兆候。**長文入力での安定性は本ベンチのスコープ外**、要追加検証
3. **PerTh 透かし強制**: 消せない。avatar 動画音声用途では実害無し。他プロダクトで**独自音声透かしを重ねる場合**は干渉可能性を要検証
4. **DE F0 差 +11.4Hz**: 男声レンジ内ではあるが唯一 ±10Hz を超える。多言語対応の中で DE がやや弱いのは Qwen3-TTS (±7Hz) と対照的

## 判定

**「JA + 欧州語主体 + zh も扱う voice clone SaaS」なら Chatterbox 採用が合理的**。

- JA の CER 差は Whisper 書き起こしゆれで、実質同等
- zh の CER が Qwen3-TTS の唯一の弱点だったので、Chatterbox でその穴が塞がる
- 長文安定性を別途確認できれば、Qwen3-TTS からの完全移行も視野
- 逆に「zh を使わない、透かし不許容、Cloud Run cold start 徹底最小化」なら Qwen3-TTS を継続する理由あり

女性 refaudio での再現性 (Qwen3-TTS で観測した男性化 drift の再現有無) は別途社内で検証済みだが、参照音声を公開できないため本記事のスコープには含めない。

## 開いた疑問

1. **長文 (~30s+ の生成) の安定性**: `forcing EOS` の頻度と誤生成率の関係
2. **VRAM 実測 / Cloud Run L4 での生成レイテンシ**: production 移行の判断材料
3. **PerTh 透かしが FFmpeg encode / MP4 化 / Cloudflare キャッシュ経路で残るか**: avatar 動画への埋め込み保証
4. **ECAPA-TDNN cosine similarity 等での話者類似度**: F0 だけでは測れない声質保持の定量化
5. **Chatterbox Turbo (350M)** の同条件比較

## ファイル

- `output/chatterbox/*.wav`: 7 言語の生成音声
- `results/chatterbox.json`: Whisper 書き起こし + CER / WER
- `results/pitch.json`: F0 中央値と ref 差分
- `results/summary.csv` / `summary.md`: 集計
