import { performance } from "node:perf_hooks";
import { elapsedMs, streamRealtime, type StreamClock } from "../stream.ts";
import { SAMPLE_RATE } from "../audio.ts";
import type { FinalSegment, Provider, TranscribeInput, TranscribeResult } from "./types.ts";

// LiveKit の @livekit/agents-plugin-soniox 1.9.3 の既定と同じ設定にする。model だけ現行の stt-rt-v5 を明示する
// (プラグインの既定の stt-rt-v4 は 2026-06-30 から v5 に転送されている、https://soniox.com/docs/stt/models)。
const MODEL = "stt-rt-v5";
// プラグインの既定。Soniox の API の既定は 2000 (https://soniox.com/docs/stt/rt/endpoint-detection)。
export const SONIOX_PLUGIN_MAX_ENDPOINT_DELAY_MS = 500;
const BASE_URL = "wss://stt-rt.soniox.com/transcribe-websocket";
const END_TOKEN = "<end>";
const FINALIZED_TOKEN = "<fin>";
const TRAILING_SILENCE_MS = 3000;

// maxEndpointDelayMs がプラグインの既定と違うときは、結果を分けるため name に付ける (例: soniox-d2000)。
export function createSonioxProvider(options: { apiKey: string; maxEndpointDelayMs: number }): Provider {
  const maxEndpointDelayMs = options.maxEndpointDelayMs;
  return {
    name: maxEndpointDelayMs === SONIOX_PLUGIN_MAX_ENDPOINT_DELAY_MS ? "soniox" : `soniox-d${maxEndpointDelayMs}`,
    describeSettings: ({ language, hasTerms }) => ({
      endpoint: BASE_URL,
      ...buildConfig({ language, terms: hasTerms ? ["<その文の固有名詞の一覧>"] : undefined, maxEndpointDelayMs }),
    }),
    transcribe: (input) => transcribe({ apiKey: options.apiKey, input, maxEndpointDelayMs }),
  };
}

function buildConfig(options: { language: string; terms: string[] | undefined; maxEndpointDelayMs: number }): Record<string, unknown> {
  return {
    model: MODEL,
    audio_format: "pcm_s16le",
    num_channels: 1,
    sample_rate: SAMPLE_RATE,
    enable_endpoint_detection: true,
    language_hints: [options.language],
    language_hints_strict: false,
    enable_speaker_diarization: false,
    enable_language_identification: true,
    max_endpoint_delay_ms: options.maxEndpointDelayMs,
    ...(options.terms === undefined ? {} : { context: { terms: options.terms } }),
  };
}

type SonioxToken = { text: string; is_final: boolean };
type SonioxMessage = { tokens?: SonioxToken[]; finished?: boolean; error_code?: number | string; error_message?: string };

async function transcribe(options: { apiKey: string; input: TranscribeInput; maxEndpointDelayMs: number }): Promise<TranscribeResult> {
  const { input } = options;
  const segments: FinalSegment[] = [];
  let error: string | null = null;
  let isForcing = false;
  let isClosed = false;
  let pending = "";
  const clock: StreamClock = { startedAt: 0 };

  const ws = new WebSocket(BASE_URL, { headers: { Authorization: `Bearer ${options.apiKey}` } } as unknown as string[]);
  const closed = new Promise<void>((resolve) => {
    ws.addEventListener("close", () => {
      isClosed = true;
      resolve();
    });
  });
  ws.addEventListener("message", (event) => {
    const data = JSON.parse(String(event.data)) as SonioxMessage;
    if (data.error_code !== undefined || data.error_message !== undefined) {
      error = `${data.error_code ?? ""}: ${data.error_message ?? ""}`;
      ws.close();
      return;
    }
    for (const token of data.tokens ?? []) {
      if (!token.is_final) continue;
      if (token.text === END_TOKEN || token.text === FINALIZED_TOKEN) {
        flush();
      } else {
        pending += token.text;
      }
    }
    if (data.finished) {
      flush();
      ws.close();
    }
  });
  function flush(): void {
    if (pending.trim() !== "") segments.push({ text: pending, receivedAtMs: elapsedMs(clock), isForced: isForcing });
    pending = "";
  }
  await new Promise<void>((resolve, reject) => {
    ws.addEventListener("open", () => resolve(), { once: true });
    ws.addEventListener("error", () => reject(new Error("soniox websocket error")), { once: true });
  });
  ws.send(JSON.stringify(buildConfig({ language: input.language, terms: input.terms, maxEndpointDelayMs: options.maxEndpointDelayMs })));

  clock.startedAt = performance.now();
  await streamRealtime({
    pcm: input.pcm,
    trailingSilenceMs: TRAILING_SILENCE_MS,
    clock,
    isClosed: () => isClosed,
    // 塊は送る分だけの新しい配列に写す (subarray のまま送ると、型の上で共有メモリの可能性が残る)。
    send: (chunk) => ws.send(new Uint8Array(chunk)),
  });
  if (!isClosed) {
    // 空の文字列 (テキストのフレーム) で音声の終わりを伝える。サーバーは残りを確定して finished を返す。
    // 空のバイナリは空の音声の塊として扱われ、終わりにならない (https://soniox.com/docs/stt/api-reference/websocket-api)。
    isForcing = true;
    ws.send("");
  }
  await closed;
  return { segments, error };
}
