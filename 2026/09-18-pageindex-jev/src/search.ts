import { TypeSafeClient, choice, noul } from "@typesafe-ai/sdk";
import { excerpt, subtreeText, type Node } from "./tree";
import { describe, pathOf, type Corpus } from "./corpus";
import { search as bm25Search, type Index } from "./bm25";

export type Config = {
  beam: number; // 残す経路の本数
  excerptChars: number; // 各子ノードの criteria に載せる本文文字数
  paragraphChars: number; // 段落特定で各段落を criteria に載せる文字数
  noneThreshold: number; // Choice の none がこれ以上なら経路を捨てる
  model: string;
  lexical: number; // BM25 で拾って locate 段に足す候補数
};

export type Path = { nodes: Node[]; probs: number[]; done: boolean; lexical?: boolean };
export type RequestLog = { step: string; questions: number; ms: number; input_tokens: number; output_tokens: number };
export type Result = {
  ranked: { path: Path; paragraph: string; locProb: number; none: number; score: number; fits: number }[];
  requests: RequestLog[];
};

const NONE = "__none__";
const SELF = "__this_section__";

export const pathScore = (p: Path) =>
  p.lexical ? 0 : p.probs.length === 0 ? 1 : Math.exp(p.probs.reduce((s, x) => s + Math.log(Math.max(x, 1e-9)), 0) / p.probs.length);

const tail = (p: Path): Node => p.nodes[p.nodes.length - 1]!;
const titles = (p: Path) => p.nodes.slice(1).map((n) => n.title).join(" > ");
const sameTail = (a: Path, b: Path) => tail(a).id === tail(b).id;

