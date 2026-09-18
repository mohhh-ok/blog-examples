# pageindex-jev

PageIndex（Vectorless RAG。目次の木を LLM が読みながら降りる検索）の「降りる判断」を TypeSafe の Jev に置き換えた試作。
複数の docs サイトを 1 本の木（サイト > ページ > H2 > H3…）にして、質問に答える段落を探す。

## 構成

| 段 | 何をするか | 使うもの |
|---|---|---|
| 前処理 1 | `corpus/raw/<site>.md`（各サイトの llms-full.txt）を見出し木にする | `src/ingest.ts`（front matter か H1 でページを切る） |
| 前処理 2 | ページと H2 ごとに「目録」（要約でなく棚卸し）を書く | Claude Code のサブエージェント（Haiku）。仕様は `corpus/work/INSTRUCTIONS.md`、指示文は `corpus/work/AGENT_PROMPT.md` |
| 探索 1 | 各段で経路ごとに Choice 1 本（子ノードの目録が選択肢、「該当なし」付き）を 1 リクエストにまとめ、ビーム幅 3 で降りる | Jev（`src/search.ts`） |
| 探索 2 | 目録から落ちる固有文字列（関数名・エラー文）を BM25 で別経路から拾い、候補に足す | `src/bm25.ts` |
| 探索 3 | 候補の節を段落に割り、Choice で答えの段落を選び、Noul で「答えが書いてあるか」を確認 | Jev |
| 比較用 | 総当たり: 全段落を 10k トークンずつのチャンクにして並列に投げ、Noul で合流 | `src/scan.ts` |
| 評価 | 節を seeded 乱数で選び、その節だけで答えられる質問をサブエージェントに書かせ、当たり率を測る | `src/make-eval.ts` + `corpus/eval/INSTRUCTIONS.md`、`src/eval.ts` |

要約を「目録」にした理由: 要約は書き手が重要と思った点に絞るので情報が消える。木を降りる判定に要るのは「この下に答えがあるか」の再現率なので、扱う対象・識別子・数値・答えられる質問を列挙する形式にした。本文は末端に丸ごと残り、要約に頼るのは中間ノードだけ。

## 使い方

```sh
cp .env.example .env               # TYPESAFE_API_KEY を書く
set -a; . ./.env; set +a
scripts/fetch-corpus.sh            # corpus/raw/<site>.md（git には入れていない）
bun run src/ingest.ts zod.dev hono.dev elysiajs.com vite.dev   # corpus/index/<site>.tree.json
bun run src/split-pages.ts zod.dev hono.dev elysiajs.com vite.dev  # corpus/work/<site>/<n>.md（サブエージェントの入力）
#   → サブエージェントが corpus/work/<site>/<n>.json を書く（AGENT_PROMPT.md）
bun run src/merge-manifests.ts zod.dev hono.dev elysiajs.com vite.dev  # corpus/index/<site>.summaries.json
bun run src/cli.ts "How do I make a schema that accepts a string but outputs a number?"
EVAL_PER_SITE=12 bun run src/make-eval.ts zod.dev hono.dev elysiajs.com vite.dev  # corpus/eval/<site>.todo.md → サブエージェントが .eval.json
MODE=tree bun run src/eval.ts
MODE=scan SITES=zod.dev CHUNK_TOKENS=10000 bun run src/eval.ts
MODE=bm25 TYPESAFE_API_KEY=unused bun run src/eval.ts   # Jev を使わず BM25 の上位 3 節だけで判定
```

環境変数: `SITES`（既定は上の 4 つ）、`BEAM=3`、`LEXICAL=3`（BM25 で足す候補数）、`EXCERPT_CHARS=160`（目録が無いノードの説明の長さ）、`PARAGRAPH_CHARS=400`、`NONE_THRESHOLD=0.6`、`TYPESAFE_MODEL=jev-latest`。 `DEBUG_SEARCH=1` で各段の Choice の上位 4 件を stderr に出す。

## データ

`corpus/raw/` に各サイトの llms-full.txt（2026-09-18 取得）。他サイトの文書そのものと、それを組み替えただけの `tree.json`・`work/*/*.md` は git に入れず、`scripts/fetch-corpus.sh` と `ingest` / `split-pages` で作り直す。サブエージェントが書いた目録（`work/*/*.json`・`summaries.json`）と評価セット（`corpus/eval/`）は入れてある。

| サイト | サイズ | ページ | H2 |
|---|---|---|---|
| zod.dev | 0.29 MB | 16 | 122 |
| hono.dev | 0.37 MB | 87 | 444 |
| elysiajs.com | 0.46 MB | 89 | 377 |
| vite.dev | 0.43 MB | 40 | 334 |

目録は 1,492 件。Haiku のサブエージェント 11 体（1 体 150k 文字）で約 12 分、うち 14 ページは JSON が壊れて Sonnet 1 体で書き直し。

