/**
 * Read all results/*.jsonl and print a summary table + RESULTS.md-friendly
 * markdown to stdout.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const RESULTS_DIR = path.join(ROOT, "results");

type FireRecord = {
  provider: "runpod" | "cloudrun";
  model: "sdxl" | "whisper";
  mode: "cold" | "warm" | "seed";
  fire_start_epoch_ms: number;
  wall_seconds: { fire_to_first_byte?: number; fire_to_done: number };
  http_status: number;
  response: unknown;
};

function loadAll(): FireRecord[] {
  const files = fs
    .readdirSync(RESULTS_DIR)
    .filter((f) => f.endsWith(".jsonl"))
    .sort();
  const out: FireRecord[] = [];
  for (const f of files) {
    const raw = fs.readFileSync(path.join(RESULTS_DIR, f), "utf8");
    for (const line of raw.split("\n").filter(Boolean)) {
      try {
        out.push(JSON.parse(line));
      } catch (e) {
        console.error(`skipped bad line in ${f}:`, e);
      }
    }
  }
  return out;
}

function phaseOf(rec: FireRecord): Record<string, number> | undefined {
  const b = rec.response;
  const inner =
    rec.provider === "runpod" && b && typeof b === "object" && "output" in b
      ? (b as { output: unknown }).output
      : b;
  if (
    inner &&
    typeof inner === "object" &&
    "phase_seconds" in inner &&
    typeof (inner as { phase_seconds: unknown }).phase_seconds === "object"
  ) {
    return (inner as { phase_seconds: Record<string, number> }).phase_seconds;
  }
  return undefined;
}

function main() {
  const records = loadAll();
  if (records.length === 0) {
    console.log("no results yet");
    return;
  }

  console.log("## Raw fires\n");
  console.log("| when | provider | model | mode | http | wall (s) |");
  console.log("|---|---|---|---|---|---|");
  for (const r of records) {
    const iso = new Date(r.fire_start_epoch_ms).toISOString();
    console.log(
      `| ${iso} | ${r.provider} | ${r.model} | ${r.mode} | ${r.http_status} | ${r.wall_seconds.fire_to_done.toFixed(2)} |`,
    );
  }

  console.log("\n## Phase breakdown (cold + seed only)\n");
  const cold = records.filter((r) => (r.mode === "cold" || r.mode === "seed") && r.http_status === 200);
  if (cold.length === 0) {
    console.log("_no successful cold fires_");
    return;
  }
  const phaseKeys = [
    "python_start_to_import_done",
    "python_start_to_weights_loaded",
    "python_start_to_warmup_done",
    "inference_only",
    "python_start_to_return",
  ];
  const derivedKey = "container_init_derived";
  const header = ["when", "provider/model/mode", ...phaseKeys, derivedKey, "wall_total"];
  console.log(`| ${header.join(" | ")} |`);
  console.log(`| ${header.map(() => "---").join(" | ")} |`);
  for (const r of cold) {
    const p = phaseOf(r) ?? {};
    const iso = new Date(r.fire_start_epoch_ms).toISOString().substring(11, 19);
    const row: (string | number)[] = [iso, `${r.provider}/${r.model}/${r.mode}`];
    for (const k of phaseKeys) row.push(p[k]?.toFixed(3) ?? "-");
    const container = r.wall_seconds.fire_to_done - (p.python_start_to_return ?? 0);
    row.push(container.toFixed(3));
    row.push(r.wall_seconds.fire_to_done.toFixed(3));
    console.log(`| ${row.join(" | ")} |`);
  }
}

main();
