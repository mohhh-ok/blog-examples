# blog-examples

ブログ記事 ([mohhh-ok.github.io/blog](https://mohhh-ok.github.io/blog/)) で扱った検証コードの集約リポジトリ。

記事ごとに `YYYY/MM-DD-スラッグ/` のディレクトリで分けています。各ディレクトリの README に記事URLとセットアップ手順があります。

## 一覧

- [2025/04-24-pgvector-drizzle](./2025/04-24-pgvector-drizzle/) — Postgres + pgvector + Drizzle + OpenAI embedding で意味検索（cosine / L1）
- [2026/07-24-web-speech-quality-chrome150](./2026/07-24-web-speech-quality-chrome150/) — Chrome 150 の `SpeechRecognitionOptions.quality`(デフォルト "command")で onresult が返らなくなる問題の最小再現

## Secret スキャン

[gitleaks](https://github.com/gitleaks/gitleaks) を設定済み。

- GitHub Actions: push / PR で自動実行（`.github/workflows/gitleaks.yml`）
- ローカル: [pre-commit](https://pre-commit.com/) を入れて `pre-commit install` すると `.pre-commit-config.yaml` の hook が走ります

手動スキャン:

```bash
brew install gitleaks
gitleaks detect --source . --verbose
```
