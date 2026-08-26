# Fish Audio voice clone consistency test

Fish Audio の日本語 TTS voice clone（inline zero-shot）で、同一の reference audio +
同一テキストから 5 回音声を生成し、クローン声の試行間の安定性（再現性）と
reference への近さ（忠実度）を話者 embedding の類似度で測る。

## 手法

- モデル: `s2.1-pro`（SDK の `backend` 引数 → `model` ヘッダ）
- reference: inline zero-shot clone（`references` に wav バイナリ + 書き起こしテキスト）。
  事前の voice model 登録はしない
- 生成テキスト: 日本語 3 文（固有名詞なし）を 5 回とも完全に同一で使用
- 5 回逐次実行（リクエスト間 2 秒スリープ）、出力は `format="wav"`
- 測定:
  - 話者類似度: resemblyzer `VoiceEncoder` の utterance embedding 同士のコサイン類似度
    （ref vs 各 trial の 5 個、trial 間全 10 ペア）
  - 音声尺のばらつき、librosa `pyin` による trial ごとの F0 mean / median
  - ref + trial1..5 の 6x6 類似度行列ヒートマップ（webp）

## 再現手順

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python \
  fish-audio-sdk resemblyzer librosa matplotlib pillow soundfile 'setuptools<81'
# setuptools<81 は resemblyzer が依存する webrtcvad の pkg_resources import 用

cp .env.example .env  # FISH_AUDIO_API_KEY を設定
# reference/ref.wav に自分の reference audio（〜10 秒・mono）を置き、
# scripts/generate.py の REF_TEXT をその書き起こしに合わせる

export FISH_AUDIO_API_KEY=...
.venv/bin/python scripts/generate.py   # output/trial1..5.wav + generation.json
.venv/bin/python scripts/measure.py    # output/results.json + similarity_heatmap.webp
```

## 第 2 弾: テキスト変動テスト

同一 reference で互いに異なる日本語テキスト 5 種（各 3 文・同程度の長さ・固有名詞なし）を
各 1 回生成し、「文章が変わっても声が維持されるか」を第 1 弾ベースラインと比較する。
モデル・clone 方式・実行条件は第 1 弾と同一。

- 測定: ref vs 各 text（5）、text 間全 10 ペア、クロスセット text×trial の 25 ペア、
  ref + trial1..5 + text1..5 の 11x11 類似度行列ヒートマップ（webp）、尺・F0
- 前提: 第 1 弾の `output/trial1..5.wav` と `output/results.json` が存在すること

```bash
export FISH_AUDIO_API_KEY=...
.venv/bin/python scripts/generate_varied.py   # output/varied/text1..5.wav + generation.json
.venv/bin/python scripts/measure_varied.py    # output/varied/results.json + similarity_heatmap_11x11.webp
.venv/bin/python scripts/make_report_varied.py > output/report-varied.md
```

注意: resemblyzer の utterance embedding は音素内容の影響を完全には除去できないため、
異テキスト間の類似度差には声質変化と音素内容差の両方が混ざる（report-varied.md の
「指標の限界」参照）。

## 第 3 弾: 書き起こし省略テスト

第 1 弾と完全同一条件（同一 reference + 同一テキスト 5 回）で、`ReferenceAudio` の
書き起こしテキストだけを渡さずに生成し、ref_text の有無が忠実度・再現性に効くかを
第 1 弾ベースラインと比較する。fish-audio-sdk の `ReferenceAudio.text` は必須フィールドの
ため、省略ではなく空文字列 `""` を渡す。

- 測定: ref vs 各 noref（5）、noref 間全 10 ペア、クロスセット noref×trial の 25 ペア、
  ref + trial1..5 + noref1..5 の 11x11 類似度行列ヒートマップ（webp）、尺・F0・RMS
- 前提: 第 1 弾の `output/trial1..5.wav` と `output/results.json` が存在すること

```bash
export FISH_AUDIO_API_KEY=...
.venv/bin/python scripts/generate_noreftext.py   # output/noreftext/trial1..5.wav + generation.json
.venv/bin/python scripts/measure_noreftext.py    # output/noreftext/results.json + similarity_heatmap_noreftext.webp
.venv/bin/python scripts/make_report_noreftext.py > output/report-noreftext.md
```

## 第 4 弾: 書き起こし省略 × テキスト変動テスト

第 2 弾と完全同一の異テキスト 5 種を、第 3 弾と同じく書き起こしなし（空文字列 `""`）で
各 1 回生成し、ref_text 有無 × 同一文/異文の 2×2 実験マトリクスを完成させる。
モデル・clone 方式・実行条件は第 2・3 弾と同一。

- 測定: ref vs 各 nv（5）、nv 間全 10 ペア、クロス A: nv×第 2 弾 text の 25 ペア
  （同一文章同士の 5 ペアも個別記録）、クロス B: nv×第 3 弾 noref の 25 ペア、
  ref + 第 2 弾 text1..5 + nv1..5 の 11x11 類似度行列ヒートマップ（webp）、尺・F0・RMS
- 前提: 第 1〜3 弾の出力（`output/results.json`・`output/varied/`・`output/noreftext/`）が存在すること

```bash
export FISH_AUDIO_API_KEY=...
.venv/bin/python scripts/generate_noreftext_varied.py   # output/noreftext_varied/text1..5.wav + generation.json
.venv/bin/python scripts/measure_noreftext_varied.py    # output/noreftext_varied/results.json + similarity_heatmap_noreftext_varied.webp
.venv/bin/python scripts/make_report_noreftext_varied.py > output/report-noreftext-varied.md
```

## 第 5 弾: 多言語テスト

日本語話者の同一 reference から 7 言語 (ja / en / zh / ko / fr / es / de) のテキストを
各 1 回生成し、「言語をまたいでも同じクローン声が出るか」を第 2 弾 (日本語異文 5 本)
ベースラインと比較する。条件は第 1・2 弾と同じ標準形 (ref_text あり)。生成テキストは
`2026/06-19-multilingual-voice-cloning-benchmark/prompts.py` と同一。

- 測定: ref vs 各言語（7）、言語間全 21 ペア (ja–他言語 6 ペアは個別記録)、
  クロスセット 言語×第 2 弾 text の 35 ペア、ref + 7 言語の 8x8 類似度行列
  ヒートマップ（webp）、尺・F0・RMS
- 言語検証: faster-whisper (small・CPU) で各 wav の言語判定 + 書き起こし
- 前提: 第 2 弾の `output/varied/` が存在すること

```bash
uv pip install --python .venv/bin/python faster-whisper  # 言語検証用に追加

