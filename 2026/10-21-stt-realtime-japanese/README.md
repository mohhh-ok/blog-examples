# 日本語のリアルタイム文字起こしで ElevenLabs と Soniox を比べる

FLEURS（google/fleurs、CC BY 4.0）の日本語の読み上げ音声 40 本を、ElevenLabs Scribe v2 Realtime（`scribe_v2_realtime`）と Soniox（`stt-rt-v5`）に実時間の速さで流し、文字誤り率・文の区切り方・話し終わりから確定までの時間を比べた。

記事: [日本語のリアルタイム文字起こしでElevenLabs Scribe v2 RealtimeとSonioxを比べた](https://mohhh-ok.github.io/blog/posts/2026/10-21-ai日本語のリアルタイム文字起こしでelevenlabs-scribe-v2-realtimeとsonioxを比べた/)

## 中身

- `src/prepare-fleurs.ts`: FLEURS の 1 言語から N 本を固定の seed で選んで一覧（tsv）を書く
- `src/run.ts`: 一覧の音声を 1 本ずつ、1 つのプロバイダに流して結果を jsonl に書く
- `src/score.ts`: jsonl を採点し、1 本ごとの表 `items.tsv` と集計 `summary.md` を書く
- `src/rescore-kanji-numerals.ts`: 漢数字を算用数字に直した参考値の文字誤り率を出す
- `results/`: 2026-10-20 に流した生の結果（jsonl）と採点の出力。正解の文は FLEURS のもの

一覧の tsv の列は `id`・`text`（正解の文）・`terms`（固有名詞。`;` 区切り。無ければ空）・`audio`（任意。無ければ `--audio-dir` の `<id>.wav`）。

## 必要なもの

- Node.js 24 以上（型注釈付きの `.ts` をそのまま動かす。依存パッケージは無い）
- ffmpeg
- `ELEVENLABS_API_KEY`・`SONIOX_API_KEY`

## 使い方

```sh
# 1. Hugging Face の google/fleurs から data/ja_jp/dev.tsv と data/ja_jp/audio/dev.tar.gz を取り、展開する
# 2. 40 本選ぶ
node src/prepare-fleurs.ts --tsv <dir>/dev.tsv --audio-dir <dir>/dev --count 40 --seed 1 --out /tmp/stt-bench/fleurs-ja.tsv

# 3. 流す（1 条件で約 13 分）
node src/run.ts --manifest /tmp/stt-bench/fleurs-ja.tsv --language ja --provider elevenlabs --out-dir /tmp/stt-bench/results
node src/run.ts --manifest /tmp/stt-bench/fleurs-ja.tsv --language ja --provider soniox --out-dir /tmp/stt-bench/results
node src/run.ts --manifest /tmp/stt-bench/fleurs-ja.tsv --language ja --provider soniox --soniox-max-endpoint-delay-ms 2000 --out-dir /tmp/stt-bench/results

# 4. 採点
node src/score.ts --manifest /tmp/stt-bench/fleurs-ja.tsv --out-dir /tmp/stt-bench/results /tmp/stt-bench/results/*.jsonl
node src/rescore-kanji-numerals.ts /tmp/stt-bench/fleurs-ja.tsv /tmp/stt-bench/results/*.jsonl
```

- `--provider`: `elevenlabs` か `soniox`
- `--soniox-max-endpoint-delay-ms`: Soniox の `max_endpoint_delay_ms`（500〜3000）。既定は LiveKit のプラグインの既定の 500。500 以外にすると結果のファイル名が `soniox-d<値>` になる
- `--hints`: `none`（既定）か `terms`（一覧の `terms` を ElevenLabs には `keyterms`、Soniox には `context.terms` で渡す）。記事では使っていない
- `--limit`: 先頭の N 本だけ流す（動作確認用）
- 結果は `<out-dir>/<provider>-<hints>.jsonl` に追記する。止めて流し直すと、書き終えた id は飛ばす
- 1 本ずつ順に流す。同時に流さない

## 測り方

- 16kHz・モノラル・16bit に変換し、50ms の塊を、その塊が録り終わる時刻に送る（マイクから届くのと同じ速さ）。音声の後に 3 秒の無音を足して送り、最後に終わりを明示する（ElevenLabs は `commit: true`、Soniox は空のフレーム）
- ElevenLabs は LiveKit のプラグインと同じく、無音 0.5 秒で確定する（`commit_strategy` vad）。Soniox も LiveKit のプラグインの既定の設定に、model `stt-rt-v5` を明示した
- 話し終わりの時刻は、10ms の窓の RMS がその音声の最大値の 10% 以上になる最後の窓の終わり
- 話し終わりから確定までの時間は、最後の確定が届いた時刻 − 話し終わりの時刻。最後の確定が終わりの明示の後に届いたもの（プロバイダが自分で区切らなかった）は数えず、本数だけ出す
- 文字誤り率は、正解と結果を同じ規則で正規化（NFKC・小文字・句読点と記号と空白を消す、`src/normalize.ts`）し、書記素の編集距離 ÷ 正解の書記素数。数字の書き方の違い（三十 と 30）も誤りとして数える
