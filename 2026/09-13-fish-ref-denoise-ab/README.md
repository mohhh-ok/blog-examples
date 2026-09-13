# Fish Audio TTS reference audio denoise A/B

Fish Audio S2 系 (`s2.1-pro`) の zero-shot voice clone で、参照音声 (reference audio) に
DeepFilterNet 3 の denoise をかけると、生成音声の完走度 (台本を最後まで読み切るか) が
良くなるのか・悪くなるのか・変わらないのかを A/B テストで測る。

## 背景

「ノイズの乗った参照音声には denoise をかけたほうが良い」という直感はよくあるが、
zero-shot voice clone 系の TTS では、denoise によって参照音声のプロソディ (息継ぎ・
子音の立ち上がり等) が変質し、かえってクローン結果が不安定になることがある
(他の TTS エンジン向けに実施した denoise 評価では、ノイズが強い素材に限って有効という
結果だった)。この実験は Fish Audio S2 系についてその効果を単独で切り分ける。

## 手法

- 変数は「参照音声への denoise の有無」だけ。truncate 区間 (先頭 15 秒)・無音圧縮
  (densify)・末尾の無音 pad・モデル・temperature・台本・参照音声側の書き起こし
  (reference text) は全条件で同一にする。
- 条件は 3 つ。
  - `N` (no denoise): truncate → densify → pad
  - `D` (denoise): truncate → DeepFilterNet 3 (fal.ai 経由) → 16kHz mono 化 → densify → pad
  - `R` (resample only): truncate → 16kHz mono 化 → densify → pad
  - `D` は「denoise」と「16kHz mono 化」の 2 つの変更を同時に含む。`R` を対照として
    入れることで、差が出た場合にそれが DeepFilterNet 3 由来か、単なるサンプルレート
    変換由来かを切り分けられる。
- 参照音声は話者ごとに 4 変種を用意する (音量 × ノイズの 2x2)。
  - `loud_clean`: 原本を `loudnorm` (ヘッドルーム 4dB) で正規化しただけ
  - `quiet_clean`: `loud_clean` をさらに -10dB 減衰
  - `loud_noise`: `loud_clean` に pink noise を SNR 20dB 目安で加算
  - `quiet_noise`: `quiet_clean` に同じ pink noise を加算 (SNR 20dB・音量小、ノイズが
    最も denoise を誘発しやすいプロファイル)
  - noise 加算後のピークが 0dBFS 付近まで来ると clipping で歪みが混入し denoise 以外の
    変数になるため、加算直後に max_volume を測って閾値超過なら生成を止める (fail-loud)
  - denoise を実際に発動させるかどうかの本番相当ゲート (`SNR < 30dB` かつ
    `maxVolume >= -15dB`) がどの変種で成立するかは `refs/manifest.json` に記録するが、
    このハーネス自体は 3 条件を強制的に全 ref に適用する (ゲート判定はログ用途のみ)。
- 台本は短文 (2 行) と長文 (22 行) の 2 種類。
- 各セル (ref 8 種 × 台本 2 種 × 条件 3 種) を n=20 で回す。
- 生成音声は本番相当の無音圧縮 (1 秒以上の無音のみ検出して 0.4 秒に切り詰め) を通した
  あと、`whisper-1` で書き起こし、台本との LCS (最長共通部分列) 比率で完走度を測る。
  比率が閾値未満なら NG、0.5 未満なら「崩壊」、実測尺が保守話速から見積もった上限を
  超えたら「overflow」として記録する。
- 主判定は pooled (全 ref × 台本) の NG 率を `N` vs `D` で Fisher の正確検定 (両側)
  にかける。副次的に ref 変種別・台本別の pooled 比較も行う。

## 結果 (話者 2 名、n=20/セル)

話者 2 名 (収録音声、感情ラベル「悲しみ」の発話を素材に使用)、台本 2 種、条件 3 種
(N/D/R) を n=20 で回した (セル数 8 ref × 2 台本 × 3 条件、生成 960 件、エラー 0 件)。
pooled (全 ref × 台本、条件ごと n=320) の NG 件数と Fisher の正確検定 (両側):

| 条件 | NG 件数 |
|---|---|
| N (denoise なし) | 3 / 320 |
| R (16kHz mono 化のみ) | 4 / 320 |
| D (denoise) | 21 / 320 |

- N vs D: p = 0.000215
- N vs R: p = 1.000000
- R vs D: p = 0.000726

D は N・R のどちらと比べても NG 率が有意に高く、N と R の間には差がない。この 2 つを
合わせると、NG 率の増加は 16kHz mono 化ではなく DeepFilterNet 3 の denoise 処理自体に
起因すると読める。台本別・ref 変種別の内訳、失敗した生成の書き起こし例は
`output-summary/summary.md` と `output-summary/results.jsonl` を参照。

## 前提・環境変数