export FISH_AUDIO_API_KEY=...
.venv/bin/python scripts/generate_multilingual.py   # output/multilingual/<lang>.wav + generation.json
.venv/bin/python scripts/measure_multilingual.py    # output/multilingual/results.json + similarity_heatmap_multilingual.webp
.venv/bin/python scripts/make_report_multilingual.py > output/report-multilingual.md
```

注意: resemblyzer の VoiceEncoder は英語中心のデータセットで学習されており、言語を
またいだ類似度には声質変化・音素体系差・encoder の言語バイアスが混ざる
(report-multilingual.md の「指標の限界」参照)。

## 第 6 弾: voice model 登録 (reference_id) A/B テスト

inline zero-shot（`references`）と、事前に voice model を登録して `reference_id` で
指定する方式の A/B。「登録すれば声が一貫するのか」を発話間ペア類似度で比較する。
voice model は `train_mode="fast"`・`visibility="private"` で作成し、実験後に削除する。

- 生成: 同一文 × 5 回（第 1 弾と同一文）+ 異文 × 10 本（第 2 弾の text1..5 +
  セリフ行を模した短文 5 本）を、テキストごとに A (inline) → B (reference_id) の対で生成
  （時間帯ドリフトを条件間で均す）。temperature/top_p は SDK 既定値 0.7/0.7 で両条件共通
- 測定: 各条件の群内発話間ペア類似度（same 10 / varied 45 / all15 105 ペア）、
  各発話 vs ref（忠実度）、尺 std、同一テキスト対の A vs B（15 対）、
  permutation test（mean 差 B−A、参考値）
- 前提: 第 1 弾の `output/results.json` が存在すること

```bash
export FISH_AUDIO_API_KEY=...
.venv/bin/python scripts/create_model.py                    # output/voiceid_ab/model.json (id を控える)
.venv/bin/python scripts/generate_voiceid_ab.py <model_id>  # output/voiceid_ab/{a,b}_*.wav + generation.json
.venv/bin/python scripts/measure_voiceid_ab.py              # output/voiceid_ab/results.json
.venv/bin/python scripts/delete_model.py <model_id>         # 後片付け (404 確認まで)
```

注意: SDK `create_model` の `enhance_audio_quality` は default True のまま使用している
（登録経路の素の挙動を測るため）。reference_id 側の ref 忠実度低下の一因候補。

## 構成

- `scripts/generate.py` — Fish API で 5 trial 生成（レイテンシ・尺を記録）
- `scripts/measure.py` — embedding 類似度・F0・ヒートマップ
- `scripts/generate_varied.py` — 第 2 弾: 異テキスト 5 種を各 1 回生成
- `scripts/measure_varied.py` — 第 2 弾: 4 群の類似度・11x11 ヒートマップ・F0
- `scripts/make_report_varied.py` — 第 2 弾: report-varied.md の組み立て
- `scripts/generate_noreftext.py` — 第 3 弾: 書き起こしなしで 5 trial 生成
- `scripts/measure_noreftext.py` — 第 3 弾: 4 群の類似度・11x11 ヒートマップ・F0・RMS
- `scripts/make_report_noreftext.py` — 第 3 弾: report-noreftext.md の組み立て
- `scripts/generate_noreftext_varied.py` — 第 4 弾: 書き起こしなしで異テキスト 5 種を各 1 回生成
- `scripts/measure_noreftext_varied.py` — 第 4 弾: 類似度 4 群・11x11 ヒートマップ・F0・RMS
- `scripts/make_report_noreftext_varied.py` — 第 4 弾: report-noreftext-varied.md の組み立て
- `scripts/generate_multilingual.py` — 第 5 弾: 7 言語を各 1 回生成
- `scripts/measure_multilingual.py` — 第 5 弾: 類似度群・8x8 ヒートマップ・F0・RMS・言語検証 (faster-whisper)
- `scripts/make_report_multilingual.py` — 第 5 弾: report-multilingual.md の組み立て
- `scripts/common_voiceid_ab.py` — 第 6 弾: 共通定義（ref・テキスト・パラメータ）
- `scripts/create_model.py` — 第 6 弾: voice model 作成（fast / private）
- `scripts/generate_voiceid_ab.py` — 第 6 弾: A/B 30 発話を対で生成
- `scripts/measure_voiceid_ab.py` — 第 6 弾: 群内ペア類似度・忠実度・permutation test
- `scripts/delete_model.py` — 第 6 弾: voice model 削除 + 404 確認
- `reference/` — reference audio（git 管理外）
- `output/` — 生成音声と測定結果（第 2 弾は `output/varied/`、第 3 弾は `output/noreftext/`、第 4 弾は `output/noreftext_varied/`、第 5 弾は `output/multilingual/`、第 6 弾は `output/voiceid_ab/`。ライセンスは `output/LICENSE.md`）
