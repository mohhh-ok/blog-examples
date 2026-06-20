# 生成音声のライセンス

このディレクトリには各モデルで生成された 7 言語の音声ファイルが含まれます。
**生成物のライセンスはモデルごとに異なります**。

| ディレクトリ | 元モデル | 出力ライセンス | 商用利用 |
|---|---|---|---|
| `f5_tts/` | F5-TTS_v1_Base | CC-BY-NC 4.0 派生扱い | **不可** (非商用のみ) |
| `xtts/` | XTTS-v2 (Coqui) | Coqui Public Model License 準拠 | 別途条件、要確認 |
| `openvoice/` | OpenVoice v2 (MyShell) | MIT | 可 |
| `elevenlabs/` | ElevenLabs eleven_multilingual_v2 | ElevenLabs ToS 準拠 (本リポジトリ所有者の Starter プランで生成) | 可 |

商用利用される場合は `f5_tts/` 配下を除外してください。
ElevenLabs 生成物を再利用する場合は ElevenLabs ToS の attribution 条項に従ってください。

## 参照音声について

`../reference/ref.wav` はリポジトリ所有者の声で、公開を許諾しています。
所有者の声は別途 YouTube 等で公開済みのため、本ファイルの追加公開による
クローン素材としての二次利用余地は実質的に変わりません。
