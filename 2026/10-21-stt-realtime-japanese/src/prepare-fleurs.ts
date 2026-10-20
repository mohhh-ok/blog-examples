// FLEURS (google/fleurs、CC BY 4.0) の 1 言語の split から、文の重ならない N 本を固定の seed で選び、計測の一覧 (tsv) を書く。
// 入力は Hugging Face の data/<config>/<split>.tsv と、audio/<split>.tar.gz を展開したディレクトリ。使い方は README.md。
// FLEURS の tsv の列: 文の id・音声のファイル名・raw_transcription・transcription・文字の分かち書き・サンプル数・話者の性別。
import { readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { parseArgs } from "node:util";

const { values } = parseArgs({
  options: {
    tsv: { type: "string" },
    "audio-dir": { type: "string" },
    count: { type: "string" },
    seed: { type: "string", default: "1" },
    out: { type: "string" },
  },
});
if (values.tsv === undefined || values["audio-dir"] === undefined || values.count === undefined || values.out === undefined) {
  throw new Error("usage: prepare-fleurs.ts --tsv <split.tsv> --audio-dir <dir> --count <n> [--seed <n>] --out <manifest.tsv>");
}
const audioDir = resolve(values["audio-dir"]);

// 同じ文を別の話者が読んだ行があるので、文の id ごとにファイル名の小さい 1 本を残す。
const bySentence = new Map<string, { file: string; text: string }>();
for (const line of readFileSync(values.tsv, "utf8").split("\n")) {
  const [sentenceId, file, rawTranscription] = line.split("\t");
  if (sentenceId === undefined || file === undefined || rawTranscription === undefined || sentenceId === "") continue;
  const current = bySentence.get(sentenceId);
  if (current === undefined || file < current.file) bySentence.set(sentenceId, { file, text: rawTranscription });
}

const sentenceIds = [...bySentence.keys()].sort();
const random = mulberry32(Number(values.seed));
for (let index = sentenceIds.length - 1; index > 0; index--) {
  const swap = Math.floor(random() * (index + 1));
  [sentenceIds[index], sentenceIds[swap]] = [sentenceIds[swap] ?? "", sentenceIds[index] ?? ""];
}
const selected = sentenceIds.slice(0, Number(values.count)).sort();

const rows = selected.map((sentenceId) => {
  const entry = bySentence.get(sentenceId);
  if (entry === undefined) throw new Error(`missing ${sentenceId}`);
  return [sentenceId, entry.text, "", join(audioDir, entry.file)].join("\t");
});
writeFileSync(values.out, ["id\ttext\tterms\taudio", ...rows].join("\n") + "\n");
console.log(`${selected.length} / ${bySentence.size} sentences -> ${values.out}`);

// 小さな seed 付きの乱数 (再現のため。Math.random は seed を指定できない)。
function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}
