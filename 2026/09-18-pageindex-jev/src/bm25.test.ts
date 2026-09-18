import { describe, expect, test } from "bun:test";
import { buildIndex, search, tokenize } from "./bm25";

describe("tokenize", () => {
  test("keeps dotted/snake_case/kebab-case tokens whole and adds sub-tokens", () => {
    const tokens = tokenize("Use Foo.Bar with snake_case and kebab-case options.");
    expect(tokens).toContain("foo.bar");
    expect(tokens).toContain("foo");
    expect(tokens).toContain("bar");
    expect(tokens).toContain("snake_case");
    expect(tokens).toContain("snake");
    expect(tokens).toContain("case");
    expect(tokens).toContain("kebab-case");
    expect(tokens).toContain("kebab");
  });

  test("drops common English stopwords but keeps content words", () => {
    const tokens = tokenize("the quick fox and the lazy dog");
    expect(tokens).not.toContain("the");
    expect(tokens).not.toContain("and");
    expect(tokens).toContain("quick");
    expect(tokens).toContain("fox");
    expect(tokens).toContain("lazy");
    expect(tokens).toContain("dog");
  });

  test("lowercases input", () => {
    expect(tokenize("MaxRetries")).toContain("maxretries");
  });
});

describe("buildIndex + search", () => {
  const docs = [
    { id: "a", text: "Configure the retry policy with maxRetries and backoff.foo option." },
    { id: "b", text: "Use snake_case_option to enable verbose logging output." },
    { id: "c", text: "General overview of the system architecture and design goals." },
  ];
  const index = buildIndex(docs);

  test("finds the doc containing an exact dotted identifier", () => {
    const results = search(index, "backoff.foo", 3);
    expect(results.length).toBeGreaterThan(0);
    expect(results[0]!.id).toBe("a");
  });

  test("finds a doc via a sub-token of a snake_case identifier", () => {
    const results = search(index, "verbose logging", 3);
    expect(results.length).toBeGreaterThan(0);
    expect(results[0]!.id).toBe("b");
  });

  test("respects k and ranks the best match first", () => {
    const results = search(index, "architecture design", 1);
    expect(results.length).toBe(1);
    expect(results[0]!.id).toBe("c");
  });

  test("returns an empty array when nothing matches", () => {
    const results = search(index, "nonexistent term xyz123", 3);
    expect(results).toEqual([]);
  });

  test("returns an empty array for an empty index", () => {
    const emptyIndex = buildIndex([]);
    expect(search(emptyIndex, "anything", 3)).toEqual([]);
  });
});
