// corpus/eval/<site>.eval.json の質問を全部流し、正解の節に当たった率を出す。
//   bun run src/eval.ts   (env SITES, BEAM, LEXICAL などは cli.ts と同じ)
import { TypeSafeClient } from "@typesafe-ai/sdk";
import { z } from "zod";
import { buildIndex, search as bm25Search } from "./bm25";
import { loadCorpus, pathOf, subtreeText } from "./corpus";
import { search, type Config } from "./search";
import { chunk, paragraphs, scan } from "./scan";

const env = z
  .object({
    TYPESAFE_API_KEY: z.string().min(1),
    TYPESAFE_MODEL: z.string().default("jev-latest"),
    BEAM: z.coerce.number().int().min(1).default(3),
    EXCERPT_CHARS: z.coerce.number().int().default(160),
    PARAGRAPH_CHARS: z.coerce.number().int().default(400),
    NONE_THRESHOLD: z.coerce.number().default(0.6),
    LEXICAL: z.coerce.number().int().default(3),
    SITES: z.string().default("zod.dev,hono.dev,elysiajs.com,vite.dev"),
    LIMIT: z.coerce.number().int().default(0),
    MODE: z.enum(["tree", "scan", "bm25"]).default("tree"), // bm25: Jev を使わず全文検索の上位だけで判定
    MANIFESTS: z.coerce.number().int().default(1), // 0 で目録を使わず見出し + 本文冒頭だけで降りる
    CHUNK_TOKENS: z.coerce.number().int().default(10000),
    KEEP: z.coerce.number().int().default(6),
  })
  .parse(process.env);
type EvalItem = { id: string; path: string[]; question: string; answer: string };

const sites = env.SITES.split(",");
const corpus = await loadCorpus(sites);
if (env.MANIFESTS === 0) corpus.manifests = {};
const index = buildIndex([...corpus.byId.values()].filter((n) => n.level >= 1 && n.text.trim().length > 0).map((n) => ({ id: n.id, text: `${n.title}\n${subtreeText(n)}` })));
const cfg: Config = { beam: env.BEAM, excerptChars: env.EXCERPT_CHARS, paragraphChars: env.PARAGRAPH_CHARS, noneThreshold: env.NONE_THRESHOLD, model: env.TYPESAFE_MODEL, lexical: env.LEXICAL };
const client = new TypeSafeClient({ apiKey: env.TYPESAFE_API_KEY });
const chunks = env.MODE === "scan" ? chunk(paragraphs(corpus, 1200), env.CHUNK_TOKENS) : [];

const items: EvalItem[] = [];
for (const site of sites) {
  const f = Bun.file(`corpus/eval/${site}.eval.json`);
  if (await f.exists()) items.push(...((await f.json()) as EvalItem[]).map((x) => ({ ...x, id: x.id.includes(":") ? x.id : `${site}:${x.id}` })));
}
const subset = env.LIMIT > 0 ? items.slice(0, env.LIMIT) : items;
console.log(`mode=${env.MODE} manifests_used=${env.MANIFESTS} sites=${sites.join(",")} manifests=${Object.keys(corpus.manifests).length} questions=${subset.length} beam=${cfg.beam} lexical=${cfg.lexical}${env.MODE === "scan" ? ` chunks=${chunks.length} (${env.CHUNK_TOKENS} tokens each)` : ""}\n`);

// 正解判定: 返した段落が正解ノードの本文（子孫込み）に含まれる、または返したノードが正解の祖先/子孫
const norm = (s: string) => s.replace(/\s+/g, " ").trim();
let top1 = 0, top3 = 0, lexWins = 0, empty = 0, totalMs = 0, totalTok = 0, reqs = 0;
const misses: string[] = [];
for (const item of subset) {
  const gold = corpus.byId.get(item.id);
  if (!gold) { console.log(`skip ${item.id}: not in corpus`); continue; }
  const goldText = norm(subtreeText(gold));
  const goldPath = new Set(pathOf(corpus, gold).map((n) => n.id));
  const t0 = performance.now();
  const r =
    env.MODE === "scan" ? await scan(client, corpus, chunks, item.question, { chunkTokens: env.CHUNK_TOKENS, paragraphChars: 1200, keep: env.KEEP, model: env.TYPESAFE_MODEL })
    : env.MODE === "bm25" ? { requests: [] as { input_tokens: number }[], ranked: bm25Search(index, item.question, 3).map((h) => ({ path: { nodes: pathOf(corpus, corpus.byId.get(h.id)!), probs: [], done: true, lexical: true }, paragraph: "", fits: h.score })) }
    : await search(client, corpus, index, item.question, cfg);
  totalMs += performance.now() - t0;
  totalTok += r.requests.reduce((s, q) => s + q.input_tokens, 0);
  reqs += r.requests.length;
  const hit = (x: (typeof r.ranked)[number]) => {
    const tailId = x.path.nodes[x.path.nodes.length - 1]!.id;
    if (goldPath.has(tailId) || pathOf(corpus, x.path.nodes[x.path.nodes.length - 1]!).some((n) => n.id === gold.id)) return true;
    return x.paragraph.length > 0 && goldText.includes(norm(x.paragraph).slice(0, 200));
  };
  const first = r.ranked[0];
  if (!first) { empty++; misses.push(`EMPTY  ${item.path.join(" > ")}\n       Q: ${item.question}`); continue; }
  if (hit(first)) { top1++; top3++; if (first.path.lexical) lexWins++; }
  else if (r.ranked.slice(1, 3).some(hit)) { top3++; misses.push(`TOP3   ${item.path.join(" > ")}\n       Q: ${item.question}\n       got: ${first.path.nodes.slice(1).map((n) => n.title).join(" > ")}`); }
  else misses.push(`MISS   ${item.path.join(" > ")}\n       Q: ${item.question}\n       got: ${first.path.nodes.slice(1).map((n) => n.title).join(" > ")} (fits ${first.fits.toFixed(2)})`);
}
const n = subset.length;
console.log(`top1 ${top1}/${n} (${((100 * top1) / n).toFixed(0)}%)  top3 ${top3}/${n} (${((100 * top3) / n).toFixed(0)}%)  empty ${empty}  top1-by-bm25 ${lexWins}`);
console.log(`avg ${(totalMs / n).toFixed(0)}ms, ${(reqs / n).toFixed(1)} requests, ${Math.round(totalTok / n)} input tokens per question\n`);
for (const m of misses) console.log(m);
