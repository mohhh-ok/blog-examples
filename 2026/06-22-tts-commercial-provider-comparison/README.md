# 商用可能な voice clone TTS provider 比較

**やること**: 06-19 の多言語 voice clone ベンチで分かった「ElevenLabs > XTTS > OpenVoice > F5 (JP)」の品質順序を、**商用利用 OK** かつ **slot 上限が緩い** provider 群（Cartesia / Fish Audio / PlayHT / Azure Personal Voice 等）に拡張して再検証する。

**やらないこと**: MOS、声質主観評価、非商用ライセンス weights の再検証 (06-19 で済)。

## 背景

voice clone TTS を multi-tenant SaaS で運用するにあたり、ElevenLabs に対して以下 2 つの懸念が出てきた:

1. **voice slot 上限が低い** — Business plan でも 660 slot まで。multi-tenant で 1 ユーザー 1 voice 設計だと早期に天井。
2. **TTS 以外の機能 (Studio, Dubbing, Agents, SFX, Music) と抱き合わせ価格** — 本プロジェクトは API TTS しか使わないので不要機能ぶんを払っている。

TTS 特化 provider に切り替えれば **単価 3〜10 倍安く、slot 実質無制限**になる可能性がある。ただし日本語品質が ElevenLabs に届くかは未検証。

## provider 一覧 (2026/06 時点)

### 商用可能なもの (API 利用)

| Provider | 単価 (TTS) | voice clone | slot 上限 | License / 商用 | JP 評価 |
|---|---|---|---|---|---|
| **ElevenLabs** | $0.12〜0.20 / 1k chars | IVC (10秒〜2分) / PVC (30分+) | **Free 3 / Starter 10 / Creator 30 / Pro 160 / Scale/Business 660** | 商用可 (Starter $5〜) | 06-19 で 1 位 |
| **Cartesia Sonic 3** | $0.05 / 1k chars (PAYG) | Instant + PVC | **無制限** (credits 次第) | 商用可 | 未検証 |
| **Fish Audio (S2 Pro)** | $0.015 / 1k bytes ($15/1M) + $0.1/voice 登録 | 15秒 sample | **実質無制限** | 商用可 | 未検証 (06-19 比較対象外) |
| **PlayHT 2.0/3.0** | $0.030 / 1k chars | Instant | プラン依存 | 商用可 | 未検証 |
| **PlayHT Turbo** | $0.015 / 1k chars | Instant | プラン依存 | 商用可 | 未検証 (品質低めの噂) |
| **Azure Personal Voice** | $0.024 / 1k chars | Personal Voice (consent required) | エンタープライズ枠 | 商用可 (要 Limited Access 申請) | 未検証 |
| **Azure Custom Neural Voice** | $0.024 / 1k chars + $23.90/hr training | Custom training | エンタープライズ枠 | 商用可 (要申請) | 未検証 |
| **Resemble.ai** | プラン制 | Instant + PVC | プラン依存 | 商用可 | 未検証 |

### 商用不可 / 制約あり (参考、自社ホスト weights)

