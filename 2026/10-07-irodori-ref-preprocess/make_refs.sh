#!/bin/sh
# 参照 R26 (24kHz mono) から条件 B〜F の参照を作る。
# usage: sh make_refs.sh <r26.wav> <出力ディレクトリ>
set -eu
src=$1
mkdir -p "$2"
out=$(cd "$2" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

FILTER='silenceremove=start_periods=1:start_silence=0.2:start_threshold=-40dB:detection=peak:stop_periods=-1:stop_silence=0.3:stop_threshold=-40dB,loudnorm=I=-18:TP=-1.5:LRA=11'

# 下処理: 先頭 X 秒に切る → 無音を詰めて音量をそろえる → 末尾に 0.5 秒の無音
# -ar を付けないので、loudnorm の出力は 192kHz になる
preprocess() {
  ffmpeg -v error -y -i "$src" -af "atrim=end=$1" -c:a pcm_s16le "$tmp/trim.wav"
  ffmpeg -v error -y -f wav -i "$tmp/trim.wav" -af "$FILTER" -c:a pcm_s16le "$tmp/dense.wav"
  ffmpeg -v error -y -f wav -i "$tmp/dense.wav" -af "apad=pad_dur=0.500" -c:a pcm_s16le "$2"
}

# B: 先頭 15 秒に切っただけ
ffmpeg -v error -y -i "$src" -af "atrim=end=15.000" -c:a pcm_s16le "$out/r26t15.wav"
# C: 先頭 15 秒に下処理
preprocess 15.000 "$out/r26pipe.wav"
# D: C を 2 回つないだだけ
printf "file '%s'\nfile '%s'\n" "$out/r26pipe.wav" "$out/r26pipe.wav" > "$tmp/concat.txt"
ffmpeg -v error -y -f concat -safe 0 -i "$tmp/concat.txt" -c copy "$out/r26pipe2x.wav"
# E: 先頭 12.87 秒 (C と同じ長さ) に切っただけ
ffmpeg -v error -y -i "$src" -af "atrim=end=12.870" -c:a pcm_s16le "$out/r26t1287.wav"
# F: 先頭 18 秒に下処理 (下処理後に 15 秒以上残る最小の長さ)
preprocess 18.000 "$out/r26long-pipe.wav"
