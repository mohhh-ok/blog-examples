// fal.ai DeepFilterNet3 denoise。実運用の TTS パイプラインと同じ endpoint / input contract
// を使う。
import { readFile, writeFile } from "node:fs/promises";
import { createFalClient } from "@fal-ai/client";

const DEEPFILTERNET3_ENDPOINT = "fal-ai/deepfilternet3";
const REQUEST_TIMEOUT_MS = 60_000;

export async function denoiseWavFile(params: {
  inputPath: string;
  outputPath: string;
  falKey: string;
}): Promise<void> {
  const fal = createFalClient({ credentials: params.falKey });
  const buffer = await readFile(params.inputPath);
  const blob = new Blob([new Uint8Array(buffer)], { type: "audio/wav" });
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), REQUEST_TIMEOUT_MS);
  try {
    const audioUrl = await fal.storage.upload(blob);
    const result = await fal.subscribe(DEEPFILTERNET3_ENDPOINT, {
      input: {
        audio_url: audioUrl,
        audio_format: "wav",
      },
      abortSignal: ac.signal,
    });
    const url = (result.data as { audio_file?: { url?: string } }).audio_file?.url;
    if (!url) {
      throw new Error("fal.ai deepfilternet3 returned no audio_file url");
    }
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`denoiseWavFile: HTTP ${res.status} for ${url}`);
    }
    const outBuf = Buffer.from(await res.arrayBuffer());
    await writeFile(params.outputPath, outBuf);
  } finally {
    clearTimeout(timer);
  }
}
