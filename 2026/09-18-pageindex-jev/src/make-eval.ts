// corpus/index/<site>.tree.json から評価用の質問セットを作り corpus/eval/<site>.eval.json に書く。
// 本文が長い H2 以下のノードを seeded 乱数で EVAL_PER_SITE 件選び、Claude Haiku 4.5 に
// 「この節の本文だけで答えられ、他の節では答えられない」質問を 1 つずつ作らせる。
import type { Node } from "./tree";

type SiteTree = { site: string; pages: Node[] };
type EvalItem = { id: string; path: string[]; question: string; answer: string };


const EVAL_PER_SITE = Number.parseInt(process.env.EVAL_PER_SITE ?? "10", 10) || 10;
const SEED = Number.parseInt(process.env.SEED ?? "1", 10) || 1;
const MIN_LEVEL = 2; // H2 以下
const MIN_TEXT_CHARS = 300;

const treePath = (site: string) => `corpus/index/${site}.tree.json`;
const evalPath = (site: string) => `corpus/eval/${site}.eval.json`;

// --- seeded 乱数（mulberry32）: 同じ SEED + コーパスなら常に同じ選出になる ---
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashString(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  return h;
}

function seededShuffle<T>(items: T[], seed: number): T[] {
  const rng = mulberry32(seed);
  const result = [...items];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    const tmp = result[i]!;
    result[i] = result[j]!;
    result[j] = tmp;
  }
  return result;
}

type Candidate = { node: Node; path: string[] };

// 本文 300 文字以上の H2 以下ノードを全部集める。path はサイト名からその節までの見出し列。
function collectCandidates(tree: SiteTree): Candidate[] {
  const candidates: Candidate[] = [];
  const walk = (node: Node, path: string[]) => {
    const nextPath = [...path, node.title];
    if (node.level >= MIN_LEVEL && node.text.trim().length >= MIN_TEXT_CHARS) {
      candidates.push({ node, path: nextPath });
    }
    for (const child of node.children) walk(child, nextPath);
  };
  for (const page of tree.pages) walk(page, [tree.site]);
  return candidates;
}

async function loadExisting(site: string): Promise<Map<string, EvalItem>> {
  const file = Bun.file(evalPath(site));
  if (!(await file.exists())) return new Map();
  try {
    const items = (await file.json()) as EvalItem[];
    return new Map(items.map((item) => [item.id, item]));
  } catch (err) {
    console.error(`warning: failed to parse existing ${evalPath(site)}, starting fresh (${(err as Error).message})`);
    return new Map();
  }
}

// 質問生成は API でなく Claude Code のサブエージェントに任せる。
// このスクリプトは選んだ節を corpus/eval/<site>.todo.md に書き出すだけ。サブエージェントが corpus/eval/<site>.eval.json を書く。
export const EVAL_INSTRUCTIONS = `You are building an evaluation set for a documentation search system.

The todo file contains sections, each as:

=== ITEM <id>
path: <site> > <page> > ... > <section heading>
<section text>
=== END

For every item, write exactly one specific question in English that:
- can be answered using only that item's text, and
- could NOT be answered by any other section of this documentation: ask about a concrete, specific detail (an option/parameter name, function signature, exact error message, specific value, or specific behavior described there), not a generic summary
- does NOT include the section heading verbatim, or a close paraphrase of it

Also give a short answer: a short excerpt quoted (or closely paraphrased) from the text that answers the question.

Output: one JSON array to the .eval.json path given to you, with one object per item, in the same order:
[{ "id": "<id>", "path": ["<site>", "<page>", ..., "<heading>"], "question": "...", "answer": "..." }, ...]
No extra keys, no markdown fences.`;

async function processSite(site: string): Promise<void> {
  const file = Bun.file(treePath(site));
  if (!(await file.exists())) {
    console.error(`skip ${site}: ${treePath(site)} not found`);
    return;
  }
  const tree = (await file.json()) as SiteTree;
  const candidates = collectCandidates(tree);
  const seed = hashString(`${site}:${SEED}`);
  const selected = seededShuffle(candidates, seed).slice(0, EVAL_PER_SITE);
  const existing = await loadExisting(site);
  const todo = selected.filter((c) => !existing.has(c.node.id));
  const body = todo
    .map((c) => `=== ITEM ${c.node.id}\npath: ${c.path.join(" > ")}\n${c.node.text.trim()}\n=== END`)
    .join("\n\n");
  await Bun.write(`corpus/eval/${site}.todo.md`, body);
  console.log(`${site}: selected ${selected.length} of ${candidates.length} candidates; ${todo.length} to write (${existing.size} already in eval.json)`);
}

if (import.meta.main) {
  const sites = process.argv.slice(2);
  if (sites.length === 0) {
    console.error("usage: bun run src/make-eval.ts <site>...   (EVAL_PER_SITE=10 SEED=1)");
    process.exit(1);
  }
  await Bun.write("corpus/eval/INSTRUCTIONS.md", EVAL_INSTRUCTIONS);
  for (const site of sites) await processSite(site);
}