- ランタイムは [bun](https://bun.sh/)。
- 話者の参照音声 wav (2 名以上、各 15 秒程度以上) を自分で用意する。ライセンス上
  再配布・商用利用に問題のない音声を使うこと。
- 台本ファイル (短文・長文、それぞれ 1 行 1 発話、`\n` 区切りでそのまま TTS に渡る)
  を自分で用意する。
- 以下の API キーが必要 (`.env.example` を `.env` にコピーして設定し、シェルに
  読み込んでから使う):
  - `FISH_API_KEY`: Fish Audio の API キー
  - `OPENAI_API_KEY`: OpenAI の API キー (`whisper-1` 書き起こし用)
  - `FAL_KEY`: fal.ai の API キー (DeepFilterNet 3 denoise 用)

## 再現手順

```bash
bun install

# .env.example を元に .env を作り、3 つのキーを設定してから読み込む
set -a; source .env; set +a
```

### 1. 参照音声の変種を作る (`prepare-refs.ts`)

話者ラベルと wav パスを `label=path` 形式でカンマ区切りにして渡す。

```bash
REF_SPEAKERS="speaker1=/path/to/speaker1.wav,speaker2=/path/to/speaker2.wav" \
OUT_DIR=./output \
bun run prepare-refs
```

`OUT_DIR/refs/<speaker>_<variant>/` 配下に `variant.wav` (変種そのもの) /
`truncated.wav` (15 秒切り出し) / `N.wav` / `D.wav` / `R.wav` (各条件の prepared
wav) ができる。`OUT_DIR/refs/manifest.json` に各 ref の音量・LUFS・推定 SNR・
denoise ゲート判定を記録する。wav はサイズが大きいためリポジトリにはコミットしない
(`.gitignore` 参照)。

### 2. 生成 → 書き起こし → 指標計算 (`run.ts`)

```bash
REPS=20 \
OUT_DIR=./output \
SCRIPT_SHORT_PATH=/path/to/script-short.txt \
SCRIPT_LONG_PATH=/path/to/script-long.txt \
bun run run
```

`rep × ref × 台本 × 条件` の全組み合わせについて Fish Audio を呼び、生成音声を
`OUT_DIR/runs/<ref>/<script>/<cond>/<rep>.raw.wav` に保存する。無音圧縮した
`<rep>.trim.wav` を作ってから `whisper-1` で書き起こし、1 行 1 レコードで
`OUT_DIR/results.jsonl` に追記する。既に記録済みの `(ref, script, cond, rep)` は
スキップするため、失敗時や途中終了後に同じコマンドで再実行すれば続きから再開する。

Fish Audio 呼び出しは同時 2 件まで、後段の無音圧縮・書き起こし・指標計算は同時 4 件
まで並列に走る。

`REFS_FILTER` (カンマ区切りの ref key) で対象を絞り込める。動作確認用の少数実行に
使う。

### 3. 集計 (`analyze.ts`)

```bash
OUT_DIR=./output bun run analyze
```

`results.jsonl` を読み、セル別 (ref × 台本 × 条件) の n・NG 数・崩壊数・overflow 数・
尺の中央値/最大値と、pooled および ref 変種別・台本別の `N` vs `D` / `N` vs `R` /
`R` vs `D` の Fisher 正確検定 (両側) を計算して `OUT_DIR/summary.md` /
`OUT_DIR/summary.json` に書く。

## 動作確認 (smoke test)

実際の話者音声を用意する前に、パイプライン全体が動くかどうかを macOS の `say`
コマンドで確認できる。

```bash
say -v Kyoko -o /tmp/smoke_say.aiff "（20 秒程度の日本語テキスト）"
ffmpeg -i /tmp/smoke_say.aiff -c:a pcm_s16le /tmp/smoke_say.wav

REF_SPEAKERS="smoke=/tmp/smoke_say.wav" OUT_DIR=./smoke bun run prepare-refs
REPS=1 REFS_FILTER=smoke_quiet_noise OUT_DIR=./smoke \
  SCRIPT_SHORT_PATH=./script-short.txt SCRIPT_LONG_PATH=./script-long.txt \
  bun run run
OUT_DIR=./smoke bun run analyze
```

## 実装の再利用元について

このハーネスの指標計算 (LCS 比率・完走判定の閾値・出力尺の上限推定・無音圧縮の
アルゴリズム) は、筆者が別プロジェクトで運用している本番の TTS 完走チェック・無音
圧縮ロジックと数値が一致するよう、同じ定数・同じ前処理で独立に再実装したもの。
再利用ではなく、本番コードとは別リポジトリの自己完結したコードとして書いている。

## ディレクトリ構成

```
src/
  lib/
    ffmpeg.ts    ffmpeg/ffprobe ラッパーと音量・ノイズフロア・LUFS 計測
    trim.ts      無音圧縮 (1 秒以上の無音のみ検出して 0.4 秒に切り詰め)
    metrics.ts   LCS 比率による完走チェック
    estimate.ts  文字種から TTS 出力尺を見積もり、上限秒数ゲートを計算
    fish.ts      Fish Audio /v1/tts 呼び出し (msgpack, リトライ)
    whisper.ts   whisper-1 書き起こし (prompt 前処理込み)
    denoise.ts   fal.ai DeepFilterNet 3 呼び出し
    fisher.ts    Fisher の正確検定 (両側、超幾何分布)
  prepare-refs.ts  話者 wav → 4 変種 → 3 条件の prepared wav
  run.ts           生成 → trim → 書き起こし → 指標計算のメインループ
  analyze.ts       集計・検定・summary 出力
```