export async function search(client: TypeSafeClient, corpus: Corpus, index: Index, question: string, cfg: Config): Promise<Result> {
  const requests: RequestLog[] = [];
  let frontier: Path[] = [{ nodes: [corpus.root], probs: [], done: false }];

  for (let depth = 0; depth < 8; depth++) {
    const expanding = frontier.filter((p) => !p.done && tail(p).children.length > 0);
    if (expanding.length === 0) break;
    const finished = frontier.filter((p) => !expanding.includes(p)).map((p) => ({ ...p, done: true }));

    // 経路ごとに Choice 1 本。全経路分を 1 リクエストにまとめる（speculative fan-out）
    const questions: Record<string, ReturnType<typeof choice>> = {};
    for (const [i, p] of expanding.entries()) {
      const t = tail(p);
      const criteria: Record<string, string> = {};
      for (const c of t.children) criteria[c.id] = describe(corpus, c, cfg.excerptChars);
      if (t.level >= 1 && excerpt(t, 40).length > 0) criteria[SELF] = `The introductory text of "${t.title}" itself, before any subsection: ${excerpt(t, cfg.excerptChars)}`;
      criteria[NONE] = "None of these sections would contain the answer";
      questions[`p${i}`] = choice(
        `The user is looking for the answer to \`question\` in a document. We are inside the section "${t.title || "(document root)"}". Which of these subsections is most likely to contain the answer?`,
        criteria,
      );
    }
    const started = performance.now();
    const res = await client.systemOne({ state: { question }, questions, model: cfg.model });
    requests.push({ step: `depth ${depth}`, questions: Object.keys(questions).length, ms: Math.round(performance.now() - started), ...res.usage });

    const candidates: Path[] = [...finished];
    for (const [i, p] of expanding.entries()) {
      const answer = res.answers[`p${i}`] as { probabilities: Record<string, number> };
      const probs = answer.probabilities;
      if ((probs[NONE] ?? 0) >= cfg.noneThreshold) continue;
      const t = tail(p);
      const sorted = Object.entries(probs)
        .filter(([k]) => k !== NONE)
        .sort((a, b) => b[1] - a[1])
        .slice(0, cfg.beam);
      for (const [id, prob] of sorted) {
        if (id === SELF) candidates.push({ nodes: p.nodes, probs: [...p.probs, prob], done: true });
        else {
          const child = t.children.find((c) => c.id === id)!;
          candidates.push({ nodes: [...p.nodes, child], probs: [...p.probs, prob], done: false });
        }
      }
    }
    frontier = candidates.sort((a, b) => pathScore(b) - pathScore(a)).slice(0, cfg.beam);
    if (process.env.DEBUG_SEARCH) {
      for (const [i, p] of expanding.entries()) {
        const probs = (res.answers[`p${i}`] as { probabilities: Record<string, number> }).probabilities;
        const top = Object.entries(probs).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([id, pr]) => `${id === NONE ? "(none)" : id === SELF ? "(this section)" : tail(p).children.find((c) => c.id === id)?.title} ${pr.toFixed(3)}`);
        console.error(`[depth ${depth}] from "${titles(p) || "(root)"}" (${tail(p).children.length} options): ${top.join(" | ")}`);
      }
    }
  }

  // 字句一致の経路: 要約から落ちる固有文字列（関数名・エラー文）を BM25 で拾い、locate 段の候補に足す
  const lexicalHits: string[] = [];
  for (const hit of bm25Search(index, question, cfg.lexical)) {
    const node = corpus.byId.get(hit.id);
    if (!node) continue;
    const path: Path = { nodes: pathOf(corpus, node), probs: [], done: true, lexical: true };
    if (!frontier.some((p) => sameTail(p, path))) { frontier.push(path); lexicalHits.push(hit.id); }
  }
  if (frontier.length === 0) return { ranked: [], requests }; // 根から「該当なし」で止まった

  // 段落の特定: 候補ごとに小節全体を段落に割り、Choice で答えの段落を選ぶ（line-by-line search と同じ形）
  const paragraphsOf = (p: Path) =>
    subtreeText(tail(p))
      .split(/\n\s*\n/)
      .map((x) => x.replace(/\s+/g, " ").trim())
      .filter((x) => x.length > 20)
      .slice(0, 254);
  const locate: Record<string, ReturnType<typeof choice>> = {};
  const paras = frontier.map(paragraphsOf);
  frontier.forEach((p, i) => {
    const criteria: Record<string, string> = {};
    paras[i]!.forEach((text, j) => (criteria[`q${j}`] = text.slice(0, cfg.paragraphChars)));
    criteria[NONE] = "No paragraph here states the answer";
    locate[`loc${i}`] = choice(`Which paragraph of the section "${titles(p)}" states the answer to \`question\`?`, criteria);
  });
  let started = performance.now();
  const loc = await client.systemOne({ state: { question }, questions: locate, model: cfg.model });
  requests.push({ step: "locate", questions: frontier.length, ms: Math.round(performance.now() - started), ...loc.usage });

  const picked = frontier.map((p, i) => {
    const a = loc.answers[`loc${i}`] as { choice: string; probabilities: Record<string, number> };
    const j = Number(a.choice.replace("q", ""));
    return { path: p, paragraph: a.choice === NONE ? "" : paras[i]![j]!, locProb: a.probabilities[a.choice] ?? 0, none: a.probabilities[NONE] ?? 0 };
  });

  // 最終確認: 選んだ段落を state に載せ、Noul で「答えが書いてあるか」を独立に問う
  const sections: Record<string, string> = {};
  const verify: Record<string, ReturnType<typeof noul>> = {};
  picked.forEach((c, i) => {
    sections[`s${i}`] = c.paragraph || "(no paragraph selected)";
    verify[`fits${i}`] = noul(`Does \`sections.s${i}\` state the answer to \`question\`? Yes only if the answer is written there, not merely related.`);
  });
  started = performance.now();
  const res = await client.systemOne({ state: { question, sections }, questions: verify, model: cfg.model });
  requests.push({ step: "verify", questions: picked.length, ms: Math.round(performance.now() - started), ...res.usage });

  const ranked = picked
    .map((c, i) => ({ ...c, score: pathScore(c.path), fits: (res.answers[`fits${i}`] as { noul: number }).noul }))
    .sort((a, b) => b.fits - a.fits);
  return { ranked, requests };
}

export { titles as pathTitles };
