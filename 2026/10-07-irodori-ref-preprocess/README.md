# Irodori-TTS v4.1-Small: 参照音声の下処理と、短い入力の前後に出る音

参照音声に無音詰め・音量そろえの下処理をかけると、短い入力の声の前後に音が出るかを、参照の条件を変えて測った。

| ファイル | 役割 | 実行場所 |
|---|---|---|
| `gen_words.py` | 第1弾: 清水寺・鹿苑寺を単語と文で 18 本生成 (参照 R10) | RunPod RTX 4090 |
| `transcribe_words.py` | 第1弾: gpt-4o-transcribe でカタカナ書き起こし | ローカル (API) |
| `make_refs.sh` | R26 から条件 B〜F の参照を ffmpeg で作る | ローカル |
| `gen.py` | 第2〜5弾: 短い入力 8 文 × 参照 × seed 2 を生成 (`short` / `ref` / `2x` / `len`) | RunPod RTX 4090 |
| `measure.py` | 長さ・先頭 0.2 秒 / 末尾 0.4 秒の RMS を測り、`results/measurements.json` と `results/report.md` を書く | ローカル |
| `make_figure.py` | 「金閣寺」seed 2 の A/B/E/C/F のスペクトログラム (0〜2kHz) を並べた図 | ローカル |

生成の設定は前編 (`../10-07-irodori-tts-japanese/eval_irodori.py`) と同じ。Irodori-TTS commit 89f9d8f、fp32、ステップ数と CFG はチェックポイント既定、参照音声だけを渡し書き起こしは渡さない。

## 参照の条件

| 条件 | 中身 |
|---|---|
| R10 | 前編の 10 秒の参照 (08-26 の記事の録音、下処理なし) |
| A | R26 そのまま (25.69 秒、24kHz) |
| B | R26 を先頭 15 秒で切っただけ |
| C | R26 を先頭 15 秒で切り、下処理をかけたもの (12.87 秒、192kHz) |
| D | C を 2 回つないだだけ (25.74 秒) |
| E | R26 を先頭 12.87 秒 (C と同じ長さ) で切っただけ |
| F | R26 を先頭 18 秒で切り、下処理をかけたもの (15.54 秒。下処理後に 15 秒以上残る最小の長さ) |

R26 は 09-24 の記事の `../09-24-gemini-tts-vs-fish-clone/audio/ref-source.mp3` を 24kHz mono 16bit に戻したもの (`ffmpeg -i ref-source.mp3 -ac 1 -ar 24000 -c:a pcm_s16le r26.wav`)。これを `make_refs.sh` に渡すと、実験で使った B〜F とサンプル単位で同じ wav が出る (ffmpeg 9.0.2 で確認)。

下処理は `make_refs.sh` の `preprocess`。先頭 X 秒に切る → `silenceremove` で無音を詰め `loudnorm` で音量をそろえる → 末尾に 0.5 秒の無音を足す。`-ar` を付けていないので、`loudnorm` の出力は 192kHz になる。

## results/

- `gen-words.json` / `transcripts-words.jsonl`: 第1弾の生成記録と書き起こし
- `gen.json`: 第2〜5弾の生成記録 112 本。`messages` に Irodori が出した予測長 (`predicted duration`) が入っている
- `measurements.json`: 全 130 本の長さ・予測長・RMS と、参照 7 本の長さ・サンプルレート・最も静かな 0.2 秒の RMS
- `report.md`: `measurements.json` の表

RMS は dBFS。先頭 0.2 秒が -60 dB より大きい本数を、声の前に何か鳴っているかの目安にした (A・B は全部 -78 dB 台以下)。

## output/

記事に載せた「金閣寺」seed 2 の 5 本 (A `k3-r26-s2`、B `k3-r26t15-s2`、E `k3-r26t1287-s2`、C `k3-r26pipe-s2`、F `k3-r26long-pipe-s2`)。扱いは `output/LICENSE.md`。
