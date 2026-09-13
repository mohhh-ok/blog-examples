// ffmpeg/ffprobe の薄いラッパーと、音量・ノイズフロア・LUFS の計測関数。
//
// 本プロジェクトが対象とする wav はすべて自前の ffmpeg 呼び出しが `-c:a pcm_s16le` で
// 書き出したものなので、コンテナ自動判別の誤認 (ffmpeg が WAV を稀に mpegts と誤認する
// バグ、content 依存で決定論的に再現する) を避けるため、読み込み時は常に `-f wav` を明示する。
export const WAV_INPUT_FORMAT_ARGS = ["-f", "wav"] as const;

import { spawn } from "node:child_process";

export async function runProcessCapture(
  cmd: string,
  args: string[],
  label: string,
  opts: { captureStderr?: boolean } = {},
): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", (error) => {
      reject(new Error(`${label} failed to start: ${error.message}`));
    });
    child.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(`${label} exited with code ${code}: ${stderr.slice(-2000)}`));
        return;
      }
      resolve(opts.captureStderr ? stderr : stdout);
    });
  });
}

export async function runFfmpeg(args: string[], label: string): Promise<void> {
  await runProcessCapture("ffmpeg", ["-y", "-hide_banner", ...args], label, { captureStderr: true });
}

export async function ffprobeJson(args: string[]): Promise<unknown> {
  const stdout = await runProcessCapture(
    "ffprobe",
    ["-v", "quiet", "-print_format", "json", ...args],
    "ffprobe",
  );
  return JSON.parse(stdout);
}

export async function getWavDurationSec(filePath: string): Promise<number> {
  const json = (await ffprobeJson([
    "-show_entries",
    "format=duration",
    ...WAV_INPUT_FORMAT_ARGS,
    filePath,
  ])) as { format?: { duration?: string } };
  const duration = Number(json.format?.duration);
  if (!Number.isFinite(duration)) {
    throw new Error(`getWavDurationSec: ffprobe returned invalid duration for ${filePath}`);
  }
  return duration;
}

export async function getAudioSampleRate(filePath: string): Promise<number> {
  const json = (await ffprobeJson([
    "-select_streams",
    "a:0",
    "-show_entries",
    "stream=sample_rate",
    ...WAV_INPUT_FORMAT_ARGS,
    filePath,
  ])) as { streams?: Array<{ sample_rate?: string }> };
  const rate = Number(json.streams?.[0]?.sample_rate);
  if (!Number.isFinite(rate) || rate <= 0) {
    throw new Error(`getAudioSampleRate: ffprobe returned invalid sample_rate for ${filePath}`);
  }
  return rate;
}

type VolumeStats = {
  maxVolumeDb: number | undefined;
  meanVolumeDb: number | undefined;
};

function parseVolumedetectValue(stderr: string, key: "max_volume" | "mean_volume"): number | undefined {
  const re = new RegExp(`${key}:\\s*(-?[\\d.]+)\\s*dB`);
  const m = re.exec(stderr);
  if (!m) return undefined;
  const value = Number(m[1]);
  return Number.isFinite(value) ? value : undefined;
}

async function measureVolumeStats(filePath: string): Promise<VolumeStats> {
  const stderr = await runProcessCapture(
    "ffmpeg",
    ["-hide_banner", ...WAV_INPUT_FORMAT_ARGS, "-i", filePath, "-af", "volumedetect", "-f", "null", "-"],
    "volumedetect",
    { captureStderr: true },
  );
  return {
    maxVolumeDb: parseVolumedetectValue(stderr, "max_volume"),
    meanVolumeDb: parseVolumedetectValue(stderr, "mean_volume"),
  };
}

export async function measureMaxVolumeDb(filePath: string): Promise<number | undefined> {
  const { maxVolumeDb } = await measureVolumeStats(filePath);
  return maxVolumeDb;
}

export async function measureMeanVolumeDb(filePath: string): Promise<number | undefined> {
  const { meanVolumeDb } = await measureVolumeStats(filePath);
  return meanVolumeDb;
}

// ノイズフロア推定: 0.4s 幅の窓で RMS level (dB) を系列化し、下位 25 パーセンタイルを
// ノイズフロアとみなす (実運用の TTS パイプライン側の同等ロジックと一致させている)。
const NOISE_FLOOR_WINDOW_SEC = 0.4;
const NOISE_FLOOR_PERCENTILE = 0.25;

export async function measureNoiseFloorDb(filePath: string): Promise<number | undefined> {
  const sampleRate = await getAudioSampleRate(filePath);
  const windowSamples = Math.max(1, Math.round(sampleRate * NOISE_FLOOR_WINDOW_SEC));
  const stdout = await runProcessCapture(
    "ffmpeg",
    [
      "-hide_banner",
      ...WAV_INPUT_FORMAT_ARGS,
      "-i",
      filePath,
      "-af",
      `asetnsamples=n=${windowSamples},astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-`,
      "-f",
      "null",
      "-",
    ],
    "astats-windowed-rms",
  );
  const values: number[] = [];
  for (const line of stdout.split("\n")) {
    const m = /lavfi\.astats\.Overall\.RMS_level=(-?[\d.]+)/.exec(line);
    if (!m) continue;
    const value = Number(m[1]);
    if (Number.isFinite(value)) values.push(value);
  }
  if (values.length === 0) return undefined;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.min(
    sorted.length - 1,
    Math.max(0, Math.floor(NOISE_FLOOR_PERCENTILE * (sorted.length - 1))),
  );
  return sorted[idx];
}

// EBU R128 Integrated loudness (LUFS)。ebur128 は summary を stderr に出す
// (`I:            -23.0 LUFS`)。観測用の記録にのみ使い、判定には使わない。
export async function measureIntegratedLufs(filePath: string): Promise<number | undefined> {
  const stderr = await runProcessCapture(
    "ffmpeg",
    ["-hide_banner", ...WAV_INPUT_FORMAT_ARGS, "-i", filePath, "-af", "ebur128", "-f", "null", "-"],
    "ebur128",
    { captureStderr: true },
  );
  const m = /^\s*I:\s*(-?[\d.]+)\s*LUFS/m.exec(stderr);
  if (!m) return undefined;
  const value = Number(m[1]);
  return Number.isFinite(value) ? value : undefined;
}

export async function runFfmpegCapture(args: string[], label: string): Promise<string> {
  return runProcessCapture("ffmpeg", ["-hide_banner", ...args], label, { captureStderr: true });
}
