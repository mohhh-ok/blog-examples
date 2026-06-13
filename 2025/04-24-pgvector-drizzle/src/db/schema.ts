import { index, integer, pgTable, varchar, vector } from "drizzle-orm/pg-core";
import { EMBEDDING_DIMENSIONS } from '../constants';

export const postsTable = pgTable(
  "posts",
  {
    id: integer().primaryKey().generatedAlwaysAsIdentity(),
    content: varchar({ length: 255 }).notNull(),
    embedding: vector({ dimensions: EMBEDDING_DIMENSIONS }).notNull(),
  },
  (table) => [
    index('embedding_hnsw_cosine').using('hnsw', table.embedding.op('vector_cosine_ops')),
    index('embedding_hnsw_l1').using('hnsw', table.embedding.op('vector_l1_ops')),
  ]
);
