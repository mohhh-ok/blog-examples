# Irodori-TTS v4.1-Small: 1 行ずつ合成したときの行間の声の一貫性

台本を 1 行ずつ別々に合成したとき、行の境目で声が別人に入れ替わるかを、11 声 × 参照の品質 3 条件 × 合成方式 3 通りで測った。結論・条件・全条件の表は `result.md`。前提の計測 (読みの精度、同じ文を seed を変えて合成したときの似方) は `../10-07-irodori-tts-japanese/`。

| ファイル | 役割 | 実行場所 |
|---|---|---|
| `texts.py` | 台本 10 行、run の分け方、方式、参照品質の設定 | 共通 |
| `make_refs.py` | JVS から話者 10 人を選び、参照 3 条件 (clean / quiet / noisy) を作る | ローカル |
| `gen_lines.py` | preflight (10 行を 1 回にしたときの予測尺) と 726 本の生成 | RunPod RTX 4090 |
| `measure.py` | 行単位の話者類似度 (resemblyzer) と F0 (parselmouth) | RunPod (CPU で動く) |
| `measure_windows.py` | 3 方式を同じ 2.5 秒窓で測り直す | ローカル |
| `make_report.py` | `results/summary.json` と `result.md` の表、聴き比べ用の連結音声 | ローカル |
| `make_figure.py` | 記事の図 (声ごと・方式ごとの ref 比の平均) | ローカル |

生成の設定は前編 (`../10-07-irodori-tts-japanese/eval_irodori.py`) と同じ。Irodori-TTS commit 89f9d8f、fp32、ステップ数と CFG はチェックポイント既定、参照音声だけを渡し書き起こしは渡さない。

## 方式

| 方式 | 中身 |
|---|---|
| per-line-random | 1 行ずつ合成、seed はランダム |
| per-line-fixed | 1 行ずつ合成、全行 seed=42 |
| run | 1〜5 行目と 6〜10 行目をそれぞれ 1 回で合成 (10 行を 1 回にすると出力上限の 30 秒を超えるため 2 回に分けた) |

## 参照の品質

| 品質 | 中身 |
|---|---|
| clean | JVS の parallel100 を番号順に連結し、15 秒を超えた発話で止めたもの (無加工)。mo は R10 そのまま |
| quiet | clean を -25 dB 下げたもの |
| noisy | clean に白色ノイズを足し、最も静かな 0.2 秒の RMS を -45 dB にしたもの |

## results/

- `summary.json`: 条件ごとの集計、品質 × 方式の集計、seed 固定とランダムの対比較、preflight、生成時間
- `windows.json`: 3 方式を同じ 2.5 秒窓で測った集計と、窓ごとの ref 比
- `measure.json`: 行・窓ごとの生の値 (`measure.py` の出力)
- `gen.jsonl`: 生成ごとの文・seed・秒数・Irodori のメッセージ
- `refs.json`: 選んだ話者と参照音声の測定値

## output/

記事に載せた mo の clean 3 方式の音声。per-line は 10 行を、run は 2 回分を、間に 0.4 秒の無音を挟んでつないだもの。扱いは `output/LICENSE.md`。

## JVS コーパスについて

話者 10 人は [JVS コーパス](https://sites.google.com/site/shinnosuketakamichi/research-topics/jvs_corpus) (Takamichi et al.) から選んだ。規約 (コーパス同梱の README.txt) は "Personal use, including blog posts." を認め、再配布は認めていない ("Re-distribution is not permited, but you can upload a part of this corpus (e.g., ~10 audio files) in your webpage or blog.")。JVS の声で合成した音声の公開については記述が無いため、JVS の元音声も、JVS の声を参照にした生成音声もこのリポジトリには置いていない。`make_refs.py` に手元の jvs_ver1 を渡すと同じ参照が作れる。
