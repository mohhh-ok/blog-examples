# ElevenLabs Instant Voice Clone の声の類似度

ElevenLabs の Instant Voice Clone (IVC) で作った声を `eleven_v4` で読ませ、参照音声の本人にどれだけ似るか、
試行・文章・言語を変えたときにどれだけ揃うかを測る。
参照音声と生成テキストは [08-26 の測定](../08-26-fish-voice-clone-consistency/) から借りている。

## 手法

- 参照音声: `../08-26-fish-voice-clone-consistency/reference/ref.wav` (筆者本人の声 10.16 秒・24kHz mono・git 管理外)。IVC を 1 つ作り、測定後に削除した
  - `POST /v1/voices/add`、`remove_background_noise=false`。IVC は書き起こしを受け取らない
- モデル: `eleven_v4` (2026-10 時点で公式の models ページが最新のフラッグシップとして挙げるもの)
- 生成: `POST /v1/text-to-speech/{voice_id}?output_format=wav_24000`。`voice_settings`・`seed`・`language_code` は送らない (既定値)
  - 同一文 x 5、異文 x 5、7 言語 x 1
- 測定 (`scripts/measure.py`): resemblyzer `VoiceEncoder` の utterance embedding のコサイン類似度、librosa `pyin` の F0
  (確認用に `yin` でも推定)、faster-whisper (small) の言語判定
- 基準 (`scripts/baseline_other_speaker.py`): クローンではない別人の声 (ライブラリ音声 Shohei、日本語男性) で同一文を生成し、ref との類似度を測る

## 再現手順

08-26 の venv を流用する (resemblyzer・librosa・faster-whisper・requests が入っている)。

```bash
PY=../08-26-fish-voice-clone-consistency/.venv/bin/python
export ELEVENLABS_API_KEY=...
$PY scripts/create_voice.py            # output/voice.json に voice_id を控える
$PY scripts/generate.py                # output/eleven_v4/{same,varied,multilingual}/*.wav
$PY scripts/baseline_other_speaker.py  # output/baseline/
$PY scripts/measure.py                 # output/results.json + output/figures/*.webp (API キー不要)
$PY scripts/delete_voice.py            # voice.json の id と name を照合して削除し、一覧から消えたことを確かめる
```

参照音声のパスは `REF_WAV` 環境変数で差し替えられる。

## 構成

- `scripts/common.py` — 参照音声・テキスト・モデルの定義
- `scripts/create_voice.py` / `scripts/delete_voice.py` — IVC の作成と削除
- `scripts/generate.py` — 17 本生成
- `scripts/baseline_other_speaker.py` — 別人の声の基準
- `scripts/measure.py` — 類似度・F0・言語判定・図
- `output/results.json` — 全測定値
- `output/figures/` — 要約の棒グラフ、11x11 / 8x8 ヒートマップ
- `output/eleven_v4/generation.json` — 生成時のレイテンシ・尺・request id
