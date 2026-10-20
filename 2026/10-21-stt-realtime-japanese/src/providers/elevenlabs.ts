import { performance } from "node:perf_hooks";
import { elapsedMs, streamRealtime, type StreamClock } from "../stream.ts";
import { SAMPLE_RATE } from "../audio.ts";
import type { FinalSegment, Provider, TranscribeInput, TranscribeResult } from "./types.ts";

// LiveKit の @livekit/agents-plugin-elevenlabs 1.9.3 が serverVad 付きでつなぐときと同じ設定にする
// (model scribe_v2_realtime・無音 0.5 秒で確定・言語を指定)。
const MODEL = "scribe_v2_realtime";
const VAD_SILENCE_THRESHOLD_SECS = 0.5;
const BASE_URL = "wss://api.elevenlabs.io/v1/speech-to-text/realtime";
// 音声の後に足す無音。無音 0.5 秒の確定が起きるのに十分な長さ。
const TRAILING_SILENCE_MS = 3000;
// 終わりを明示 (commit) してから確定を待つ上限。
const FORCED_COMMIT_TIMEOUT_MS = 5000;

export function createElevenLabsProvider(options: { apiKey: string }): Provider {
  return {
    name: "elevenlabs",
    describeSettings: ({ language, hasTerms }) => ({
      endpoint: BASE_URL,
      model_id: MODEL,
      audio_format: `pcm_${SAMPLE_RATE}`,
      commit_strategy: "vad",
      vad_silence_threshold_secs: VAD_SILENCE_THRESHOLD_SECS,
      language_code: language,
      enable_logging: true,
      keyterms: hasTerms ? "その文の固有名詞の一覧" : "なし",
    }),
    transcribe: (input) => transcribe({ apiKey: options.apiKey, input }),
  };
}

function buildUrl(input: TranscribeInput): string {
  const params = new URLSearchParams({
    model_id: MODEL,
    audio_format: `pcm_${SAMPLE_RATE}`,
    commit_strategy: "vad",
    enable_logging: "true",
    vad_silence_threshold_secs: String(VAD_SILENCE_THRESHOLD_SECS),
    language_code: input.language,
  });
  for (const term of input.terms ?? []) params.append("keyterms", term);
  return `${BASE_URL}?${params.toString()}`;
}

async function transcribe(options: { apiKey: string; input: TranscribeInput }): Promise<TranscribeResult> {
  const { input } = options;
  const segments: FinalSegment[] = [];
  let error: string | null = null;
  let isForcing = false;
  let isClosed = false;
  const clock: StreamClock = { startedAt: 0 };

  // Node の WebSocket (undici) は 2 つ目の引数で headers を渡せる。
  const ws = new WebSocket(buildUrl(input), { headers: { "xi-api-key": options.apiKey } } as unknown as string[]);
  const closed = new Promise<void>((resolve) => {
    ws.addEventListener("close", () => {
      isClosed = true;
      resolve();
    });
  });
  let resolveCommitted: () => void = () => {};
  ws.addEventListener("message", (event) => {
    const data = JSON.parse(String(event.data)) as { message_type?: string; text?: string; error?: string };
    if (data.message_type === "committed_transcript") {
      if (data.text) segments.push({ text: data.text, receivedAtMs: elapsedMs(clock), isForced: isForcing });
      if (isForcing) resolveCommitted();
    } else if (data.message_type !== "partial_transcript" && data.message_type !== "session_started") {
      error = `${data.message_type}: ${data.error ?? JSON.stringify(data)}`;
      ws.close();
    }
  });
  await new Promise<void>((resolve, reject) => {
    ws.addEventListener("open", () => resolve(), { once: true });
    ws.addEventListener("error", () => reject(new Error("elevenlabs websocket error")), { once: true });
  });

  clock.startedAt = performance.now();
  await streamRealtime({
    pcm: input.pcm,
    trailingSilenceMs: TRAILING_SILENCE_MS,
    clock,
    isClosed: () => isClosed,
    send: (chunk) =>
      ws.send(JSON.stringify({ message_type: "input_audio_chunk", audio_base_64: chunk.toString("base64"), commit: false, sample_rate: SAMPLE_RATE })),
  });
  if (!isClosed) {
    // 無音の間に確定しなかった分を出させる。ここで届いた確定は isForced になる。
    isForcing = true;
    const committed = new Promise<void>((resolve) => {
      resolveCommitted = resolve;
    });
    ws.send(JSON.stringify({ message_type: "input_audio_chunk", audio_base_64: "", commit: true, sample_rate: SAMPLE_RATE }));
    await Promise.race([committed, closed, new Promise((resolve) => setTimeout(resolve, FORCED_COMMIT_TIMEOUT_MS))]);
    ws.close();
  }
  await closed;
  return { segments, error };
}
