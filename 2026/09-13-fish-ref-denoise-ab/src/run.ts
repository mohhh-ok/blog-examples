// Fish TTS 生成 → 無音圧縮 (trim) → whisper-1 書き起こし → 指標計算、を全セルについて回す。
// ループ順: rep -> ref -> script -> cond。Fish 呼び出しは並列 2、trim+whisper+指標の後段は並列 4。
// 詳細は README の「手法」節参照。
import { mkdir, readFile, appendFile } from "node:fs/promises";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import {
  computeTtsContentCheckMetrics,
  isCollapse,
  isNg,
  resolveActLineContentCheckThreshold,
} from "./lib/metrics";
import { computeTtsOutputUpperBoundSec, isOverflow } from "./lib/estimate";
import { synthesizeSpeech } from "./lib/fish";
import { buildTranscriptionPrompt, transcribeAudio } from "./lib/whisper";
import { getWavDurationSec } from "./lib/ffmpeg";
import { trimExcessSilence } from "./lib/trim";

const OUT_DIR = process.env.OUT_DIR ?? "./output";
const REPS = Number(process.env.REPS ?? "20");
const CONDITIONS = ["N", "D", "R"] as const;
type Cond = (typeof CONDITIONS)[number];

const FISH_CONCURRENCY = 2;
const WHISPER_CONCURRENCY = 4;

// 自作の p-limit 相当 (依存追加を避けるための最小実装)。
function createLimiter(concurrency: number) {
  let active = 0;
  const queue: Array<() => void> = [];
  const next = () => {
    active--;
    const job = queue.shift();
    if (job) job();
  };
  return function limit<T>(fn: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      const run = () => {
        active++;
        fn()
          .then((value) => {
            next();
            resolve(value);
          })
          .catch((error) => {
            next();
            reject(error);
          });
      };
      if (active < concurrency) {
        run();
      } else {
        queue.push(run);
      }
    });
  };
}

type ResultRecord = {
  rep: number;
  ref: string;
  speaker: string;
  variant: string;
  script: "short" | "long";
  cond: Cond;
  text: string | null;
  rawDurationSec: number | null;
  actualDurationSec: number | null;
  upperBoundSec: number | null;
  overflow: boolean | null;
  asrText: string | null;
  lcsRatio: number | null;
  threshold: number | null;
  ng: boolean | null;
  collapse: boolean | null;
  scriptChars: number | null;
  asrChars: number | null;
  fishMs: number | null;
  whisperMs: number | null;
  fishAttempts: number | null;
  error: string | null;
  startedAt: string;
};

type Manifest = Record<
  string,
  { speaker: string; variant: string; [key: string]: unknown }
