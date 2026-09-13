// whisper-1 書き起こし。実運用の TTS パイプラインと同じ prompt 加工
// (空白正規化 → 末尾 224 文字) を使う。
import OpenAI from "openai";
import { createReadStream } from "node:fs";

export const PROMPT_MAX_CHARS = 224;

export function normalizeTranscriptionPrompt(prompt: string): string {
  return prompt.replace(/\s+/g, " ").trim();
}

export function truncateTranscriptionPrompt(prompt: string): string {
  return prompt.length > PROMPT_MAX_CHARS ? prompt.slice(-PROMPT_MAX_CHARS) : prompt;
}

export function buildTranscriptionPrompt(script: string): string {
  return truncateTranscriptionPrompt(normalizeTranscriptionPrompt(script));
}

export type TranscribeResult = {
  text: string;
  whisperMs: number;
};

export async function transcribeAudio(params: {
  filePath: string;
  prompt: string;
  apiKey: string;
}): Promise<TranscribeResult> {
  const openai = new OpenAI({ apiKey: params.apiKey });
  const startedAt = Date.now();
  const response = await openai.audio.transcriptions.create({
    model: "whisper-1",
    file: createReadStream(params.filePath),
    response_format: "verbose_json",
    timestamp_granularities: ["word"],
    prompt: params.prompt,
  });
  return { text: response.text, whisperMs: Date.now() - startedAt };
}