| Provider | weights License | 備考 |
|---|---|---|
| XTTS-v2 | CPML (非商用) | 06-19 で OSS 2 位。**Coqui が 2024 初頭に解散** → 商用ライセンス発行主体なし、実質商用詰み |
| F5-TTS | CC-BY-NC (非商用) | 06-19 で 4 位 (JP 破綻) |
| Fish Speech open weights | CC-BY-NC-SA | 商用は Fish Audio 商用 API へ |
| OpenVoice v2 | **MIT (商用可)** | 06-19 で 3 位 (JP 二線・DE 不可) |
| IndexTTS-2 | 非商用 (contact 要) | duration control が動画 dub に効く |
| Chatterbox | **MIT (商用可)** | EN 中心、JP 弱い |
| **Fun-CosyVoice 3 (Alibaba)** | **Apache 2.0 (商用可)** | code (GitHub `FunAudioLLM/CosyVoice`) / weights (HF `FunAudioLLM/Fun-CosyVoice3-0.5B-2512`) ともに Apache-2.0 確認済み。**9 言語サポート (zh/en/ja/ko/de/es/fr/it/ru) + 18+ 中国方言**、bi-directional streaming ~150ms。多言語 + JP 動く OSS 商用可の**ほぼ唯一の現実解** |
| **Qwen3-TTS (Alibaba Qwen)** | **Apache 2.0 (商用可)** | code (GitHub `QwenLM/Qwen3-TTS`) / weights (HF `Qwen/Qwen3-TTS-12Hz-*` 全 7 モデル) ともに Apache-2.0 確認済み。**10 言語サポート (zh/en/ja/ko/de/fr/ru/pt/es/it)**、3 秒参照で voice clone。公式論文値 WER 1.835% / SIM 0.789 で MiniMax/ElevenLabs 超え主張、JP 品質も高評価。Mac MPS で動作実証あり (float32 + sdpa 必須) |

## 規模別コスト試算 (200 chars/本想定)

| 月間本数 (chars) | ElevenLabs Scale | Cartesia PAYG | Fish Audio |
|---|---|---|---|
| 10,000本 (2M) | $330 | $100 | **$30** |
| 30,000本 (6M) | $990 (overage) | $300 | **$90** |
| 100,000本 (20M) | ~$2,670 (Business + overage) | $1,000 | **$300** |

100k本/月で **ElevenLabs vs Fish ≒ 9x** の差。年間 ~$28,000 浮く可能性。

## 検証対象 (本ベンチで実走するもの)

商用可能 + 06-19 未検証 を優先:

1. **Cartesia Sonic 3** (API) — 単価 / slot のバランス良
2. **Fish Audio S2 Pro** (API) — 最安、JP 品質次第で本命
3. **Azure Personal Voice** (API) — Microsoft の clone、JP 学習が厚い可能性
4. **CosyVoice 2** (self-host, Apache 2.0) — JA / EN / ZH / KO に強い旧世代モデル
5. **Fun-CosyVoice 3** (self-host, Apache 2.0) — 9 言語サポートだが JA は前処理 (kanji→katakana + は→わ) を要する
6. **Qwen3-TTS** (self-host, Apache 2.0) — 10 言語サポート、3 秒参照で clone。Mac MPS で動作、CosyVoice 3 の `contains_chinese()` バグ系を持たないと想定
7. **OpenVoice v2** (06-19 結果を流用) — MIT、設定見直しは効果薄と判断

**CosyVoice の実測結果と JA 劣化バグの切り分けは [`cosyvoice-notes.md`](./cosyvoice-notes.md) を参照**。v2 と v3 で得意領域が大きく違うこと、v3 の JA は単純な kanji 入力だと CER 0.25 で崩壊することなど、想定外のトレードオフが出ている。

ベースライン: **ElevenLabs** (06-19 と同条件で 1 回走らせる、参照点として)

## 検証方法

06-19 のフレームワーク (`../06-19-multilingual-voice-cloning-benchmark/`) を流用:

- **参照音声**: 同 `reference/ref.wav` (10 秒、自分の声、24kHz mono)
- **生成テキスト**: `prompts.py` の 7 言語ぶん (本プロジェクトの主眼は JP だが多言語ぶんも記録)
- **検証**: Whisper large-v3 で書き起こし → WER / CER / bigram 類似度
- **追加メタ**: 各 provider の (a) 登録レイテンシ (b) TTS レイテンシ (c) 連続合成での声安定性 を記録

### ディレクトリ構成 (予定)