>;

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} env is required`);
  return value;
}

function loadScript(filePath: string): string {
  const raw = readFileSync(filePath, "utf-8");
  return raw.replace(/\n+$/, "");
}

async function loadExistingKeys(resultsPath: string): Promise<Set<string>> {
  const keys = new Set<string>();
  if (!existsSync(resultsPath)) return keys;
  const content = await readFile(resultsPath, "utf-8");
  for (const line of content.split("\n")) {
    if (!line.trim()) continue;
    try {
      const record = JSON.parse(line) as ResultRecord;
      keys.add(`${record.ref}|${record.script}|${record.cond}|${record.rep}`);
    } catch {
      // 壊れた行は無視 (resume の判定に使わないだけで、ファイル自体は書き換えない)
    }
  }
  return keys;
}

async function main(): Promise<void> {
  const fishApiKey = requireEnv("FISH_API_KEY");
  const openaiApiKey = requireEnv("OPENAI_API_KEY");
  const scriptShortPath = requireEnv("SCRIPT_SHORT_PATH");
  const scriptLongPath = requireEnv("SCRIPT_LONG_PATH");

  const manifestPath = path.join(OUT_DIR, "refs", "manifest.json");
  const manifest = JSON.parse(await readFile(manifestPath, "utf-8")) as Manifest;

  const refsFilter = process.env.REFS_FILTER
    ? process.env.REFS_FILTER.split(",").map((s) => s.trim())
    : undefined;
  const allRefs = Object.keys(manifest);
  const refs = refsFilter ? allRefs.filter((r) => refsFilter.includes(r)) : allRefs;
  if (refs.length === 0) {
    throw new Error(`run: no refs matched (REFS_FILTER=${process.env.REFS_FILTER ?? "<unset>"})`);
  }

  const scripts: Array<{ label: "short" | "long"; text: string }> = [
    { label: "short", text: loadScript(scriptShortPath) },
    { label: "long", text: loadScript(scriptLongPath) },
  ];

  const runsDir = path.join(OUT_DIR, "runs");
  const resultsPath = path.join(OUT_DIR, "results.jsonl");
  await mkdir(runsDir, { recursive: true });

  const existingKeys = await loadExistingKeys(resultsPath);

  const fishLimit = createLimiter(FISH_CONCURRENCY);
  const whisperLimit = createLimiter(WHISPER_CONCURRENCY);

  const pending: Promise<void>[] = [];
  let totalCells = 0;
  let skippedCells = 0;

  for (let rep = 1; rep <= REPS; rep++) {
    for (const ref of refs) {
      const { speaker, variant } = manifest[ref]!;
      for (const script of scripts) {
        for (const cond of CONDITIONS) {
          totalCells++;
          const key = `${ref}|${script.label}|${cond}|${rep}`;
          if (existingKeys.has(key)) {
            skippedCells++;
            continue;
          }

          const cellDir = path.join(runsDir, ref, script.label, cond);
          const refWavPath = path.join(OUT_DIR, "refs", ref, `${cond}.wav`);

          const job = fishLimit(async () => {
            await mkdir(cellDir, { recursive: true });
            const startedAt = new Date().toISOString();
            let record: ResultRecord = {
              rep,
              ref,
              speaker,
              variant,
              script: script.label,
              cond,
              text: script.text,
              rawDurationSec: null,
              actualDurationSec: null,
              upperBoundSec: null,
              overflow: null,
              asrText: null,
              lcsRatio: null,
              threshold: null,
              ng: null,
              collapse: null,
              scriptChars: null,
              asrChars: null,
              fishMs: null,
              whisperMs: null,
              fishAttempts: null,
              error: null,
              startedAt,
            };

            try {
              const referenceAudio = new Uint8Array(await readFile(refWavPath));
              const { audio, attempts, fishMs } = await synthesizeSpeech({
                text: script.text,
                referenceAudio,
                apiKey: fishApiKey,
              });
              const rawPath = path.join(cellDir, `${rep}.raw.wav`);
              await Bun.write(rawPath, audio);
              record.fishAttempts = attempts;
              record.fishMs = fishMs;
              return { record, rawPath };
            } catch (error) {
              record.error = error instanceof Error ? error.message : String(error);
              return { record, rawPath: null };
            }
          });

          const postJob = job.then(({ record, rawPath }) =>
            whisperLimit(async () => {
              if (rawPath) {
                try {
                  const rawDurationSec = await getWavDurationSec(rawPath);
                  record.rawDurationSec = rawDurationSec;

                  const trimPath = path.join(cellDir, `${rep}.trim.wav`);
                  await trimExcessSilence({ inputPath: rawPath, outputPath: trimPath });
                  const actualDurationSec = await getWavDurationSec(trimPath);
                  record.actualDurationSec = actualDurationSec;

                  const upperBoundSec = computeTtsOutputUpperBoundSec(record.text!);
                  record.upperBoundSec = upperBoundSec;
                  record.overflow = isOverflow({ actualDurationSec, text: record.text! });

                  const prompt = buildTranscriptionPrompt(record.text!);
                  const { text: asrText, whisperMs } = await transcribeAudio({
                    filePath: trimPath,
                    prompt,
                    apiKey: openaiApiKey,
                  });
                  record.asrText = asrText;
                  record.whisperMs = whisperMs;

                  const metrics = computeTtsContentCheckMetrics({ asrText, script: record.text! });
                  record.lcsRatio = metrics.lcsRatio;
                  record.scriptChars = metrics.scriptChars;
                  record.asrChars = metrics.asrChars;
                  const threshold = resolveActLineContentCheckThreshold(metrics.scriptChars);
                  record.threshold = threshold;
                  record.ng = isNg(metrics.lcsRatio, threshold);
                  record.collapse = isCollapse(metrics.lcsRatio);
                } catch (error) {
                  record.error = error instanceof Error ? error.message : String(error);
                }
              }
              await appendFile(resultsPath, JSON.stringify(record) + "\n", "utf-8");
              console.log(
                `[run] rep=${record.rep} ref=${record.ref} script=${record.script} cond=${record.cond} ` +
                  `ng=${record.ng} collapse=${record.collapse} overflow=${record.overflow} error=${record.error ?? "-"}`,
              );
            }),
          );
          pending.push(postJob);
        }
      }
    }
  }

  await Promise.all(pending);
  console.log(`[run] done. total=${totalCells} skipped(resume)=${skippedCells} ran=${totalCells - skippedCells}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
