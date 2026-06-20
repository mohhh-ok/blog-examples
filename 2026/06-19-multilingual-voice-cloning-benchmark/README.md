# 多言語ボイスクローンTTSベンチマーク（F5-TTS / XTTS-v2 / OpenVoice v2 / Style-Bert-VITS2 / ElevenLabs）

**やること**：日本語1本の参照音声で 7 言語（ja / en / zh / ko / fr / es / de）をゼロショット生成し、**Whisper large-v3** で書き起こして「期待テキストとどれだけ一致するか」を機械的に測る。複数のクローンTTSモデルで横並びに比較する。

**やらないこと**：MOS（人手評価）、声質の主観評価、商用クラウド全網羅。

> 背景: F5-TTS は学習データが英中ベース（Emilia 10万時間）で日本語/韓国語の評価が論文に載っていない。XTTS-v2 / OpenVoice v2 / ElevenLabs は多言語サポートを公式に謳う。Style-Bert-VITS2 JP-Extra は日本語特化で fine-tune 前提。これらを**同じ参照音声・同じ生成テキスト**で並べる。

## ディレクトリ構成

```
.
├── README.md
├── prompts.py                       # 共通: ref_text + 7言語のgen_text
├── reference/                       # 参照音声 (gitignore)
│   └── ref.wav                      # 自分の声を10秒前後、24kHz mono
├── output/                          # 生成wav (gitignore)
├── results/                         # Whisper検証JSON/CSV/MD (gitignore)
├── scripts/
│   ├── generate_f5_tts.py
│   ├── generate_xtts.py
│   ├── generate_openvoice.py
│   ├── generate_style_bert_vits2.py
│   ├── generate_elevenlabs.py
│   ├── verify_with_whisper.py       # WER / CER / bigram類似度
│   └── summarize.py                 # CSV + Markdown表
└── envs/
    ├── openvoice.md
    └── sbv2.md
```

各モデルで依存と Python バージョン要件がバラバラなので **1モデル = 1 venv** で分離する。

## 共通設定

### 参照音声

`reference/ref.wav` に**自分の声**で 10 秒前後の音声を 1 本置く。24kHz mono 推奨。

> ⚠ 他人の声・芸能人の声をクローンしない。人格権・パブリシティ権の問題が出る。

読み上げ原稿（`prompts.py` の `REF_TEXT` と一致させる）:

> 本日はお忙しい中お越しいただき、誠にありがとうございます。それでは、プロジェクトの進捗状況について、簡単にご説明させていただきます。

濁音・拗音・促音・撥音・長音を含めた構成。

### 生成テキスト

7 言語ぶんを `prompts.py` に固定。固有のプロダクト名・社名は含めない（**Whisper の固有名詞ミスとモデルの破綻を切り分けるため**）。

## モデル別セットアップ

### 1. F5-TTS

