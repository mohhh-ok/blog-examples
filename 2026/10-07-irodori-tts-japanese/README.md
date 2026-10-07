# Irodori-TTS v4.1-Small の日本語読みと声クローン (Fish Audio s2.1-pro との比較)

結果と手法は `report.md`、数値の表は `report-numbers.md`。

| ファイル | 役割 | 実行場所 |
|---|---|---|
| `select_rows.py` | JKYB-Parakeet から 100 行を固定 seed で選び `data/r100.jsonl` に書く | ローカル |
| `data/n10.jsonl` | 数字・英字の自作 10 文 (JKYB と同じ形式) | — |
| `texts.py` | 全実験の文・参照音声の書き起こし・生成の一覧 | 共通 |
| `gen_fish.py` | Fish Audio s2.1-pro で 125 本生成 | ローカル (API) |
| `eval_irodori.py` | Irodori で 129 本生成し、両モデルの resemblyzer 類似度を出す | RunPod RTX 4090 |
| `transcribe.py` | gpt-4o-transcribe でカタカナ書き起こし | ローカル (API) |
| `score.py` | JKYB-Parakeet 公式ツールキットの `score_row` で採点 | ローカル |
| `make_report.py` | `results/` にまとめ、`report-numbers.md` を書く | ローカル |

`results/` の中身:

- `gen_irodori.json` / `gen_fish.json`: 生成ごとの文・参照・seed・秒数・RTF
- `similarity.json`: 参照音声との類似度 (`ref_vs`)、B の試行間類似度 (`b_pairwise`)
- `seed_md5.json`: seed=42 の 2 回生成の MD5
- `transcripts.jsonl` / `transcripts-pass2.jsonl`: カタカナ書き起こし (2 回目は不正解・疑いの行だけ)
- `scores.json`: 行ごとの判定 (`rows`) と集計 (`summary`)

`output/` は記事に載せた 5 文の Irodori / Fish のペア (B の run1、c1、r014、n01、n04)。扱いは `output/LICENSE.md`。

`data/r100.jsonl` は [JKYB-Parakeet](https://huggingface.co/datasets/Parakeet-Inc/joyo-kanji-yomi-benchmark-parakeet) (MIT, Parakeet Inc.) から選んだ行をそのまま含む。
