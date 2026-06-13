# pgvector + Drizzle + Ollama Embedding

記事: [【AI】Postgres + Drizzle + Embeddingで意味検索する](https://mohhh-ok.github.io/blog/posts/2025/04-24-aipostgres--drizzle--embedding%E3%81%A7%E6%84%8F%E5%91%B3%E6%A4%9C%E7%B4%A2%E3%81%99%E3%82%8B/)

cosine / L1 (Manhattan) 両方を試せます。

埋め込みモデルは [bge-m3](https://ollama.com/library/bge-m3)（多言語対応、1024次元）を Ollama 経由で使います。

## 前提

- [Ollama](https://ollama.com/) がホストで動いていること
- Docker

## セットアップ

```bash
ollama pull bge-m3

bun install
cp .env.example .env

docker compose up -d
bun run db:push
bun run insert
```

## 検索

```bash
# cosine
bun run search 音楽
bun run search お年寄り

# L1 (Manhattan)
bun run search:l1 音楽
bun run search:l1 お年寄り
```

## モデルを差し替えたい場合

`src/constants.ts` の `EMBEDDING_MODEL` と `EMBEDDING_DIMENSIONS` を変更してください。次元数を変えたらスキーマも変わるため、`posts` テーブルを drop してから `bun run db:push` し直す必要があります。
