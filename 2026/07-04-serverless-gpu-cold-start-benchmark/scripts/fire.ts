/**
 * Fire a single request at (provider, model) and record timings.
 *
 * Usage:
 *   pnpm fire runpod   sdxl    cold
 *   pnpm fire runpod   whisper warm
 *   pnpm fire cloudrun sdxl    warm
 *
 * mode is a label written into the jsonl (cold / warm). We do NOT wait for
 * the endpoint to actually cool down — cold-fire scheduling is the operator's
 * job (idle 15+ min before firing with mode=cold).
 *
 * Output: results/{iso}-{provider}-{model}-{mode}.jsonl
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

// LibriSpeech test-clean sample, ~30s, public domain. Hosted on HF datasets CDN.
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

async function fireRunpod(model: Model): Promise<Response> {
  const apiKey = requireEnv("RUNPOD_API_KEY");
  const endpointId = requireEnv(
    model === "sdxl" ? "RUNPOD_SDXL_ENDPOINT_ID" : "RUNPOD_WHISPER_ENDPOINT_ID",
  );
  const url = `https://api.runpod.ai/v2/${endpointId}/runsync`;
  const input = model === "sdxl" ? SDXL_PAYLOAD : WHISPER_PAYLOAD;
  return fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ input }),
  });
}

async function fireCloudrun(model: Model): Promise<Response> {
  const url = requireEnv(
    model === "sdxl" ? "CLOUDRUN_SDXL_URL" : "CLOUDRUN_WHISPER_URL",
  );
  const payload = model === "sdxl" ? SDXL_PAYLOAD : WHISPER_PAYLOAD;
  // If service is deployed with --allow-unauthenticated, no auth needed.
  // Otherwise attach an identity token.
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (process.env.CLOUDRUN_USE_IDENTITY_TOKEN === "1") {
    const token = execFileSync("gcloud", ["auth", "print-identity-token"]).toString().trim();
    headers["Authorization"] = `Bearer ${token}`;
  }
  return fetch(`${url}/infer`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
}

async function main() {
  const [providerArg, modelArg, modeArg] = process.argv.slice(2);
  if (!providerArg || !modelArg || !modeArg) {
    console.error("usage: fire <runpod|cloudrun> <sdxl|whisper> <cold|warm>");
    process.exit(1);
  }
  const provider = providerArg as Provider;
  const model = modelArg as Model;
  const mode = modeArg as Mode;

  const fireStartEpoch = Date.now();
  const fireStartHrtime = process.hrtime.bigint();
  console.log(
    `[fire] provider=${provider} model=${model} mode=${mode} start=${new Date(fireStartEpoch).toISOString()}`,
  );

  let response: Response;
  try {
    response = await (provider === "runpod" ? fireRunpod(model) : fireCloudrun(model));
  } catch (err) {
    console.error("[fire] transport error", err);
    process.exit(2);
  }

  const firstByteEpoch = Date.now();
  const firstByteHrtime = process.hrtime.bigint();
  const status = response.status;
  const bodyText = await response.text();
  const doneEpoch = Date.now();
  const doneHrtime = process.hrtime.bigint();

  let body: unknown;
  try {
    body = JSON.parse(bodyText);
  } catch {
    body = bodyText;
  }

  const record = {
    provider,
    model,
    mode,
    fire_start_epoch_ms: fireStartEpoch,
    first_byte_epoch_ms: firstByteEpoch,
    done_epoch_ms: doneEpoch,
    wall_seconds: {
      fire_to_first_byte: Number(firstByteHrtime - fireStartHrtime) / 1e9,
      fire_to_done: Number(doneHrtime - fireStartHrtime) / 1e9,
    },
    http_status: status,
    response: body,
  };

  const iso = new Date(fireStartEpoch).toISOString().replace(/[:.]/g, "-");
  const filename = `${iso}-${provider}-${model}-${mode}.jsonl`;
  const outPath = path.join(RESULTS_DIR, filename);
  fs.writeFileSync(outPath, JSON.stringify(record) + "\n");
  console.log(
    `[fire] done status=${status} wall=${record.wall_seconds.fire_to_done.toFixed(2)}s → ${outPath}`,
  );

  // Print phase breakdown if the server returned it.
  // Note: RunPod wraps output under `.output`, Cloud Run returns it at the top level.
  const inner =
    provider === "runpod" && body && typeof body === "object" && "output" in body
      ? (body as { output: unknown }).output
      : body;
  if (
    inner &&
    typeof inner === "object" &&
    "phase_seconds" in inner &&
    typeof (inner as { phase_seconds: unknown }).phase_seconds === "object"
  ) {
    const phases = (inner as { phase_seconds: Record<string, number> }).phase_seconds;
    console.log("[fire] server phase_seconds:");
    for (const [k, v] of Object.entries(phases)) {
      console.log(`         ${k.padEnd(35)} ${v.toFixed(3)}s`);
    }
    const containerInit =
      record.wall_seconds.fire_to_done -
      (phases.python_start_to_return ?? phases.python_start_to_warmup_done ?? 0);
    console.log(
      `[fire] derived container_init                 ${containerInit.toFixed(3)}s (wall - python_start_to_return)`,
    );
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
