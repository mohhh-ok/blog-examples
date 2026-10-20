import { spawn } from "node:child_process";

// 計測で送る音声の形。ElevenLabs のプラグインの既定 (pcm_16000) と Soniox のプラグインの既定 (16000Hz) にそろえる。
export const SAMPLE_RATE = 16000;
// 発話の終わりを決める窓の長さ。
const SPEECH_FRAME_MS = 10;
// 雑音の床 (窓の RMS の下位 10%) と声の上 (上位 5%) の間の、床から 10% の位置をしきい値にする。
const NOISE_FLOOR_QUANTILE = 0.1;
const SPEECH_TOP_QUANTILE = 0.95;
const THRESHOLD_POSITION = 0.1;
// しきい値を超える窓がこの長さ以上続いたものだけを声とみなす (クリックのような短い雑音を除く)。
const MIN_SPEECH_RUN_MS = 100;
// 声の上が雑音の床のこの倍に届かない音声は、声と雑音を分けられないので話し終わりを決めない。
const MIN_TOP_TO_FLOOR_RATIO = 4;

export type DecodedAudio = {
  pcm: Buffer;
  durationMs: number;
  // 話し終わりの時刻。声と雑音を分けられない音声は null。
  speechEndMs: number | null;
};

// ffmpeg で 16kHz・モノラル・16bit の生の PCM に変換し、発話の終わりの時刻を求める。
export async function decodeAudio(path: string): Promise<DecodedAudio> {
  const pcm = await runFfmpeg(path);
  const samples = pcm.length / 2;
  return {
    pcm,
    durationMs: (samples / SAMPLE_RATE) * 1000,
    speechEndMs: detectSpeechEndMs(pcm),
  };
}

// 10ms の窓ごとの RMS を取り、しきい値以上が 100ms 以上続いた最後のまとまりの終わりを話し終わりとする。
export function detectSpeechEndMs(pcm: Buffer): number | null {
  const frameSamples = (SAMPLE_RATE * SPEECH_FRAME_MS) / 1000;
  const frameCount = Math.floor(pcm.length / 2 / frameSamples);
  const rms: number[] = [];
  for (let frame = 0; frame < frameCount; frame++) {
    let sum = 0;
    for (let index = 0; index < frameSamples; index++) {
      const value = pcm.readInt16LE((frame * frameSamples + index) * 2) / 32768;
      sum += value * value;
    }
    rms.push(Math.sqrt(sum / frameSamples));
  }
  const sorted = [...rms].sort((a, b) => a - b);
  const floor = sorted[Math.floor((sorted.length - 1) * NOISE_FLOOR_QUANTILE)] ?? 0;
  const top = sorted[Math.floor((sorted.length - 1) * SPEECH_TOP_QUANTILE)] ?? 0;
  if (top === 0) throw new Error("audio is silent");
  if (top < floor * MIN_TOP_TO_FLOOR_RATIO) return null;
  const threshold = floor + (top - floor) * THRESHOLD_POSITION;
  const minRunFrames = MIN_SPEECH_RUN_MS / SPEECH_FRAME_MS;
  let lastRunEnd: number | null = null;
  let runLength = 0;
  rms.forEach((value, frame) => {
    runLength = value >= threshold ? runLength + 1 : 0;
    if (runLength >= minRunFrames) lastRunEnd = frame + 1;
  });
  return lastRunEnd === null ? null : lastRunEnd * SPEECH_FRAME_MS;
}

function runFfmpeg(path: string): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const child = spawn("ffmpeg", ["-hide_banner", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", String(SAMPLE_RATE), "-f", "s16le", "-"]);
    const chunks: Buffer[] = [];
    const errors: Buffer[] = [];
    child.stdout.on("data", (chunk: Buffer) => chunks.push(chunk));
    child.stderr.on("data", (chunk: Buffer) => errors.push(chunk));
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) reject(new Error(`ffmpeg failed (${code}): ${Buffer.concat(errors).toString()}`));
      else resolve(Buffer.concat(chunks));
    });
  });
}
