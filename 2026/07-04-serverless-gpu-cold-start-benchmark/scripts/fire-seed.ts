/**
 * Seed fire: fire once on each RunPod endpoint to trigger the volume-seed
 * download inside the worker. Records results as mode="seed" for later
 * distinction from actual cold-start measurements. Both endpoints fire in
 * parallel because they share the same network volume in US-IL-1 but load
 * different weight subdirs.
 */

import { config } from "dotenv";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
config({ path: path.join(ROOT, ".env") });

const RESULTS_DIR = path.join(ROOT, "results");
fs.mkdirSync(RESULTS_DIR, { recursive: true });

type Model = "sdxl" | "whisper";

const SDXL_PAYLOAD = {
  prompt: "A photo of an astronaut riding a horse",
  steps: 25,
  width: 1024,
  height: 1024,
} as const;

const WHISPER_PAYLOAD = {
  audio_url: "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/1.flac",
  language: "en",
  beam_size: 5,
} as const;

function requireEnv(key: string): string {
  const v = process.env[key];
  if (!v) throw new Error(`env ${key} required`);
  return v;
}

async function seed(model: Model) {
  const apiKey = requireEnv("RUNPOD_API_KEY");
  const endpointId = requireEnv(
    model === "sdxl" ? "RUNPOD_SDXL_ENDPOINT_ID" : "RUNPOD_WHISPER_ENDPOINT_ID",
  );
  const input = model === "sdxl" ? SDXL_PAYLOAD : WHISPER_PAYLOAD;
  const fireStartEpoch = Date.now();
  const fireStartHrtime = process.hrtime.bigint();
  console.log(`[seed/${model}] start ${new Date(fireStartEpoch).toISOString()}`);
  const submit = await fetch(`https://api.runpod.ai/v2/${endpointId}/run`, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({ input }),
  });
  const { id } = (await submit.json()) as { id: string };
  console.log(`[seed/${model}] queued jobId=${id}`);
  const deadline = Date.now() + 30 * 60 * 1000;
  let body: unknown = null;
  let status = 0;
  while (Date.now() < deadline) {
    const st = await fetch(`https://api.runpod.ai/v2/${endpointId}/status/${id}`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    status = st.status;
    body = await st.json();
    const s = (body as { status?: string }).status;
    if (s && ["COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"].includes(s)) break;
    await new Promise((r) => setTimeout(r, 2000));
  }
  const doneHrtime = process.hrtime.bigint();
  const rec = {
    provider: "runpod",
    model,
    mode: "seed",
    fire_start_epoch_ms: fireStartEpoch,
    wall_seconds: { fire_to_done: Number(doneHrtime - fireStartHrtime) / 1e9 },
    http_status: status,
    response: body,
  };
  const iso = new Date(fireStartEpoch).toISOString().replace(/[:.]/g, "-");
  const p = path.join(RESULTS_DIR, `${iso}-batch-runpod-${model}-seed.jsonl`);
  fs.writeFileSync(p, JSON.stringify(rec) + "\n");
  console.log(`[seed/${model}] done status=${status} wall=${rec.wall_seconds.fire_to_done.toFixed(1)}s`);
  return rec;
}

Promise.all([seed("sdxl"), seed("whisper")]).then((r) => {
  console.log(`[seed] wrote ${r.length} records`);
});
