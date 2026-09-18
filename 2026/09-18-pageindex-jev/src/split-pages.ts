// tree.json のページを corpus/work/<site>/<n>.md に書き出し、サブエージェント用の仕事の束（chunks.json）を作る。
//   bun run src/split-pages.ts <site>...    env CHUNK_CHARS（既定 150000）
import type { SiteTree } from "./ingest";
import { pageDocument } from "./manifest";

const CHUNK_CHARS = Number(process.env.CHUNK_CHARS ?? 150000);
const sites = process.argv.slice(2);
const chunks: { site: string; files: string[]; chars: number }[] = [];
for (const site of sites) {
  const tree = (await Bun.file(`corpus/index/${site}.tree.json`).json()) as SiteTree;
  let cur = { site, files: [] as string[], chars: 0 };
  for (const page of tree.pages) {
    const { text } = pageDocument(page);
    const file = `corpus/work/${site}/${page.id.split(":")[1]}.md`;
    await Bun.write(file, text);
    if (cur.chars + text.length > CHUNK_CHARS && cur.files.length > 0) { chunks.push(cur); cur = { site, files: [], chars: 0 }; }
    cur.files.push(file); cur.chars += text.length;
  }
  if (cur.files.length > 0) chunks.push(cur);
}
await Bun.write("corpus/work/chunks.json", JSON.stringify(chunks, null, 1));
chunks.forEach((c, i) => console.log(`chunk ${i}: ${c.site} ${c.files.length} pages ${Math.round(c.chars / 1000)}k chars`));
