import OpenAI from "openai";
import { EMBEDDING_DIMENSIONS, EMBEDDING_MODEL } from "./constants";

const client = new OpenAI();

export async function embed(content: string) {
  const response = await client.embeddings.create({
    model: EMBEDDING_MODEL,
    input: content,
    dimensions: EMBEDDING_DIMENSIONS,
  });
  return response.data[0].embedding;
}
