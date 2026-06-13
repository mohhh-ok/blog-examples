import 'dotenv/config';
import { db } from './db';
import { postsTable } from "./db/schema";
import { embed } from './ollama';
import { cosineDistance, l1Distance, l2Distance } from 'drizzle-orm';

async function main() {
  const query = process.argv[2];
  if (!query) throw new Error('no query');
  const embedding = await embed(query);

  const rows = await db
    .select({
      content: postsTable.content,
      cosine: cosineDistance(postsTable.embedding, embedding),
      l1: l1Distance(postsTable.embedding, embedding),
      l2: l2Distance(postsTable.embedding, embedding),
    })
    .from(postsTable);

  const byCosine = [...rows].sort((a, b) => a.cosine - b.cosine);
  const byL1 = [...rows].sort((a, b) => a.l1 - b.l1);
  const byL2 = [...rows].sort((a, b) => a.l2 - b.l2);

  console.log(`query: ${query}\n`);

  console.log('=== Cosine ranking ===');
  byCosine.forEach((r, i) => {
    console.log(`[${i + 1}] cosine=${r.cosine.toFixed(4)} chars=${r.content.length}`);
    console.log(r.content);
    console.log();
  });

  console.log('=== L1 ranking ===');
  byL1.forEach((r, i) => {
    console.log(`[${i + 1}] L1=${r.l1.toFixed(2)} chars=${r.content.length}`);
    console.log(r.content);
    console.log();
  });

  console.log('=== L2 ranking ===');
  byL2.forEach((r, i) => {
    console.log(`[${i + 1}] L2=${r.l2.toFixed(4)} chars=${r.content.length}`);
    console.log(r.content);
    console.log();
  });
}

main();
