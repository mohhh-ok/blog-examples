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

## Cloud Run GPU 運用コスト試算

本番展開は **Cloud Run GPU (NVIDIA L4, Tier 1 Tokyo region) 前提**。Mac MPS は検証用で、production GPU では bfloat16 化 (issue #333 は MPS 限定なので CUDA では適用可) で更に高速化見込み。

### per-second 単価 (L4 最小構成)

L4 を使う場合 vCPU 4 + memory 16 GiB が最小要件 (Cloud Run 規約)。

| 項目 | 単価 | 最小構成 |
|---|---:|---|
| GPU (L4, no zonal redundancy) | $0.000187 / sec | 1 |
| vCPU (instance-based billing) | $0.000018 / sec | 4 必須 |
| Memory | $0.000002 / GiB-sec | 16 GiB 必須 |
| **合計** | **$0.000291 / sec** | ≈ **$1.05 / 時 / $756 / 月** (min=1 換算) |

### per-request 単価 (200 chars = 7 sec audio)

L4 の RTF 推定は **0.5〜0.7** (公式 H100 値 0.288 の 1.7〜2.4 倍時間)。concurrency 6 まで batch 可能で per-req 時間は 1/6 弱まで圧縮できる。

| シナリオ | 1 req の active sec | per req $ | per req JPY (150円換算) |
|---|---:|---:|---:|
| concurrency 1, RTF 0.7 (悲観) | 4.9 sec | $0.00143 | **0.21 円** |
| concurrency 1, RTF 0.5 (中央) | 3.5 sec | $0.00102 | **0.15 円** |
| concurrency 6 batch, RTF 0.5 | 0.58 sec | $0.00017 | **0.025 円** |

### min-instances=1 (常時 warm) での per-req 按分

GPU は scale-to-zero すると **cold start ~30 秒** (model load 2.3GB) を伴うため、interactive SaaS では `min-instances=1` 固定が現実解。固定費 $756/月 をリクエスト数で按分:

| 月間 req | 月額 (固定) | per req JPY |
|---:|---:|---:|
| 1,000 | $756 | 113 円 (論外) |
| 10,000 | $756 | **11.4 円** |
| 30,000 | $756 | **3.8 円** |
| 100,000 | $756 | **1.14 円** |
| 300,000 | $756 | **0.38 円** |
| 500,000 | $756 | **0.23 円** |

### API provider との per-req 比較 (200 chars)

| provider | per req | JPY | vs Qwen3 (batch 6) |
|---|---:|---:|---:|
| ElevenLabs Scale | $0.024〜0.040 | 3.6〜6 円 | **140〜240x 高** |
| PlayHT 2.0 | $0.006 | 0.9 円 | 35x 高 |
| Cartesia PAYG | $0.010 | 1.5 円 | 60x 高 |
| Fish Audio S2 Pro | $0.003 | 0.45 円 | 18x 高 |
| Azure Personal Voice | $0.005 | 0.7 円 | 28x 高 |
| **Cloud Run L4 (batch 6)** | **$0.00017** | **0.025 円** | (基準) |
| Cloud Run L4 (concurrency 1) | $0.001 | 0.15 円 | 6x 高 (自社内比較) |

### 損益分岐 (vs Fish Audio API)

Fish Audio は API として最安だが (B2B で地政学要件に引っかかる場合は採用不可)。

| 月間 req | Cloud Run 固定 | Fish Audio | 勝者 |
|---:|---:|---:|---|
| 10,000 | $756 | **$30** | Fish が 25x 安 |
| 30,000 | $756 | **$90** | Fish が 8x 安 |
| 100,000 | $756 | **$300** | Fish が 2.5x 安 |
| 300,000 | **$756** | $900 | **Cloud Run 逆転** (1.2x 安) |
| 500,000 | **$756** | $1,500 | Cloud Run が 2x 安 |
| 1,000,000 | **$756** | $3,000 | Cloud Run が 4x 安 |

**non-interactive job (batch mode)** は別系統で、どんな規模でも Cloud Run が圧勝 ($0.025 円/req)。

### egress / 補助コスト

| 項目 | per req 上乗せ |
|---|---:|
| wav 24kHz mono float32 (7s = ~700KB) egress | +0.13 円 |
| **MP3 64kbps (7s = ~56KB) egress** | **+0.01 円** |
| GCS / Cloud Storage cache (任意) | 微々 |
| Cloud Logging / Monitoring | base 無料枠あり |

**MP3 化前提なら egress 込みでも 1 円切るのは確実**。

### 結論: per-req 0.15〜1.14 円のレンジ

| 状況 | per req |
|---|---:|
| concurrency 6 batch (非同期 job) | **0.025〜0.05 円** |
| 月 100k req + min=1 interactive | **1.14 円** |
| 月 300k req + min=1 interactive | **0.38 円** |
| 月 10k req + min=1 interactive | 11.4 円 (この規模では API の方が安い) |

ElevenLabs Scale ($0.024〜0.040 / req) と比べて **140〜240 倍安い世界**。これが意味するのは:
- 100k req/月のサービスで **年間 ~$24,000 浮く** (vs ElevenLabs)
- **per-user 課金が現実的になる** — ユーザー 1 人当たり 10 req/月で 1.5 円弱、サブスク料金内に余裕で押し込める
- **多言語サポートのコストが事実上タダ** — UI 言語切替やローカライズ施策の意思決定が変わる

ElevenLabs 想定で「TTS コスト高いから機能制限しよう」と考えていた制約は、Qwen3-TTS + Cloud Run 採用で原則消える。

### voice_clone_prompt キャッシュによる最適化余地

上記試算は **`ref_audio=` を毎リクエスト渡す前提** (本ベンチの `generate_qwen3_tts.py` と同じ)。
production では `model.create_voice_clone_prompt()` で事前計算 + キャッシュすることで **25〜30% 短縮**できる:

```python
# 登録時 (1 回):
prompts = model.create_voice_clone_prompt(ref_audio, ref_text)  # 5KB tensor 群を返す
redis.set(voice_id, pickle.dumps(prompts))

# TTS 時 (毎回):
cached = pickle.loads(redis.get(voice_id))
model.generate_voice_clone(text=..., voice_clone_prompt=cached)  # ref_audio 不要
```

効果:
- GPU の speech_tokenizer.encode + extract_speaker_embedding を skip (~1 sec / req 短縮)
- L4 上の 1 req active sec: 3.5s → 2.5s 程度 (concurrency 1 / RTF 0.5 換算)
- per req 0.15 円 → **0.11 円** (約 27% 安)
- network: ref.wav (~700KB) を毎回送らなくて済む
- voice tensor は **1 voice ~5KB** (ref_code 240B + ref_spk_embedding 4KB) なので DB / Redis に何百万件でも乗る

ただし副作用が重い:

| 何が増える | コスト |
|---|---|
| Voice registration 専用 endpoint / service | エンジニアリング工数 |
| precompute prompt のキャッシュ層 (Redis / GCS / DB) | infra 1 つ追加 |
| シリアライズ format 選択 (pickle はバージョン依存リスク、torch.save / msgpack 等) | バグ温床 |
| voice 削除 / 更新時の cache invalidation | 状態管理問題 |
| **upload endpoint が GPU 依存になる** (`create_voice_clone_prompt` は GPU 必須) | アーキの密結合 / job queue で剥がすと eventual consistency |

#### 現実的な進化パス

| 段階 | 構成 | per req コスト |
|---|---|---|
| **MVP / prototype** | ref.wav を GCS に置き URL を毎回 `ref_audio=` に渡す | 0.15 円 (毎回 encode) |
| **scale 上がってきた頃** | TTS service の側で in-memory LRU cache (`{ref_url → prompt_tensor}`)。再起動で消えるが副作用ほぼ無し | 0.12 円 (warm cache hit 時) |
| **multi-tenant 本気運用** | voice registration を別 service + persistent cache、prompt tensor を DB 永続化 | 0.11 円 + 別 service の運用負荷 |

本ベンチの per-req 試算 (0.15〜1.14 円) は **MVP 段階の pessimistic な数字**。
voice cache を入れる頃には実装複雑性を払う合理性が出ているはずなので、悪い見立てではない。

### Caveats

- **L4 上の RTF は実測していない推定値**。production 投入前に実機ベンチ必須
- **bfloat16 化 (CUDA) で 1.5〜2x 速くなる**見込みだが未検証。Cloud Run L4 で実走すると更に安くなる可能性
- **concurrency 6 batch 前提は VRAM 24GB の L4 で安全圏のはず** (0.6B モデルなら) が、実 VRAM 占有も未計測
- 1.7B-Base にすると VRAM・推論時間とも 2〜3 倍。scale-to-zero ケースで $150〜200/月程度に上振れ
- Cloud Run 以外の選択肢 (GCE 直で L4 spot $0.28/時、A10G オンプレ等) で更に半額狙えるが運用負荷増
- 上記コスト試算は **voice_clone_prompt キャッシュ無し** (毎回 ref_audio 渡し) 前提。キャッシュ実装で 25〜30% 安くなるが、実装複雑性とのトレードオフ (上記セクション参照)

## 結論 (本ベンチの判定基準照合)

1. ✓ **JP CER 0.045** — ElevenLabs +3pt 以内ライン超え (主指標クリア)
2. ✓ **Apache 2.0 商用 OK** — License 解釈リスク無し
3. ✓ **slot 無制限** (self-host)
4. ✓ **単価** = Cloud Run L4 想定で **per req 0.15〜1.14 円**、月 300k req 以上で Fish Audio API に逆転勝ち
5. ✓ **地政学** — GCP Tokyo region で self-host すれば中国本土を経由しない (README の判定基準 5)

**zh を主要言語に含めない限り、本ベンチで採用候補筆頭**。
CosyVoice 3 (前処理必要) / CosyVoice 2 (他言語崩壊) の弱点をどちらも持たない。
ElevenLabs より声質保持が強いので、「自分の声を多言語で使いたい」用途では本モデルの方が
ユーザー体験的に優れる可能性がある (要 voice similarity 計測で裏付け)。
