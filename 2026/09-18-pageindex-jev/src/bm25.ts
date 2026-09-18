// BM25 全文検索インデックス（外部ライブラリなし）。
// 目的: 技術文書の関数名・オプション名・エラーメッセージのような固有文字列で節を引く経路。
// search.ts の Choice/Noul による要約ベースの探索から落ちる文字列を拾うための補助経路。

export type Doc = { id: string; text: string };

export type Index = {
  docIds: string[];
  docLen: number[];
  avgDocLen: number;
  termFreqs: Map<string, number>[]; // termFreqs[i] = ドキュメント i の term -> 出現回数
  docFreq: Map<string, number>; // term -> その term を含むドキュメント数
  n: number;
};

const K1 = 1.2;
const B = 0.75;

// 英語の一般的なストップワード。技術文書の固有文字列（識別子・エラーメッセージ）を
// 埋もれさせないための最小限の除去で、網羅的な NLP ストップワードリストは意図的に使わない。
const STOPWORDS = new Set([
  "a", "an", "the",
  "and", "or", "but", "if", "then", "else",
  "for", "of", "to", "in", "on", "at", "by", "with", "as", "from",
  "is", "are", "was", "were", "be", "been", "being",
  "it", "this", "that", "these", "those",
]);

const TOKEN_RE = /[a-z0-9_.-]+/g;

// 小文字化 + [a-z0-9_.-]+ で分割。"foo.bar" / "snake_case" / "kebab-case" は
// 1 トークンのまま残しつつ、区切り文字で割った部分トークンも追加する。
export function tokenize(text: string): string[] {
  const raw = text.toLowerCase().match(TOKEN_RE) ?? [];
  const tokens: string[] = [];
  for (const rawToken of raw) {
    const token = rawToken.replace(/^[._-]+|[._-]+$/g, "");
    if (!token) continue;
    tokens.push(token);
    if (/[._-]/.test(token)) {
      for (const part of token.split(/[._-]+/)) {
        if (part && part !== token) tokens.push(part);
      }
    }
  }
  return tokens.filter((t) => !STOPWORDS.has(t));
}

export function buildIndex(docs: Doc[]): Index {
  const docIds: string[] = [];
  const docLen: number[] = [];
  const termFreqs: Map<string, number>[] = [];
  const docFreq = new Map<string, number>();

  for (const doc of docs) {
    const tokens = tokenize(doc.text);
    const tf = new Map<string, number>();
    for (const token of tokens) tf.set(token, (tf.get(token) ?? 0) + 1);
    docIds.push(doc.id);
    docLen.push(tokens.length);
    termFreqs.push(tf);
    for (const term of tf.keys()) docFreq.set(term, (docFreq.get(term) ?? 0) + 1);
  }

  const n = docIds.length;
  const avgDocLen = n === 0 ? 0 : docLen.reduce((s, len) => s + len, 0) / n;

  return { docIds, docLen, avgDocLen, termFreqs, docFreq, n };
}

export function search(index: Index, query: string, k: number): { id: string; score: number }[] {
  if (index.n === 0) return [];
  const queryTerms = [...new Set(tokenize(query))];
  if (queryTerms.length === 0) return [];

  const avgDocLen = index.avgDocLen || 1;
  const scores = new Array<number>(index.n).fill(0);

  for (const term of queryTerms) {
    const df = index.docFreq.get(term);
    if (!df) continue;
    const idf = Math.log((index.n - df + 0.5) / (df + 0.5) + 1);

    for (let i = 0; i < index.n; i++) {
      const tf = index.termFreqs[i]!.get(term);
      if (!tf) continue;
      const docLen = index.docLen[i]!;
      const denom = tf + K1 * (1 - B + (B * docLen) / avgDocLen);
      scores[i] = (scores[i] ?? 0) + idf * ((tf * (K1 + 1)) / denom);
    }
  }

  return scores
    .map((score, i) => ({ id: index.docIds[i]!, score }))
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, k);
}
