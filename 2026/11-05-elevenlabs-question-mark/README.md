# ElevenLabs の日本語 TTS で、全角「？」と半角「?」の文末の上がりを比べる

ElevenLabs の `eleven_v4_turbo`（language_code `ja`・Instant Voice Clone の日本語の声）で、
言い切りの形の問い（「あした ひま？」）の文末が全角「？」では上がらず、半角「?」では上がった件の、置き換えの関数と F0 の測り方。

- `src/questionMark.ts` — 送る直前に全角「？」を半角「?」にする関数。続く「？？」は 1 つにし、後ろに文が続くときは空白を挟む。画面に出す文には使わない
- `src/questionMark.test.ts` — `bun test src`
- `scripts/f0_rise.py` — wav の最後の有声区間で、いちばん低い所から終わり（最後の 30ms の中央値）までの F0 の上がりを半音で出す（parselmouth・pitch 120〜700Hz・10ms 刻み）
- `scripts/plot_f0.py` — 全角と半角の F0 を上下に並べた図を作る
- `output/ashita-hima-{fullwidth,halfwidth}.wav` — 記事に載せた 2 本（24kHz）

```sh
uv run --with praat-parselmouth python3 -I scripts/f0_rise.py output
# ashita-hima-fullwidth {"min_hz": 221, "min_at": 0.64, "end_hz": 242, "rise_st": 1.5}
# ashita-hima-halfwidth {"min_hz": 223, "min_at": 0.64, "end_hz": 447, "rise_st": 12.1}
uv run --with praat-parselmouth --with matplotlib python3 -I scripts/plot_f0.py /tmp/f0.png
```

音声の生成（課金あり）のスクリプトは載せていない。生成は `POST /v1/text-to-speech/{voice_id}/stream`、`model_id: eleven_v4_turbo`、`language_code: ja`、`output_format: pcm_24000`、voice_settings は既定。
