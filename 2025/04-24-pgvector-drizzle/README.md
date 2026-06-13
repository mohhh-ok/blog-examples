# pgvector + Drizzle + OpenAI Embedding

記事: [【AI】Postgres + Drizzle + Embeddingで意味検索する](https://mohhh-ok.github.io/blog/posts/2025/04-24-aipostgres--drizzle--embedding%E3%81%A7%E6%84%8F%E5%91%B3%E6%A4%9C%E7%B4%A2%E3%81%99%E3%82%8B/)

cosine / L1 (Manhattan) 両方を試せます。

## セットアップ

```bash
bun install
cp .env.example .env
# .env の OPENAI_API_KEY を埋める

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
