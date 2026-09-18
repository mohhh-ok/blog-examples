// 総当たり: 全段落を state 上限に収まるチャンクに分け、チャンクごとに Choice（答えの段落）+ Noul（答えがあるか）を並列に投げる。
// チャンク間の合流は Noul の絶対値で行い、最後に上位候補だけ木探索と同じ verify を通す。
import { TypeSafeClient, choice, noul } from "@typesafe-ai/sdk";
import { pathOf, type Corpus } from "./corpus";
import type { Node } from "./tree";
import type { RequestLog, Result } from "./search";

export type ScanConfig = { chunkTokens: number; paragraphChars: number; keep: number; model: string };
type Para = { key: string; node: Node; text: string };
const NONE = "__none__";

export function paragraphs(corpus: Corpus, paragraphChars: number): Para[] {
  const out: Para[] = [];
  for (const node of corpus.byId.values()) {
    if (node.level < 1) continue;
    node.text
      .split(/\n\s*\n/)
      .map((x) => x.replace(/\s+/g, " ").trim())
      .filter((x) => x.length > 20)
      .forEach((text, j) => out.push({ key: `${node.id}#${j}`, node, text: `${node.title}: ${text.slice(0, paragraphChars)}` }));
  }
  return out;
}

export function chunk(paras: Para[], chunkTokens: number): Para[][] {
  const chunks: Para[][] = [];
  let cur: Para[] = [], tokens = 0;
  for (const p of paras) {
    const t = Math.ceil(p.text.length / 4) + 8;
    if (cur.length > 0 && (tokens + t > chunkTokens || cur.length >= 250)) { chunks.push(cur); cur = []; tokens = 0; }
    cur.push(p); tokens += t;
  }
  if (cur.length > 0) chunks.push(cur);
  return chunks;
}

export async function scan(client: TypeSafeClient, corpus: Corpus, chunks: Para[][], question: string, cfg: ScanConfig): Promise<Result> {
  const requests: RequestLog[] = [];
  const started = performance.now();
  const results = await Promise.all(
    chunks.map(async (c) => {
      const state = { question, paragraphs: Object.fromEntries(c.map((p) => [p.key, p.text])) };
      const criteria: Record<string, null | string> = Object.fromEntries(c.map((p) => [p.key, null]));
      criteria[NONE] = "No paragraph in `paragraphs` states the answer";
      const t0 = performance.now();
      const res = await client.systemOne({
        state,
        questions: {
          which: choice("Which entry of `paragraphs` states the answer to `question`? Keys are paragraph ids.", criteria),
          has: noul("Does at least one entry of `paragraphs` state the answer to `question`? Yes only if the answer is written there, not merely related."),
        },
        model: cfg.model,
      });
      return { c, res, ms: Math.round(performance.now() - t0) };
    }),
  );
  const wall = Math.round(performance.now() - started);
  let inTok = 0, outTok = 0;
  for (const r of results) { inTok += r.res.usage.input_tokens; outTok += r.res.usage.output_tokens; }
  requests.push({ step: `scan×${chunks.length}`, questions: chunks.length * 2, ms: wall, input_tokens: inTok, output_tokens: outTok });

  const winners = results
    .map((r) => {
      const a = r.res.answers.which;
      const key = a.choice;
      const p = r.c.find((x) => x.key === key);
      return { p, locProb: a.probabilities[key] ?? 0, none: a.probabilities[NONE] ?? 0, has: r.res.answers.has.noul };
    })
    .filter((w): w is typeof w & { p: Para } => w.p !== undefined)
    .sort((a, b) => b.has - a.has)
    .slice(0, cfg.keep);

  if (winners.length === 0) return { ranked: [], requests };
  const sections: Record<string, string> = {};
  const verify: Record<string, ReturnType<typeof noul>> = {};
  winners.forEach((w, i) => {
    sections[`s${i}`] = w.p.text;
    verify[`fits${i}`] = noul(`Does \`sections.s${i}\` state the answer to \`question\`? Yes only if the answer is written there, not merely related.`);
  });
  const t1 = performance.now();
  const v = await client.systemOne({ state: { question, sections }, questions: verify, model: cfg.model });
  requests.push({ step: "verify", questions: winners.length, ms: Math.round(performance.now() - t1), ...v.usage });
  const ranked = winners
    .map((w, i) => ({
      path: { nodes: pathOf(corpus, w.p.node), probs: [], done: true },
      paragraph: w.p.text,
      locProb: w.locProb,
      none: w.none,
      score: w.has,
      fits: (v.answers[`fits${i}`] as { noul: number }).noul,
    }))
    .sort((a, b) => b.fits - a.fits);
  return { ranked, requests };
}
