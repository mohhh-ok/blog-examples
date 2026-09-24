# Gemini 3.8 Flash TTS と Fish Audio の voice clone 比較

Flash-Lite TTS は voice replication 非対応 (voice 作成時に model を指定すると 400) のため対象外。

記事: https://mohhh-ok.github.io/blog/posts/2026/09-24-aigemini-38-flash-ttsの声クローンをfish-audioと聴き比べた/

同じ参照音声 (筆者本人の録音 25.7 秒) と同じ読み上げ文 2 本で、次の 3 条件を生成して比べる。

- `fish-text`: Fish Audio `s2.1-pro`、参照音声の書き起こしを送る
- `fish-notext`: Fish Audio `s2.1-pro`、書き起こしを空文字で送る
- `gemini-flash`: `gemini-3.8-flash-tts`、voice replication

## 使い方

1. 同じディレクトリに `ref-source.wav` (10〜30 秒の話し声) と `ref-consent.wav` (Google 指定の同意文を同じ人が読んだもの) を置く。どちらも 24kHz mono 16bit WAV
2. `FISH_API_KEY=... GEMINI_API_KEY=... uv run generate.py`
3. 出力は `~/Downloads/gemini-tts-eval/`。`RUNS` で本数、`CONDITIONS` で条件を絞れる

## audio

`ref-source.mp3` が参照音声 (筆者の声)。ほかは各条件 × 読み上げ文 (s1 / s2) の生成結果 (`generate.py` が出す `*-r1.wav` を 128kbps の mp3 に変換したもの)。同意文の録音は同梱していない。

## results

- `katakana.tsv`: 生成音声を 16kHz mono mp3 にして `gpt-4o-transcribe` にカタカナ音写させた結果 (ファイル名・尺・音写)
