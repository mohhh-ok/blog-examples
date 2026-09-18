// corpus/work/<site>/<n>.json（サブエージェントの出力）を corpus/index/<site>.summaries.json にまとめる。
import { z } from "zod";
import type { SiteTree } from "./ingest";
import { pageDocument } from "./manifest";

const Output = z.object({ page: z.string().min(1), sections: z.array(z.object({ index: z.number().int(), manifest: z.string().min(1) })) });
for (const site of process.argv.slice(2)) {
  const tree = (await Bun.file(`corpus/index/${site}.tree.json`).json()) as SiteTree;
  const summaries: Record<string, string> = {};
  const missing: string[] = [];
  let sectionsMissing = 0, repaired = 0;
  for (const page of tree.pages) {
    const f = Bun.file(`corpus/work/${site}/${page.id.split(":")[1]}.json`);
    if (!(await f.exists())) { missing.push(page.id); continue; }
    let raw: unknown;
    const text = await f.text();
    try { raw = JSON.parse(text); } catch {
      // サブエージェントが \` や \' のような JSON に無いエスケープを書くことがあるので、その backslash だけ落として再試行
      try { raw = JSON.parse(text.replace(/\\([^"\\/bfnrtu])/g, "$1")); repaired++; } catch (e) { missing.push(`${page.id} (broken json: ${(e as Error).message})`); continue; }
    }
    const parsed = Output.safeParse(raw);
    if (!parsed.success) { missing.push(`${page.id} (invalid: ${parsed.error.issues[0]?.message})`); continue; }
    const { sections } = pageDocument(page);
    summaries[page.id] = parsed.data.page;
    const got = new Set(parsed.data.sections.map((s) => s.index));
    for (const s of parsed.data.sections) if (sections[s.index]) summaries[sections[s.index]!.id] = s.manifest;
    sectionsMissing += sections.filter((_, i) => !got.has(i)).length;
  }
  await Bun.write(`corpus/index/${site}.summaries.json`, JSON.stringify(summaries, null, 1));
  console.log(`${site}: ${Object.keys(summaries).length} manifests; repaired json=${repaired} pages missing=${missing.length} sections missing=${sectionsMissing}${missing.length ? "\n  " + missing.join("\n  ") : ""}`);
}
