// corpus/raw/<site>.md を、サイト > ページ > H2 > H3… の木にして corpus/index/<site>.tree.json に書く。
// ページ境界は front matter（--- url: ... ---）があればそれ、無ければ H1。
import { parseMarkdownTree, type Node } from "./tree";

export type SiteTree = { site: string; pages: Node[] };

const FRONT_MATTER = /^---\n(?:url: ?'?([^'\n]+)'?\n)---\n/m;

export function ingest(site: string, markdown: string): SiteTree {
  const chunks = markdown.split(/^---\nurl: ?'?[^'\n]+'?\n---\n/m);
  const urls = [...markdown.matchAll(/^---\nurl: ?'?([^'\n]+)'?\n---\n/gm)].map((m) => m[1]!);
  const pages: Node[] = [];
  let seq = 0;
  const nextId = () => `${site}:${++seq}`;
  const renumber = (n: Node) => {
    n.id = nextId();
    n.children.forEach(renumber);
  };
  if (urls.length > 0) {
    // front matter で区切られたページ。各チャンク内の H1 をページ題にする
    chunks.slice(1).forEach((chunk, i) => {
      const root = parseMarkdownTree(chunk);
      const h1 = root.children.find((c) => c.level === 1);
      const page: Node = {
        id: "",
        title: h1?.title ?? urls[i]!,
        level: 1,
        text: (root.text + (h1?.text ?? "")).trim(),
        children: h1 ? h1.children : root.children,
        url: urls[i],
      };
      // H1 が複数あるページ（稀）は後続 H1 を H2 相当として繋ぐ
      for (const extra of root.children.filter((c) => c.level === 1 && c !== h1)) page.children.push({ ...extra, level: 2 });
      if (page.text.length + page.children.length > 0) pages.push(page);
    });
  } else {
    const root = parseMarkdownTree(markdown.replace(/^<SYSTEM>.*<\/SYSTEM>\n/m, ""));
    for (const c of root.children) if (c.level === 1 && !/^Start of .* documentation$/.test(c.title)) pages.push(c);
  }
  pages.forEach(renumber);
  return { site, pages };
}

if (import.meta.main) {
  const sites = process.argv.slice(2);
  if (sites.length === 0) {
    console.error("usage: bun run src/ingest.ts <site>...   (corpus/raw/<site>.md)");
    process.exit(1);
  }
  for (const site of sites) {
    const md = await Bun.file(`corpus/raw/${site}.md`).text();
    const tree = ingest(site, md);
    const count = (n: Node): number => 1 + n.children.reduce((s, c) => s + count(c), 0);
    const h2 = tree.pages.reduce((s, p) => s + p.children.filter((c) => c.level === 2).length, 0);
    const biggest = tree.pages.reduce((m, p) => Math.max(m, JSON.stringify(p).length), 0);
    await Bun.write(`corpus/index/${site}.tree.json`, JSON.stringify(tree, null, 1));
    console.log(`${site}: pages=${tree.pages.length} h2=${h2} nodes=${tree.pages.reduce((s, p) => s + count(p), 0)} largest page≈${Math.round(biggest / 4)} tokens`);
  }
}
