# blog-examples

ブログ記事 ([mohhh-ok.github.io/blog](https://mohhh-ok.github.io/blog/)) で扱った検証コードの集約リポジトリ。

記事ごとに `YYYY/MM-DD-スラッグ/` のディレクトリで分けています。各ディレクトリの README に記事URLとセットアップ手順があります。

## 一覧

- [2025/04-24-pgvector-drizzle](./2025/04-24-pgvector-drizzle/) — Postgres + pgvector + Drizzle + OpenAI embedding で意味検索（cosine / L1）
- [2026/07-24-web-speech-quality-chrome150](./2026/07-24-web-speech-quality-chrome150/) — Chrome 150 の `SpeechRecognitionOptions.quality`(デフォルト "command")で onresult が返らなくなる問題の最小再現

- [2026/09-13-fish-ref-denoise-ab](./2026/09-13-fish-ref-denoise-ab/) — Fish Audio S2 の zero-shot voice clone で、参照音声に DeepFilterNet 3 の denoise を通すと出力が崩れるかの A/B（N/D/R 3 条件 × ref 8 変種 × 台本 2 種 × n=20、Fisher 正確検定）
- [2026/09-17-jev-character](./2026/09-17-jev-character/) — TypeSafe の System One モデル Jev に自由入力の性格文・状況・来客を渡し、反応（近寄る／様子見／隠れる）の確率分布を受け取ってコード側でサイコロを振る
- [2026/09-18-pageindex-jev](./2026/09-18-pageindex-jev/) — PageIndex 風の「目次の木を降りる検索」を TypeSafe の Jev で。4 つの docs サイトを 1 本の木にし、Haiku が書いた目録を Choice で降り、BM25 で固有文字列を拾い、Noul で答えの段落を確認（48 問で top1 94%、1 問 1.8 秒・$0.002）
- [2026/09-21-remotion-subtitle-overlay](./2026/09-21-remotion-subtitle-overlay/) — Remotion で字幕の ON/OFF だけを切り替えるとき、背景+webm+字幕を毎回全部描く（X）か、webm 焼き込み済み動画に字幕だけ重ねる（Y: Remotion 描画 / Z: 透過 webm を ffmpeg overlay）かの速度比較

## Secret スキャン

[gitleaks](https://github.com/gitleaks/gitleaks) を設定済み。

- GitHub Actions: push / PR で自動実行（`.github/workflows/gitleaks.yml`）
- ローカル: [pre-commit](https://pre-commit.com/) を入れて `pre-commit install` すると `.pre-commit-config.yaml` の hook が走ります

手動スキャン:

```bash
brew install gitleaks
gitleaks detect --source . --verbose
```
