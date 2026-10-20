// run.ts の jsonl を採点する。1 本ごとの表 (items.tsv) と、プロバイダ × ヒントごとの集計 (summary.md) を書く。
// 使い方は README.md。
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { parseArgs } from "node:util";
import { decodeAudio } from "./audio.ts";
import { readManifest } from "./manifest.ts";
import { editDistance, normalizeText, splitGraphemes } from "./normalize.ts";
import type { FinalSegment } from "./providers/types.ts";

type RunRecord = {
  id: string;
  provider: string;
  hints: string;
  language: string;
  durationMs: number;
  segments: FinalSegment[];
  error: string | null;
};

type ScoredItem = {
  record: RunRecord;
  // 音声から求めた話し終わりの時刻 (audio.ts)。声と雑音を分けられない音声は null。
  speechEndMs: number | null;
  reference: string;
  hypothesis: string;
  edits: number;
  referenceLength: number;
  termsTotal: number;
  termsCorrect: number;
  missedTerms: string[];
  // 話し終わりから、最後の確定が届くまで。最後の確定が終わりの明示の後に届いたとき・話し終わりを決められないときは null。
  endpointLatencyMs: number | null;
};

const { values, positionals } = parseArgs({
  options: {
    manifest: { type: "string" },
    "audio-dir": { type: "string" },
    "out-dir": { type: "string" },
  },
  allowPositionals: true,
});
if (values.manifest === undefined || values["out-dir"] === undefined || positionals.length === 0) {
  throw new Error("usage: score.ts --manifest <tsv> --out-dir <dir> <results.jsonl>...");
}
const manifest = new Map(readManifest({ path: values.manifest, audioDir: values["audio-dir"] ?? "" }).map((item) => [item.id, item]));
const records = positionals.flatMap((path) =>
  readFileSync(path, "utf8").split("\n").filter((line) => line !== "").map((line) => JSON.parse(line) as RunRecord),
);
// 話し終わりは採点のたびに音声から求める (判定の決まりを直しても API を流し直さずに済むように)。
const speechEnds = new Map<string, number | null>();
for (const item of manifest.values()) speechEnds.set(item.id, (await decodeAudio(item.audioPath)).speechEndMs);
const scored = records.map(scoreRecord);

writeFileSync(join(values["out-dir"], "items.tsv"), renderItems(scored));
writeFileSync(join(values["out-dir"], "summary.md"), renderSummary(scored));
console.log(renderSummary(scored));

function scoreRecord(record: RunRecord): ScoredItem {
  const item = manifest.get(record.id);
  if (item === undefined) throw new Error(`${record.id} is not in the manifest`);
  const hypothesis = record.segments.map((segment) => segment.text).join("");
  const referenceNormalized = normalizeText(item.text, record.language);
  const hypothesisNormalized = normalizeText(hypothesis, record.language);
  const referenceGraphemes = splitGraphemes(referenceNormalized, record.language);
  const missedTerms = item.terms.filter((term) => !hypothesisNormalized.includes(normalizeText(term, record.language)));
  const last = record.segments.at(-1);
  const speechEndMs = speechEnds.get(record.id) ?? null;
  return {
    record,
    speechEndMs,
    reference: item.text,
    hypothesis,
    edits: editDistance(referenceGraphemes, splitGraphemes(hypothesisNormalized, record.language)),
    referenceLength: referenceGraphemes.length,
    termsTotal: item.terms.length,
    termsCorrect: item.terms.length - missedTerms.length,
    missedTerms,
    endpointLatencyMs: last === undefined || last.isForced || speechEndMs === null ? null : last.receivedAtMs - speechEndMs,
  };
}

function renderItems(items: ScoredItem[]): string {
  const header = ["id", "provider", "hints", "cer", "edits", "ref_chars", "terms_correct", "terms_total", "missed_terms", "segments", "speech_end_ms", "endpoint_latency_ms", "forced", "error", "reference", "hypothesis"];
  const rows = items.map((item) => [
    item.record.id,
    item.record.provider,
    item.record.hints,
    (item.edits / item.referenceLength).toFixed(4),
    item.edits,
    item.referenceLength,
    item.termsCorrect,
    item.termsTotal,
    item.missedTerms.join(";"),
    item.record.segments.length,
    item.speechEndMs ?? "",
    item.endpointLatencyMs === null ? "" : Math.round(item.endpointLatencyMs),
    item.record.segments.some((segment) => segment.isForced) ? 1 : 0,
    item.record.error ?? "",
    item.reference,
    item.record.segments.map((segment) => segment.text).join(" | "),
  ]);
  return [header, ...rows].map((row) => row.join("\t")).join("\n") + "\n";
}

function renderSummary(items: ScoredItem[]): string {
  const groups = new Map<string, ScoredItem[]>();
  for (const item of items) {
    const key = `${item.record.provider}\t${item.record.hints}`;
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }
  const lines = [
    "| provider | hints | 本数 | CER (合計) | CER (平均) | 固有名詞 | 2 つ以上に分かれた本数 | 遅延を測れた本数 | 話し終わり→確定 中央値 ms | 同 p90 ms | 自分で区切らなかった本数 | エラー |",
    "|---|---|---|---|---|---|---|---|---|---|---|---|",
  ];
  for (const [key, group] of groups) {
    const [provider, hints] = key.split("\t");
    const edits = sum(group.map((item) => item.edits));
    const referenceLength = sum(group.map((item) => item.referenceLength));
    const termsTotal = sum(group.map((item) => item.termsTotal));
    const termsCorrect = sum(group.map((item) => item.termsCorrect));
    const latencies = group.flatMap((item) => (item.endpointLatencyMs === null ? [] : [item.endpointLatencyMs])).sort((a, b) => a - b);
    lines.push(
      [
        provider,
        hints,
        group.length,
        percent(edits / referenceLength),
        percent(mean(group.map((item) => item.edits / item.referenceLength))),
        termsTotal === 0 ? "-" : `${termsCorrect}/${termsTotal} (${percent(termsCorrect / termsTotal)})`,
        group.filter((item) => item.record.segments.length > 1).length,
        latencies.length,
        latencies.length === 0 ? "-" : Math.round(quantile(latencies, 0.5)),
        latencies.length === 0 ? "-" : Math.round(quantile(latencies, 0.9)),
        group.filter((item) => item.record.segments.some((segment) => segment.isForced)).length,
        group.filter((item) => item.record.error !== null).length,
      ].join(" | ").replace(/^/, "| ").replace(/$/, " |"),
    );
  }
  return lines.join("\n") + "\n";
}

function sum(values: number[]): number {
  return values.reduce((total, value) => total + value, 0);
}

function mean(values: number[]): number {
  return sum(values) / values.length;
}

// 線形補間の分位点。values は昇順。
function quantile(values: number[], q: number): number {
  const position = (values.length - 1) * q;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  return (values[lower] ?? 0) + ((values[upper] ?? 0) - (values[lower] ?? 0)) * (position - lower);
}

function percent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