[github.com/SWivid/F5-TTS](https://github.com/SWivid/F5-TTS) — Flow Matching ベース。学習データは英中中心。**ライセンス CC-BY-NC 4.0 (非商用)**。

```bash
python3.11 -m venv envs/f5-tts
source envs/f5-tts/bin/activate
pip install f5-tts torch torchaudio soundfile
python scripts/generate_f5_tts.py
```

### 2. XTTS-v2 (Coqui)

[github.com/coqui-ai/TTS](https://github.com/coqui-ai/TTS) — 13 言語サポート、ボイスクローン対応。**ライセンス Coqui Public Model License**。

```bash
python3.11 -m venv envs/xtts
source envs/xtts/bin/activate
pip install TTS faster-whisper jiwer
# TTS 0.22.0 が transformers 5.x と非互換 (BeamSearchScorer 削除済み)
pip install 'transformers<4.41'
# 新しい torchaudio が torchcodec バックエンド必須、日本語前処理に cutlet+unidic-lite 必要
pip install torchcodec cutlet unidic-lite
COQUI_TOS_AGREED=1 python scripts/generate_xtts.py
```

XTTS は ja/en/zh/ko/fr/es/de を**全てサポート**。

PyTorch 2.6+ は `torch.load` の `weights_only=True` がデフォルト化されたため、`scripts/generate_xtts.py` 冒頭で `torch.serialization.add_safe_globals([XttsConfig, ...])` を呼んでいる。

### 3. OpenVoice v2 (MyShell)

[github.com/myshell-ai/OpenVoice](https://github.com/myshell-ai/OpenVoice) — トーンと内容を分離する 2 段アーキ。内部で MeloTTS をベース音声に使う。**ライセンス MIT (v2)**。

詳細手順は [`envs/openvoice.md`](./envs/openvoice.md)。サポートは en/es/fr/zh/ja/ko、**de は MeloTTS 未対応のためスキップ**。

```bash
source envs/openvoice/bin/activate
export OPENVOICE_ROOT=$(pwd)/envs/OpenVoice
python scripts/generate_openvoice.py
```

### 4. Style-Bert-VITS2 JP-Extra

[github.com/litagin02/Style-Bert-VITS2](https://github.com/litagin02/Style-Bert-VITS2) — 日本語特化、fine-tune 前提（ゼロショット不可）。**ライセンス AGPL-3.0**。

このベンチでは「**日本語の上限を示す参考値**」として ja のみ動かす。詳細は [`envs/sbv2.md`](./envs/sbv2.md)。

```bash
source envs/sbv2/bin/activate
python scripts/generate_style_bert_vits2.py
```

### 5. ElevenLabs

[elevenlabs.io](https://elevenlabs.io) — クローズドAPI。**Instant Voice Cloning は有料プランから**。

```bash
python3.12 -m venv envs/elevenlabs
source envs/elevenlabs/bin/activate
pip install elevenlabs python-dotenv

cat > .env <<EOF
ELEVENLABS_API_KEY=sk_xxx
ELEVENLABS_VOICE_ID=your_cloned_voice_id
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
EOF

python scripts/generate_elevenlabs.py
```

`ELEVENLABS_VOICE_ID` は事前にダッシュボードで参照音声をアップロードして取得する。

## 評価

Whisper large-v3 で書き起こし → 期待テキストと比較。指標は **WER / CER + bigram Jaccard** の3つ。bigram は Whisper 側の句読点揺れに寛容な雑な参考値。WER/CER が一次指標。

```bash
pip install faster-whisper jiwer
python scripts/verify_with_whisper.py
python scripts/summarize.py
```

`results/summary.md` にマトリクス表が出る。今回の実測値:

```
| model     | ja   | en   | zh   | ko   | fr   | es   | de   |
|-----------|------|------|------|------|------|------|------|
| f5_tts    | 0.02 | 1.00 | 1.00 | 0.00 | 0.66 | 0.68 | 0.73 |
| xtts      | 0.80 | 1.00 | 1.00 | 0.63 | 1.00 | 1.00 | 1.00 |
| openvoice | 0.77 | 1.00 | 0.73 | 0.86 | 1.00 | 1.00 |  -   |
| elevenlabs| 0.93 | 1.00 | 0.70 | 0.93 | 1.00 | 1.00 | 1.00 |
```

(数値は bigram Jaccard。詳細は「実測結果」セクション)

## 結果の読み方

- `bigram_sim ≥ 0.8` または `CER < 0.2`: 実用品質。固有名詞の誤認識を除けば内容一致
- `0.4〜0.8`: 半分壊れ。一部単語が幻聴化、トーンは保たれてる場合あり
- `< 0.2`: モデルがその言語をほぼ生成できていない（音節列が無意味）

注意：

- **冒頭の挨拶句が落ちる**現象がモデル横断で観察されることがある（"Hola a todos." 等）。生成wavを必ず実聴する
- **Whisper の言語明示は必須**。自動検出だと破綻出力で誤判定 → スコア劣化が連鎖する
- **数値だけ見ない**。声質・自然さ・アクセントは別物。最終判断は耳で

## 実測結果

検証条件: macOS (Apple Silicon) / Python 3.11.8 / CPU / Whisper large-v3 (int8) / 同一参照音声 (24kHz mono 約10秒) / 同一プロンプト (`prompts.py`)。

### 総合 bigram Jaccard

| model     | ja   | en   | zh   | ko   | fr   | es   | de   |
|-----------|-----:|-----:|-----:|-----:|-----:|-----:|-----:|
| f5_tts    | 0.02 | 1.00 | 1.00 | 0.00 | 0.66 | 0.68 | 0.73 |
| xtts      | 0.80 | 1.00 | 1.00 | 0.63 | 1.00 | 1.00 | 1.00 |
| openvoice | 0.77 | 1.00 | 0.73 | 0.86 | 1.00 | 1.00 |  -   |
| elevenlabs| 0.93 | 1.00 | 0.70 | 0.93 | 1.00 | 1.00 | 1.00 |
| sbv2      | 対象外 (fine-tune 前提・GPU 必須・別ベンチ枠として見送り) |

**ざっくりの結論**:

- 内容一致の**総合ベストは ElevenLabs (eleven_multilingual_v2)**。7 言語中 5 言語で CER 0.00、ja は句読点欠落のみ (CER 0.02)、ko は今回ベスト (CER 0.02、xtts/openvoice より上)、zh だけ「一项新」→「已相信」の単語幻聴あり。クローズド API なので参考値だが、ゼロショットクローンの上限を示す数字としては明確
- OSS で多言語クローンするなら**第一候補は XTTS-v2**。7 言語すべてで実用ライン、ja は CER 0.09 で内容一致、ko だけ中盤に幻聴フレーズが入る
- **OpenVoice v2 は ko で OSS 内ベスト** (bigram 0.86)。ja/zh は単語ズレが入るが、ko 重視のユースケースなら XTTS より上。MIT ライセンスで商用利用可
- **F5-TTS は en/zh 専用**と割り切るべき。fr/es/de は意味は通るが幻聴ワード混入、ja/ko は完全破綻

各モデルの詳細表と所感は以下。

### F5-TTS_v1_Base

| lang | bigram | CER | WER | got (抜粋) | 所感 |
|---|---:|---:|---:|---|---|
| en | 1.00 | 0.00 | 0.00 | Hello everyone, today I'd like to introduce a new feature… | ほぼ完璧 |
| zh | 1.00 | 0.00 | 0.00 | 大家好,今天我将为大家介绍一项新功能,感谢您的参与 | 句読点差のみ |
| de | 0.73 | 0.30 | 0.53 | Hallo Schusterleister, ich erinnere an die neue Funktion 4. | 単語幻聴 (`Schusterleister`)、後半逸脱 |
| es | 0.68 | 0.29 | 0.56 | Hola, soy el presentador Inan Nueva Fontana. | 冒頭句崩れ、本文も逸脱 |
| fr | 0.66 | 0.24 | 0.31 | Pas de déteste, aujourd'hui, je vais vous expliquer cette… | 冒頭句崩れ (`Pas de déteste`) |
| ja | 0.02 | 0.86 | 1.00 | お待ちしております。 | 完全破綻（全く別文を10秒分発話） |
| ko | 0.00 | 0.88 | 1.00 | 띠오, 띠오키오스, 셰오아춘아에드… | 完全破綻（音節列が無意味） |

→ **F5-TTS_v1_Base は単独では多言語クローン用途に向かない**（特に ja/ko）。en/zh は学習中心言語なので強い。fr/es/de は意味は通るが幻聴ワード混入。日本語は Style-Bert-VITS2 と並走するハイブリッド構成が現実解。

生成時間は 1 サンプルあたり CPU で 70〜85 秒。検証 (Whisper) は 1 サンプル 8〜11 秒。

### XTTS-v2 (Coqui)

| lang | bigram | CER | WER | got (抜粋) | 所感 |
|---|---:|---:|---:|---|---|
| en | 1.00 | 0.00 | 0.00 | Hello everyone. Today, I'd like to introduce a new feature… | 完璧 |
| zh | 1.00 | 0.00 | 0.00 | 大家好,今天我将为大家介绍一项新功能,感谢您的参与。 | 完璧 |
| fr | 1.00 | 0.00 | 0.00 | Bonjour à tous. Aujourd'hui, je vais vous présenter… | 完璧 |
| es | 1.00 | 0.00 | 0.00 | Hola a todos. Hoy les voy a presentar una nueva función… | 完璧 |
| de | 1.00 | 0.00 | 0.00 | Hallo zusammen. Heute stelle ich Ihnen eine neue Funktion… | 完璧 |
| ja | 0.80 | 0.09 | 1.00 | みなさんこんにちは 本日は新しい機能についてご紹介しますどうぞよろしくお願いいたします | 内容一致。WER=1.00 は Whisper 側の句読点欠落でワード単位が全不一致になっているため。CER 0.09 が本質 |
| ko | 0.63 | 0.41 | 0.44 | 여러분 안녕하세요 지지연의 플레임 대통령 오늘은 새로운 체험인행을… | 中盤に幻聴フレーズ (`지지연의 플레임 대통령`) |

→ **XTTS-v2 は今回の7言語のうち 6 言語で実用品質**（ja は CER ベースで実用、ko のみ幻聴混入）。F5-TTS と異なり ja でも音節列が成立する。**多言語クローンの第一候補**。

生成は CPU で 1 サンプル 12〜33 秒（F5-TTS の約 1/5）。日本語/韓国語は文を分割するため少し長い。事前準備でハマる点が多い (`transformers<4.41` / `torch.serialization.add_safe_globals` / `torchcodec` / `cutlet` + `unidic-lite`)。詳細は `scripts/generate_xtts.py` の冒頭コメント参照。

### OpenVoice v2 (MyShell)

de は MeloTTS が未対応なのでスキップ。

| lang | bigram | CER | WER | got (抜粋) | 所感 |
|---|---:|---:|---:|---|---|
| en | 1.00 | 0.00 | 0.00 | Hello everyone, today, I'd like to introduce a new feature… | 完璧 |
| fr | 1.00 | 0.00 | 0.00 | Bonjour à tous, aujourd'hui je vais vous présenter… | 完璧 |
| es | 1.00 | 0.00 | 0.00 | Hola a todos. Hoy les voy a presentar una nueva función… | 完璧 |
| ko | 0.86 | 0.05 | 0.11 | 여러분 안녕하세요. 오늘은 새로운 디넴을 소개해 드리겠습니다… | 1 単語幻聴 (`기능을` → `디넴을`)、他は完璧。**今回最良の ko** |
| ja | 0.77 | 0.11 | 0.50 | 皆さん、今日は本日は新しい機能についてご紹介します… | 冒頭が「こんにちは」→「今日は」になり「本日は」と二重に。後半は完璧 |
| zh | 0.73 | 0.08 | 0.67 | 大家好,今天我将为大家介绍一下新功能感谢您的参与 | 「一项」→「一下」、句読点欠落。CER ベースでは内容ほぼ一致 |
| de | — | — | — | — | MeloTTS 未対応のためスキップ |

→ **OpenVoice v2 は ja/zh で軽微な単語ズレが入る**が、ko では今回ベスト。MeloTTS でベース合成 → トーン変換の 2 段構成で、声質クローンと内容生成を分離している。ライセンスが MIT で商用利用可なのも強い。

生成は CPU で 1 サンプル 5〜65 秒。**事前準備が今回一番ハマる**:
- `setup.py` の pin が古すぎて素直に入らない → `--no-deps` で本体だけ入れて依存は個別 install
- `wavmark` は別途必要
- `whisper-timestamped` の VAD が `torch.hub.load` で trust 確認を要求 → `~/.cache/torch/hub/trusted_list` に `snakers4_silero-vad` を事前登録
- `melo/text/chinese_bert.py` が `device='cpu'` を無視して MPS に切り替える → `torch.backends.mps.is_available = lambda: False`
- `converter.convert(..., message="")` が watermark で shape mismatch → 非空文字列必須
- ses checkpoint は `en` のみ `en-default.pth` 等のサブ名（`en.pth` は存在しない）
- macOS APFS の case-insensitive で `mecab-python3` (大文字 `MeCab`) と `python-mecab-ko` (小文字 `mecab`) が衝突。ko を動かすため後者だけ残し、`MeCab` をスタブ化して melo の cleaner の import を通している。**この構成では ja を再生成できない**ので ja を取り直したい時は逆に `mecab-python3` を入れ直す必要がある

詳細は `scripts/generate_openvoice.py` の冒頭コメント参照。

### Style-Bert-VITS2 JP-Extra

今回のベンチでは**対象外として見送り**。当初は「日本語の上限を示す参考値」として並べる予定だったが、実走前提を満たさないことが分かったため除外した。経緯:

- **方式が違う**: SBV2 はゼロショットではなく **fine-tune 前提**。他 4 モデルは「ref.wav 1 本を投げて即生成」だが、SBV2 は参照音声で学習を回す必要がある。同じ「同一参照音声・同一プロンプト」の枠に物理的に乗らない
- **参照音声の要件が一桁違う**: 推奨 1〜3 分。今回の `ref.wav` (10 秒) では不足。台本を書き直して録り直すことは可能だが、その瞬間に「同一参照音声で並べる」というベンチの一次目的が崩れる
- **学習環境が違う**: 100 epoch 学習は GPU 前提。macOS CPU では数時間オーダーで現実的でない。Colab T4 / 自前 GPU を用意すれば回せるが、これも他モデルと「同じ環境で叩く」原則から外れる

実装と env ドキュメントは `scripts/generate_style_bert_vits2.py` / `envs/sbv2.md` に残してあるので、上記前提を許容できる場合は SBV2 単体で「日本語 fine-tune ベースライン」として動かせる。

外部評価値が必要な場合は、第三者査読の比較論文 [arxiv:2505.17320](https://arxiv.org/abs/2505.17320) (Aoki et al. 2025, IEEE 採録) が参考になる（キャラクター演技音声 10〜15 分で fine-tune した SBV2JE が overall WER 0.04、MOS 4.37 で人間原音と統計的有意差なし）。ただし当該論文は ASR・データセット・指標いずれも本ベンチと別物のため、本ベンチの数字とは並べないこと。

### ElevenLabs (eleven_multilingual_v2)

`ref.wav` を Instant Voice Clone でアップロードして `voice_id` を取得、`eleven_multilingual_v2` で 7 言語生成。

| lang | bigram | CER | WER | got (抜粋) | 所感 |
|---|---:|---:|---:|---|---|
| en | 1.00 | 0.00 | 0.00 | Hello everyone, today I'd like to introduce a new feature… | 完璧 |
| fr | 1.00 | 0.00 | 0.00 | Bonjour à tous, aujourd'hui je vais vous présenter une nouvelle fonctionnalité… | 完璧 |
| es | 1.00 | 0.00 | 0.00 | Hola a todos, hoy les voy a presentar una nueva función… | 完璧 |
| de | 1.00 | 0.00 | 0.00 | Hallo zusammen, heute stelle ich Ihnen eine neue Funktion vor… | 完璧 |
| ja | 0.93 | 0.02 | 0.50 | 皆さんこんにちは。本日は新しい機能についてご紹介します。どうぞよろしくお願いいたします。 | 「皆さん、こんにちは」の読点欠落のみ。CER 0.02 は実質完璧 |
| ko | 0.93 | 0.02 | 0.22 | 여러분 안녕하세요. 오늘은 새로운 기능을 소개해드리겠습니다. 잘 부탁드립니다. | 「소개해 드리겠습니다」のスペース欠落のみ。**今回最良の ko** (xtts 0.63 / openvoice 0.86 と差) |
| zh | 0.70 | 0.12 | 0.33 | 大家好,今天我将为大家介绍已相信功能,感谢您的参与 | 「一项新」→「已相信」の単語幻聴。他の音節は一致 |

→ **eleven_multilingual_v2 は 7 言語中 5 言語で CER 0.00、ja/ko も実質完璧**。zh のみ単語レベルの幻聴が混入。生成は API 経由で 1 言語あたり 1〜4 秒（ja は前処理込みで少し長い）と CPU 推論勢より一桁速い。

クローズド商用 API なので OSS との並列で「上限ライン」として参照する位置付け。プラン (Starter 以上) と従量課金が必要なのでベンチを回すのは有償。

セットアップ:

```bash
python3.12 -m venv envs/elevenlabs
source envs/elevenlabs/bin/activate
pip install elevenlabs python-dotenv

# .env に ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID / ELEVENLABS_MODEL_ID を設定
# voice_id はダッシュボードの Voice Lab で ref.wav をアップロードして取得、
# または API: curl -X POST -H "xi-api-key: $KEY" -F "name=ref" -F "files=@reference/ref.wav" https://api.elevenlabs.io/v1/voices/add

python scripts/generate_elevenlabs.py
```

注意点:
- **Free プランは IVC 不可**。API でも `paid_plan_required` で蹴られる。Starter ($5/mo) 以上が必要
- IVC は 10 秒程度の参照音声 1 本で voice 化できる。アップロード即座に voice_id が発行され、追加学習なしで `text_to_speech.convert` に使える
- モデル ID は `eleven_multilingual_v2` を使用。`eleven_v3` (alpha) も同じ API 形状で呼べるがプラン制限あり

## ライセンスと公開時の注意

| モデル | ライセンス | 生成物の商用利用 |
|---|---|---|
| F5-TTS | CC-BY-NC 4.0 | **不可**（非商用のみ） |
| XTTS-v2 | Coqui Public Model License | 別途条件、要確認 |
| OpenVoice v2 | MIT | 可 |
| Style-Bert-VITS2 | AGPL-3.0 | 派生物に AGPL 要求 |
| ElevenLabs | 商用 API | プラン内で可 |

ブログにサンプル音声を埋めるだけなら fair use 側に倒せる場合が多いが、**「研究・検証目的」と明記**して商用利用と誤解されないようにする。

## 参考

- F5-TTS 論文: [arXiv:2410.06885](https://arxiv.org/abs/2410.06885)
- XTTS: [arXiv:2406.04904](https://arxiv.org/abs/2406.04904)
- OpenVoice: [arXiv:2312.01479](https://arxiv.org/abs/2312.01479)
- Style-Bert-VITS2: [GitHub](https://github.com/litagin02/Style-Bert-VITS2)
- faster-whisper: [GitHub](https://github.com/SYSTRAN/faster-whisper)
- TTS Arena (主観評価): [HF Space](https://huggingface.co/spaces/TTS-AGI/TTS-Arena)
