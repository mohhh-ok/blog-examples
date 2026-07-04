/**
 * Fire the full 12-fire benchmark matrix in one command.
 *
 * Layout:
 *   provider × model = 4 endpoints (runpod/sdxl, runpod/whisper, cloudrun/sdxl, cloudrun/whisper)
 *   each endpoint gets: cold, warm, warm (in that order, no idle between them)
 *   endpoints fire in PARALLEL — each is independent, no shared resources
 *
 * PRECONDITION: All 4 endpoints must be truly cold at start.
 *   - RunPod: idle timeout is 5s so this is easy — just wait 30s before running.
 *   - Cloud Run: scale-to-zero is ~15 min. Wait 20+ min after any previous fire.
 * The script does NOT enforce this; the operator is responsible.
 *
 * Output: results/<iso>-batch-<provider>-<model>-<mode>.jsonl (one per fire)
 */

import { config } from "dotenv";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
config({ path: path.join(ROOT, ".env") });

const RESULTS_DIR = path.join(ROOT, "results");
fs.mkdirSync(RESULTS_DIR, { recursive: true });

type Provider = "runpod" | "cloudrun";
type Model = "sdxl" | "whisper";
type Mode = "cold" | "warm";

const SDXL_PAYLOAD = {
  prompt: "A photo of an astronaut riding a horse",
  steps: 25,
  width: 1024,
  height: 1024,
} as const;

const WHISPER_PAYLOAD = {
  audio_url:
    "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/1.flac",
  language: "en",
  beam_size: 5,
} as const;

function requireEnv(key: string): string {
  const v = process.env[key];
  if (!v) throw new Error(`env ${key} is required`);
  return v;
}

async function fetchRunpod(model: Model): Promise<{ body: unknown; status: number }> {
  // Use /run (async submit) + /status/{id} poll so requests longer than the
  // /runsync 90s cap (SDXL cold) don't get cut off.
  const apiKey = requireEnv("RUNPOD_API_KEY");
  const endpointId = requireEnv(
    model === "sdxl" ? "RUNPOD_SDXL_ENDPOINT_ID" : "RUNPOD_WHISPER_ENDPOINT_ID",
  );
  const input = model === "sdxl" ? SDXL_PAYLOAD : WHISPER_PAYLOAD;
  const submit = await fetch(`https://api.runpod.ai/v2/${endpointId}/run`, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({ input }),
  });
  if (!submit.ok) {
    return { body: await submit.text(), status: submit.status };
  }
  const { id } = (await submit.json()) as { id: string };
  const deadline = Date.now() + 15 * 60 * 1000;
  while (Date.now() < deadline) {
    const st = await fetch(`https://api.runpod.ai/v2/${endpointId}/status/${id}`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    const j = (await st.json()) as { status: string; output?: unknown; error?: unknown };
    if (j.status === "COMPLETED" || j.status === "FAILED" || j.status === "CANCELLED" || j.status === "TIMED_OUT") {
      return { body: j, status: st.status };
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  return { body: { error: "poll_timeout" }, status: 504 };
}

async function fetchCloudrun(model: Model): Promise<{ body: unknown; status: number }> {
  const url = requireEnv(
    model === "sdxl" ? "CLOUDRUN_SDXL_URL" : "CLOUDRUN_WHISPER_URL",
  );
  const payload = model === "sdxl" ? SDXL_PAYLOAD : WHISPER_PAYLOAD;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (process.env.CLOUDRUN_USE_IDENTITY_TOKEN === "1") {
    const token = execFileSync("gcloud", ["auth", "print-identity-token"]).toString().trim();
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${url}/infer`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  const text = await res.text();
  let body: unknown = text;
  try {
    body = JSON.parse(text);
  } catch {
    /* leave as text */
  }
  return { body, status: res.status };
}

async function fireOnce(provider: Provider, model: Model, mode: Mode) {
  const fireStartEpoch = Date.now();
  const fireStartHrtime = process.hrtime.bigint();
  const label = `${provider}/${model}/${mode}`;
  console.log(`[${label}] start ${new Date(fireStartEpoch).toISOString()}`);
  let result: { body: unknown; status: number };
  try {
    result = await (provider === "runpod" ? fetchRunpod(model) : fetchCloudrun(model));
  } catch (err) {
    console.error(`[${label}] transport error`, err);
    return null;
  }
  const doneHrtime = process.hrtime.bigint();
  const rec = {
    provider,
    model,
    mode,
    fire_start_epoch_ms: fireStartEpoch,
    wall_seconds: {
      fire_to_done: Number(doneHrtime - fireStartHrtime) / 1e9,
    },
    http_status: result.status,
    response: result.body,
  };
  const iso = new Date(fireStartEpoch).toISOString().replace(/[:.]/g, "-");
  const outPath = path.join(RESULTS_DIR, `${iso}-batch-${provider}-${model}-${mode}.jsonl`);
  fs.writeFileSync(outPath, JSON.stringify(rec) + "\n");
  console.log(
    `[${label}] done status=${result.status} wall=${rec.wall_seconds.fire_to_done.toFixed(2)}s`,
  );
  return rec;
}

async function fireChain(provider: Provider, model: Model) {
  // Sequential cold → warm1 → warm2 for one endpoint. warm always fires
  // immediately after cold's response so the worker stays hot.
  const cold = await fireOnce(provider, model, "cold");
  const warm1 = await fireOnce(provider, model, "warm");
  const warm2 = await fireOnce(provider, model, "warm");
  return [cold, warm1, warm2];
}

async function main() {
  const targets: Array<[Provider, Model]> = [
    ["runpod", "sdxl"],
    ["runpod", "whisper"],
    ["cloudrun", "sdxl"],
    ["cloudrun", "whisper"],
  ];

  console.log("== 4 endpoints, each runs cold → warm → warm sequentially, chains in parallel ==");
  const results = await Promise.all(targets.map(([p, m]) => fireChain(p, m)));
  const all = results.flat().filter(Boolean);
  console.log(`\n[fire-all] wrote ${all.length} records`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
