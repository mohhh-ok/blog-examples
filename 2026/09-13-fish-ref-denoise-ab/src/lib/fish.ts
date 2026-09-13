// Fish Audio /v1/tts の直叩き。実運用の TTS パイプラインと同じ endpoint / header / payload
// 契約を使う (model はヘッダで送る、references は inline zero-shot clone の生バイト列 +
// 空文字列の text)。
import { encode } from "@msgpack/msgpack";

export const FISH_TTS_ENDPOINT = "https://api.fish.audio/v1/tts";
export const FISH_TTS_MODEL = "s2.1-pro";
export const FISH_TTS_TEMPERATURE = 0.7;
export const FISH_TTS_TOP_P = 0.7;
export const FISH_TTS_TIMEOUT_MS = 90_000;
export const FISH_TTS_MAX_ATTEMPTS = 3;

const TRANSIENT_STATUSES = new Set([408, 429]);

class FishAbortError extends Error {}

function isTransient(status: number): boolean {
  return status >= 500 || TRANSIENT_STATUSES.has(status);
}

export type SynthesizeSpeechArgs = {
  text: string;
  referenceAudio: Uint8Array;
  apiKey: string;
};

export type SynthesizeSpeechResult = {
  audio: Buffer;
  attempts: number;
  fishMs: number;
};

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function synthesizeSpeech(args: SynthesizeSpeechArgs): Promise<SynthesizeSpeechResult> {
  const payload = {
    text: args.text,
    references: [{ audio: args.referenceAudio, text: "" }],
    format: "wav",
    temperature: FISH_TTS_TEMPERATURE,
    top_p: FISH_TTS_TOP_P,
  };
  const body = encode(payload);
  const headers: Record<string, string> = {
    Authorization: `Bearer ${args.apiKey}`,
    "Content-Type": "application/msgpack",
    model: FISH_TTS_MODEL,
  };

  const startedAt = Date.now();
  let lastError: Error | undefined;
  for (let attempt = 1; attempt <= FISH_TTS_MAX_ATTEMPTS; attempt++) {
    const ac = new AbortController();
    const timer = setTimeout(() => ac.abort(), FISH_TTS_TIMEOUT_MS);
    try {
      const res = await fetch(FISH_TTS_ENDPOINT, {
        method: "POST",
        headers,
        body,
        signal: ac.signal,
      });
      if (!res.ok) {
        const bodyText = await res.text().catch(() => "");
        const message = `fish tts failed with status ${res.status}: ${bodyText.slice(0, 500)}`;
        if (!isTransient(res.status)) {
          throw new FishAbortError(message);
        }
        lastError = new Error(message);
        if (attempt < FISH_TTS_MAX_ATTEMPTS) {
          await sleep(1000 * attempt); // 1s -> 2s
          continue;
        }
        throw lastError;
      }
      const arrayBuffer = await res.arrayBuffer();
      return { audio: Buffer.from(arrayBuffer), attempts: attempt, fishMs: Date.now() - startedAt };
    } catch (error) {
      if (error instanceof FishAbortError) throw error;
      lastError = error instanceof Error ? error : new Error(String(error));
      if (attempt < FISH_TTS_MAX_ATTEMPTS) {
        await sleep(1000 * attempt);
        continue;
      }
      throw lastError;
    } finally {
      clearTimeout(timer);
    }
  }
  throw lastError ?? new Error("fish tts: unreachable");
}
