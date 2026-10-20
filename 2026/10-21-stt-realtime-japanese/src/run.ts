// リアルタイムの文字起こしの API に録音を実時間の速さで流し、確定した文と届いた時刻を jsonl に書く。
// 使い方は README.md。1 本ずつ順に流す (同時に流さない)。途中で止めても、書き終えた id は次の実行で飛ばす。
import { appendFileSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { parseArgs } from "node:util";
import { decodeAudio } from "./audio.ts";
import { readManifest } from "./manifest.ts";
import { createElevenLabsProvider } from "./providers/elevenlabs.ts";
import { createSonioxProvider, SONIOX_PLUGIN_MAX_ENDPOINT_DELAY_MS } from "./providers/soniox.ts";
import type { Provider } from "./providers/types.ts";

const HINT_MODES = ["none", "terms"] as const;
type HintMode = (typeof HINT_MODES)[number];

const { values } = parseArgs({
  options: {
    manifest: { type: "string" },
    "audio-dir": { type: "string" },
    language: { type: "string" },
    provider: { type: "string" },
    hints: { type: "string", default: "none" },
    "out-dir": { type: "string" },
    limit: { type: "string" },
    // Soniox の max_endpoint_delay_ms (500〜3000)。既定は LiveKit のプラグインの既定。
    "soniox-max-endpoint-delay-ms": { type: "string", default: String(SONIOX_PLUGIN_MAX_ENDPOINT_DELAY_MS) },
  },
});

const manifestPath = required(values.manifest, "--manifest");
const language = required(values.language, "--language");
const outDir = required(values["out-dir"], "--out-dir");
const hints = parseHintMode(values.hints);
const provider = createProvider(required(values.provider, "--provider"));
const limit = values.limit === undefined ? undefined : Number(values.limit);

const items = readManifest({ path: manifestPath, audioDir: values["audio-dir"] }).slice(0, limit);
mkdirSync(outDir, { recursive: true });
const outPath = join(outDir, `${provider.name}-${hints}.jsonl`);
const doneIds = readDoneIds(outPath);

console.log(`${provider.name} hints=${hints} language=${language} items=${items.length} done=${doneIds.size} -> ${outPath}`);
console.log(`settings ${JSON.stringify(provider.describeSettings({ language, hasTerms: hints === "terms" }))}`);

for (const item of items) {
  if (doneIds.has(item.id)) continue;
  const audio = await decodeAudio(item.audioPath);
  const terms = hints === "terms" && item.terms.length > 0 ? item.terms : undefined;
  const startedAt = new Date().toISOString();
  const result = await provider.transcribe({ pcm: audio.pcm, language, terms });
  const record = {
    id: item.id,
    provider: provider.name,
    hints,
    language,
    startedAt,
    durationMs: Math.round(audio.durationMs),
    segments: result.segments.map((segment) => ({ ...segment, receivedAtMs: Math.round(segment.receivedAtMs) })),
    error: result.error,
  };
  appendFileSync(outPath, `${JSON.stringify(record)}\n`);
  console.log(`${item.id} segments=${result.segments.length}${result.error === null ? "" : ` error=${result.error}`}`);
}

function createProvider(name: string): Provider {
  if (name === "elevenlabs") return createElevenLabsProvider({ apiKey: requiredEnv("ELEVENLABS_API_KEY") });
  if (name === "soniox") {
    return createSonioxProvider({ apiKey: requiredEnv("SONIOX_API_KEY"), maxEndpointDelayMs: Number(values["soniox-max-endpoint-delay-ms"]) });
  }
  throw new Error(`unknown --provider ${name} (elevenlabs | soniox)`);
}

function parseHintMode(value: string | undefined): HintMode {
  const mode = HINT_MODES.find((candidate) => candidate === value);
  if (mode === undefined) throw new Error(`--hints must be one of ${HINT_MODES.join(", ")}`);
  return mode;
}

function readDoneIds(path: string): Set<string> {
  if (!existsSync(path)) return new Set();
  const lines = readFileSync(path, "utf8").split("\n").filter((line) => line !== "");
  return new Set(lines.map((line) => (JSON.parse(line) as { id: string }).id));
}

function required(value: string | undefined, name: string): string {
  if (value === undefined || value === "") throw new Error(`${name} is required`);
  return value;
}

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (value === undefined || value === "") throw new Error(`${name} is not set`);
  return value;
}