## 結果（2026-09-18）

方式ごとに 1 実験。ケース名は記事・図と共通。

| 方式 | 試したこと | 対象 | ケース |
|---|---|---|---|
| 木探索 | 降りるときの候補を何で出すか（目録 / BM25 の有無） | 4 サイト 48 問（各サイト 12 問） | 1-a 目録 + BM25 / 1-b 目録のみ / 1-c BM25 のみ |
| 全文検索 | Jev を使わず BM25 の上位 3 節だけ（基準線） | 4 サイト 48 問 / Zod + Hono 24 問 | 0 BM25 のみ |
| 総当たり | 木探索（1-a）と同じ質問で比較 | Zod + Hono 24 問（木探索の 48 問のうち 2 サイトぶん） | 2-a 木探索（1-a と同じ設定） / 2-b 総当たり |
| 予備 | 動作確認 | Zod 12 問 | 木探索（1-a）/ 総当たり |

| ケース | 中間ノードの説明文 | BM25 | top1 | top3 | 1 問の時間 | 1 問の入力トークン | 1 問の費用（$0.042/Mtok） | 実行 |
|---|---|---|---|---|---|---|---|---|
| 1-a 目録 + BM25 | 目録 | あり | 45/48 (94%) | 48/48 | 1.8 秒 | 55k | $0.0023 | `MODE=tree bun run src/eval.ts` |
| 1-b 目録のみ | 目録 | なし | 38/48 (79%) | 40/48 | 1.9 秒 | 51k | $0.0021 | `LEXICAL=0 …` |
| 1-c BM25 のみ | 見出し + 本文冒頭 160 字 | あり | 43/48 (90%) | 48/48 | 1.7 秒 | 19k | $0.0008 | `MANIFESTS=0 …` |
| 0 BM25 のみ（Jev なし） | – | あり | 43/48 (90%) | 48/48 | 1 ms | 0 | $0 | `MODE=bm25 …` |
| 0 BM25 のみ（Jev なし、2 サイト） | – | あり | 22/24 (92%) | 24/24 | 1 ms | 0 | $0 | `SITES=zod.dev,hono.dev MODE=bm25 …` |
| 2-a 木探索 | 目録 | あり | 22/24 (92%) | 24/24 | 2.6 秒 | 38k | $0.0016 | `SITES=zod.dev,hono.dev MODE=tree …` |
| 2-b 総当たり（10k チャンク × 22、並列） | – | – | 23/24 (96%) | 24/24 | 1.2 秒 | 335k | $0.014 | `SITES=zod.dev,hono.dev MODE=scan CHUNK_TOKENS=10000 …` |
| 予備 木探索 | 目録 | あり | 11/12 | 12/12 | 1.8 秒 | 25k | $0.001 | `SITES=zod.dev MODE=tree …` |
| 予備 総当たり（10k チャンク × 9） | – | – | 11/12 | 12/12 | 1.7 秒 | 145k | $0.006 | `SITES=zod.dev MODE=scan …` |

- 1-a の top1 45 件のうち 7 件は BM25 経路の候補が勝った
- BM25 のみ（0）は節を返すので判定が粗い。top1 43 件のうち正解の節そのものが 34、正解の親（平均 4,500 字）が 9。木探索は段落まで絞って返す
- BM25 のみは質問が文書の語をそのまま含む評価だから出る数字で、言い換え・別言語の質問には効かない（測っていない）
- 切り分け（木探索）: BM25 を外す（1-b）と 94% → 79%、目録を外す（1-c）と 94% → 90%。この評価セットでは目録より BM25 の寄与が大きい。ただし評価質問は「その節だけで答えられる具体的な細部（オプション名・値・エラー文）」を聞く作りなので、固有文字列の一致に有利な設定になっている。言い換えの多い質問では逆転しうる
- 総当たり（2-b）は 2 サイト（コーパス約 165k トークン）でも 1 問 1.2 秒で終わり、木探索より速くて当たる。代わりにトークンは 9 倍。コーパスが 64k を超えても並列に投げれば時間は伸びず、費用だけがコーパス量に比例する。4 サイト 48 問なら 1 問約 800k トークン（$0.03）、Cloudflare docs 級（1,500 万トークン）なら 1 問 $0.6 とレート上限（25 万トークン/秒）で 60 秒
- 目録は「該当なし」の判定にも効いていて、目録なし + BM25 なしの組は測っていない
- 1-a で外した 3 問はいずれも「同じ内容を別ページでも扱っている」もので、正解は 2〜3 位に入っている
- Jev の上限は 1 リクエスト 64k トークン（state は 32k）。根の段は 4 サイト、ページ段は最大 89 ページ分の目録で 1 リクエストに収まる。ページ数が 255 を超えるサイトはチャンク分けが要る

