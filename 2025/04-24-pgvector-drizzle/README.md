# pgvector + Drizzle + Ollama Embedding

記事: [【AI】Postgres + Drizzle + Embeddingで意味検索する](https://mohhh-ok.github.io/blog/posts/2025/04-24-aipostgres--drizzle--embedding%E3%81%A7%E6%84%8F%E5%91%B3%E6%A4%9C%E7%B4%A2%E3%81%99%E3%82%8B/)

意味検索のサンプルに加えて、**長文埋め込みの希釈現象**（「京都の◯◯」というタイトルの文書が、本文を専門用語で固めると「京都」検索でヒットしなくなる）を観察するための実験コーパスを同梱しています。

検索結果は cosine / L1 / L2 の3つの距離でランキングを並べて比較できます。埋め込みモデルは [bge-m3](https://ollama.com/library/bge-m3)（多言語対応、1024次元、L2 正規化済み）を Ollama 経由で使います。

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
bun run reseed
```

`reseed` は既存行を全削除してから投入します。

## 検索

```bash
bun run search 京都
bun run search 和菓子
bun run search 大阪
```

1回のコマンドで cosine / L1 / L2 の3ランキングと各ドキュメント全文が表示されます。

## コーパスの構成

`src/insert.ts` に2種類のデータが入っています。

- **短文**: `京都が好きだ` などの純粋な Kyoto シグナル、`大阪の下町を散歩した` などの近接ノイズ
- **長文**: タイトル相当としては「京都の和菓子文化／伝統工芸／地下鉄延伸計画」だが、本文は和菓子製法・職人論・土木計画の専門用語で固め、京都への言及は末尾の1文だけ

`search 京都` で長文 Kyoto 記事が短文に負ける（場合によっては「大阪」短文にも負ける）と、希釈効果が観察できます。

## モデルを差し替えたい場合

`src/constants.ts` の `EMBEDDING_MODEL` と `EMBEDDING_DIMENSIONS` を変更してください。次元数を変えたらスキーマも変わるため、`posts` テーブルを drop してから `bun run db:push` し直す必要があります。

## 補足: 距離関数の関係

bge-m3 は L2 正規化された単位ベクトルを返すため、cosine と L2 はランキングが**完全に一致**します（`|a−b|² = 2(1 − cos θ)` の関係）。L1 は理論的等価ではありませんが、経験的にほぼ揃います。距離関数の違いで結果を変えたい場合は、非正規化ベクトルを返すモデル（例: Google Gemini）に差し替える必要があります。
