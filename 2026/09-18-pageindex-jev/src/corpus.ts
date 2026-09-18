// 複数サイトの tree.json と summaries.json を 1 本の木（root > site > page > H2 …）に束ねる。
import type { SiteTree } from "./ingest";
import { excerpt, subtreeText, type Node } from "./tree";

export type Corpus = {
  root: Node;
  parent: Map<string, Node>;
  byId: Map<string, Node>;
  manifests: Record<string, string>; // node id → Haiku が書いた目録（ページと H2 のみ）
};

export async function loadCorpus(sites: string[]): Promise<Corpus> {
  const root: Node = { id: "root", title: "(all sites)", level: -1, text: "", children: [] };
  const manifests: Record<string, string> = {};
  for (const site of sites) {
    const tree = (await Bun.file(`corpus/index/${site}.tree.json`).json()) as SiteTree;
    const f = Bun.file(`corpus/index/${site}.summaries.json`);
    if (await f.exists()) Object.assign(manifests, await f.json());
    root.children.push({ id: `site:${site}`, title: site, level: 0, text: "", children: tree.pages });
  }
  const parent = new Map<string, Node>();
  const byId = new Map<string, Node>();
  const walk = (n: Node) => {
    byId.set(n.id, n);
    for (const c of n.children) { parent.set(c.id, n); walk(c); }
  };
  walk(root);
  return { root, parent, byId, manifests };
}

// Choice の選択肢に載せる説明。目録があればそれ、無ければ見出し + 本文冒頭。
export function describe(c: Corpus, n: Node, fallbackChars: number): string {
  if (n.level === 0) {
    const titles = n.children.slice(0, 40).map((p) => p.title).join(", ");
    return `Documentation site ${n.title}. Pages include: ${titles}`;
  }
  const m = c.manifests[n.id];
  return m ? `${n.title}\n${m}` : `${n.title} — ${excerpt(n, fallbackChars)}`;
}

export function pathOf(c: Corpus, n: Node): Node[] {
  const out: Node[] = [];
  for (let cur: Node | undefined = n; cur; cur = c.parent.get(cur.id)) out.unshift(cur);
  return out;
}

export { subtreeText };
