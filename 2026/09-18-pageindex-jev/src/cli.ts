import { TypeSafeClient } from "@typesafe-ai/sdk";
import { z } from "zod";
import { loadCorpus, subtreeText } from "./corpus";
import { buildIndex } from "./bm25";
import { search, pathTitles, type Config } from "./search";

const env = z
  .object({
    TYPESAFE_API_KEY: z.string().min(1),
    TYPESAFE_MODEL: z.string().default("jev-latest"),
    BEAM: z.coerce.number().int().min(1).default(3),
    EXCERPT_CHARS: z.coerce.number().int().default(160),
    PARAGRAPH_CHARS: z.coerce.number().int().default(400),
    NONE_THRESHOLD: z.coerce.number().default(0.6),
    SITES: z.string().default("zod.dev,hono.dev,elysiajs.com,vite.dev"),
    LEXICAL: z.coerce.number().int().default(3),
  })
  .parse(process.env);

const question = process.argv.slice(2).join(" ").trim();
if (!question) {
  console.error('usage: bun run src/cli.ts "your question"   (SITES=a,b BEAM=3 ...)');
  process.exit(1);
}

const cfg: Config = { beam: env.BEAM, excerptChars: env.EXCERPT_CHARS, paragraphChars: env.PARAGRAPH_CHARS, noneThreshold: env.NONE_THRESHOLD, model: env.TYPESAFE_MODEL, lexical: env.LEXICAL };
const sites = env.SITES.split(",");
const corpus = await loadCorpus(sites);
const index = buildIndex([...corpus.byId.values()].filter((n) => n.level >= 1 && n.text.trim().length > 0).map((n) => ({ id: n.id, text: `${n.title}\n${subtreeText(n)}` })));
console.log(`sites: ${sites.join(", ")}  nodes=${corpus.byId.size - 1}  manifests=${Object.keys(corpus.manifests).length}`);
console.log(`question: ${question}\n`);

const client = new TypeSafeClient({ apiKey: env.TYPESAFE_API_KEY });
const t0 = performance.now();
const result = await search(client, corpus, index, question, cfg);
const total = Math.round(performance.now() - t0);

if (result.ranked.length === 0) console.log("no section in this document is likely to answer the question\n");
for (const r of result.ranked) {
  console.log(`fits=${r.fits.toFixed(2)}  path=${r.path.lexical ? "bm25" : r.score.toFixed(2)}  para=${r.locProb.toFixed(2)}  ${pathTitles(r.path)}`);
  console.log(`    ${r.paragraph.slice(0, 300) || "(none)"}\n`);
}
console.log("requests:");
for (const q of result.requests) console.log(`  ${q.step.padEnd(9)} questions=${q.questions}  ${q.ms}ms  in=${q.input_tokens} out=${q.output_tokens}`);
console.log(`total ${total}ms, ${result.requests.reduce((s, q) => s + q.input_tokens, 0)} input tokens`);