```
.
├── README.md (this file)
├── prompts.py                          # ../06-19 から symlink or copy
├── reference/                          # ref.wav (gitignore, ../06-19 から symlink)
├── output/                             # 生成 wav (gitignore)
├── results/                            # WER/CER/サマリ (gitignore)
├── scripts/
│   ├── generate_cartesia.py
│   ├── generate_fish.py
│   ├── generate_azure_personal.py
│   ├── generate_cosyvoice3.py
│   ├── generate_qwen3_tts.py
│   ├── generate_openvoice_v2.py        # 再走 (設定見直し)
│   ├── generate_elevenlabs.py          # ベースライン再走
│   ├── verify_with_whisper.py          # 06-19 と同じ
│   └── summarize.py                    # CSV + Markdown
└── envs/
    ├── cosyvoice3.md                   # self-host venv セットアップ
    └── qwen3_tts.md                    # self-host venv セットアップ (Mac MPS)
```

## 判定基準

採用優先順位:

1. **JP WER が ElevenLabs +3pt 以内** に収まること (主指標)
2. **商用 API が明確に提供** されている (License 解釈リスクが無い)
3. **voice slot 上限が 1000+ または無制限**
4. **単価が ElevenLabs Scale の 1/3 以下**

(1) を満たさない provider は不採用。(1) を満たす中で (2)(3)(4) を満たすものを採用候補。

## license の落とし穴メモ

- **CC-BY-NC** 系 (F5-TTS, Fish Speech open weights, XTTS-v2) は **収益が出る用途は全部 NG**。SaaS は当然不可、社内ツールも「業務利益に貢献するなら商用」とみなす解釈が一般的。
- **CPML (XTTS-v2)** は Coqui の独自ライセンス。`#commercial use` フィールドあり別途契約が必要だが、**Coqui は 2024 年初頭に解散** (スタッフ放出 → holding 化) しており、商用ライセンスを発行できる主体がそもそも存在しない。Replicate 等の API 経由でも CPML は外れないので production 投入は法的に詰む。
- **Apache 2.0 / MIT** は明確に商用 OK。NOTICE / LICENSE の同梱を忘れない。多言語 voice clone OSS で「商用 OK + JP 動く」は **Fun-CosyVoice 3 (Apache-2.0) がほぼ唯一**。OpenVoice v2 / Chatterbox (MIT) は JP 品質が劣る。
- **Azure Personal Voice** は MS の **Responsible AI 規約**で「話者本人の明示的 consent」必須。SaaS UI に consent flow を入れる必要あり。

## 次アクション

- [ ] 06-19 の `reference/ref.wav` と `prompts.py` を symlink で持ってくる
- [ ] Cartesia / Fish / Azure の API key を取得 (試用枠)
- [ ] generate_*.py を 06-19 のテンプレートから雛形作成
- [ ] Fun-CosyVoice 3 self-host 環境構築 (envs/cosyvoice3.md)
- [ ] Qwen3-TTS self-host 環境構築 (envs/qwen3_tts.md、Mac MPS、0.6B-Base 先行)
- [ ] 全 provider で 7 言語生成 → Whisper 検証 → summarize.py
- [ ] 結果次第で本番プロジェクトのコスト docs / architecture を更新 (provider 差し替え)

## 関連

- 06-19 ベンチ: `../06-19-multilingual-voice-cloning-benchmark/`

## 参考 URL

- ElevenLabs voice slots: https://help.elevenlabs.io/hc/en-us/articles/24351056337937
- Cartesia Pricing: https://www.cartesia.ai/pricing
- Cartesia Pro Voice Cloning (unlimited slots): https://www.cartesia.ai/blog/pro-voice-cloning/
- Fish Audio Pricing: https://fish.audio/plan/
- Fish Audio Rate Limits: https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits
- PlayHT Pricing: https://play.ht/pricing/
- Azure TTS Pricing: https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/
- Fun-CosyVoice 3: https://github.com/FunAudioLLM/CosyVoice (HF: https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B)
- Qwen3-TTS: https://github.com/QwenLM/Qwen3-TTS (HF: https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base / blog: https://qwen.ai/blog?id=qwen3tts-0115)
- OpenVoice v2: https://github.com/myshell-ai/OpenVoice
- Chatterbox: https://github.com/resemble-ai/chatterbox
