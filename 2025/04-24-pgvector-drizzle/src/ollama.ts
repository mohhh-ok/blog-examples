import {
  EMBEDDING_DIMENSIONS,
  EMBEDDING_MODEL,
  OLLAMA_BASE_URL,
} from "./constants";

export async function embed(content: string) {
  const response = await fetch(`${OLLAMA_BASE_URL}/api/embed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: EMBEDDING_MODEL, input: content }),
  });
  if (!response.ok) {
    throw new Error(`Ollama embed failed: ${response.status} ${await response.text()}`);
  }
  const data = (await response.json()) as { embeddings: number[][] };
  const embedding = data.embeddings[0];
  if (embedding.length !== EMBEDDING_DIMENSIONS) {
    throw new Error(
      `Unexpected embedding dimensions: ${embedding.length} (expected ${EMBEDDING_DIMENSIONS})`,
    );
  }
  return embedding;
}
