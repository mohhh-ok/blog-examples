import 'dotenv/config';
import { db } from './db';
import { postsTable } from "./db/schema";
import { embed } from './openai';
import { cosineDistance } from 'drizzle-orm';

async function main() {
  const query = process.argv[2];
  if (!query) throw new Error('no query');
  const embedding = await embed(query);
  const result = await db
    .select({
      content: postsTable.content,
      distance: cosineDistance(postsTable.embedding, embedding),
    })
    .from(postsTable)
    .orderBy(cosineDistance(postsTable.embedding, embedding));
  console.log(result);
}

main();
