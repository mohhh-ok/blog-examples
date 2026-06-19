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
| sbv2      | 未計測 (fine-tune 必須・参照音声不足) |
| elevenlabs| 未計測 (API キーに IVC 権限なし) |

**ざっくりの結論**:

- 多言語ゼロショットクローンの**第一候補は XTTS-v2**。今回の 7 言語すべてで実用ライン。ja は CER 0.09 で内容一致、ko だけ中盤に幻聴フレーズが入る
- **OpenVoice v2 は ko で今回ベスト** (bigram 0.86)。ja/zh は単語ズレが入るが、ko 重視のユースケースなら XTTS より上。MIT ライセンスで商用利用可
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

今回の実走では**未計測**。理由:

- SBV2 はゼロショットクローンではなく **fine-tune 前提**で、推奨参照音声は 1〜3 分。手元の素材は 10 秒 `ref.wav` のみで学習に不足
- CPU での 100 epoch 学習は数時間オーダー。このベンチの環境 (macOS CPU) で他モデルと同じ即時計測の枠に乗らない
- ベンチの設計上、「ゼロショット同士の横比較」が一次目的なので fine-tune 必須の SBV2 は別軸の参考値として後追い

参照音声を 1 分以上揃えられたら `envs/sbv2.md` の手順で学習し、`scripts/generate_style_bert_vits2.py` を回せば日本語の「fine-tune ベースライン」を取れる。

### ElevenLabs

今回の実走では**未計測**。理由:

- 手元の API キーが `create_instant_voice_clone` 権限を持っていない（API 経由のクローン作成は 401 `missing_permissions` で拒否）
- アカウントには事前にクローン済みの voice が無く、プリセット (premade/professional) しか無い。プリセット音声で生成しても「ボイスクローンのベンチ」として他モデルと並ばない

IVC 権限付きキーが用意できるか、ダッシュボードから手動で `ref.wav` をアップロードして `voice_id` を取得できれば、`.env` に `ELEVENLABS_VOICE_ID` を追加して `scripts/generate_elevenlabs.py` を回せる。

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
