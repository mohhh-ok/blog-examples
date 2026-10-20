import { performance } from "node:perf_hooks";
import { setTimeout as sleep } from "node:timers/promises";
import { SAMPLE_RATE } from "./audio.ts";

// マイクから届くのと同じ速さで送る。1 つの塊は 50ms (ElevenLabs のプラグインの既定の audioChunkDuration)。
export const CHUNK_MS = 50;

export type StreamClock = { startedAt: number };

// 塊 i は、その塊の音が録り終わる時刻 (開始 + (i + 1) × 50ms) に送る。音声の後に無音を trailingSilenceMs だけ足して送る。
export async function streamRealtime(options: {
  pcm: Buffer;
  trailingSilenceMs: number;
  clock: StreamClock;
  send: (chunk: Buffer) => void;
  isClosed: () => boolean;
}): Promise<void> {
  const bytesPerChunk = ((SAMPLE_RATE * CHUNK_MS) / 1000) * 2;
  const silence = Buffer.alloc(((SAMPLE_RATE * options.trailingSilenceMs) / 1000) * 2);
  const audio = Buffer.concat([options.pcm, silence]);
  const chunkCount = Math.ceil(audio.length / bytesPerChunk);
  for (let index = 0; index < chunkCount; index++) {
    const due = options.clock.startedAt + (index + 1) * CHUNK_MS;
    const wait = due - performance.now();
    if (wait > 0) await sleep(wait);
    if (options.isClosed()) return;
    options.send(audio.subarray(index * bytesPerChunk, (index + 1) * bytesPerChunk));
  }
}

export function elapsedMs(clock: StreamClock): number {
  return performance.now() - clock.startedAt;
}
