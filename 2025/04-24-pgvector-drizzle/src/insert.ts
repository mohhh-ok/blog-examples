import 'dotenv/config';
import { db } from './db';
import { postsTable } from "./db/schema";
import { embed } from './openai';

const TEST_DATA = [
  'みかんを食べている男の人',
  'レストランで食事する家族連れ',
  'ギターを担いだ男二人がバーで飲んでいる',
  '猫をなでる子供',
  '散歩をするおじいさん',
];

async function insert() {
  for (const testData of TEST_DATA) {
    console.log(`Inserting ${testData}`);
    const embedding = await embed(testData);
    await db.insert(postsTable).values({
      content: testData,
      embedding,
    });
  }
}

insert();
