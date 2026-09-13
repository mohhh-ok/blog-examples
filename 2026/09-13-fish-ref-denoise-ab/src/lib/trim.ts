// TTS 出力の無音圧縮 (trimExcessSilence) の再実装。
// 実運用の TTS パイプライン側の同等ロジック・定数と一致させている
// (「1s 以上の無音のみを検出し、各無音区間は先頭 0.4s だけ残して切り詰める」ワークアラウンド)。
import {
  getAudioSampleRate,
  getWavDurationSec,
  measureMaxVolumeDb,
  runFfmpeg,
  runProcessCapture,
  WAV_INPUT_FORMAT_ARGS,
} from "./ffmpeg";

export const TRIM_EXCESS_MIN_DETECT_SEC = 1.0;
export const TRIM_EXCESS_MAX_SILENCE_SEC = 0.4;
export const TRIM_EXCESS_THRESHOLD_DB = -30;
export const TRIM_EXCESS_THRESHOLD_OFFSET_DB = 25;

export function computeEffectiveTrimThresholdDb(
  maxVolumeDb: number | undefined,
  opts: { thresholdDb?: number; offsetDb?: number } = {},
): number {
  const thresholdDb = opts.thresholdDb ?? TRIM_EXCESS_THRESHOLD_DB;
  if (maxVolumeDb === undefined) return thresholdDb;
  const offsetDb = opts.offsetDb ?? TRIM_EXCESS_THRESHOLD_OFFSET_DB;
  return Math.min(thresholdDb, maxVolumeDb - offsetDb);
}

type Silence = { start: number; end: number };

async function detectSilences(
  audioPath: string,
  opts: { thresholdDb: number; minSilenceSec: number },
): Promise<Silence[]> {
  const log = await runProcessCapture(
    "ffmpeg",
    [
      "-hide_banner",
      ...WAV_INPUT_FORMAT_ARGS,
      "-i",
      audioPath,
      "-af",
      `silencedetect=noise=${opts.thresholdDb}dB:d=${opts.minSilenceSec}`,
      "-f",
      "null",
      "-",
    ],
    "silencedetect",
    { captureStderr: true },
  );
  const lines = log.split("\n");
  const silences: Silence[] = [];
  let pendingStart: number | undefined;
  for (const line of lines) {
    const ms = /silence_start: ([\d.]+)/.exec(line);
    if (ms) {
      pendingStart = Number(ms[1]);
      continue;
    }
    const me = /silence_end: ([\d.]+)/.exec(line);
    if (me && pendingStart !== undefined) {
      silences.push({ start: pendingStart, end: Number(me[1]) });
      pendingStart = undefined;
    }
  }
  return silences;
}

export type TrimExcessSilenceResult = {
  maxVolumeDb: number | undefined;
  thresholdDb: number;
  silenceCount: number;
};

export async function trimExcessSilence(params: {
  inputPath: string;
  outputPath: string;
  minDetectSec?: number;
  maxSilenceSec?: number;
  thresholdDb?: number;
}): Promise<TrimExcessSilenceResult> {
  const minDetectSec = params.minDetectSec ?? TRIM_EXCESS_MIN_DETECT_SEC;
  const maxSilenceSec = params.maxSilenceSec ?? TRIM_EXCESS_MAX_SILENCE_SEC;
  if (!(maxSilenceSec < minDetectSec)) {
    throw new Error(
      `trimExcessSilence: maxSilenceSec (${maxSilenceSec}) must be less than minDetectSec (${minDetectSec})`,
    );
  }

  let maxVolumeDb: number | undefined;
  try {
    maxVolumeDb = await measureMaxVolumeDb(params.inputPath);
  } catch {
    maxVolumeDb = undefined;
  }
  const thresholdDb = computeEffectiveTrimThresholdDb(maxVolumeDb, { thresholdDb: params.thresholdDb });

  const silences = await detectSilences(params.inputPath, { thresholdDb, minSilenceSec: minDetectSec });

  if (silences.length === 0) {
    await runFfmpeg(
      [...WAV_INPUT_FORMAT_ARGS, "-i", params.inputPath, "-c:a", "copy", params.outputPath],
      "trim-excess-silence copy",
    );
    return { maxVolumeDb, thresholdDb, silenceCount: 0 };
  }

  const totalDur = await getWavDurationSec(params.inputPath);
  const sampleRate = await getAudioSampleRate(params.inputPath);

  const segments: string[] = [];
  const labels: string[] = [];
  let cursor = 0;
  let idx = 0;
  const addSegment = (start: number, end: number, kind: "keep" | "sil"): void => {
    if (end <= start + 1e-4) return;
    const lbl = `${kind}${idx++}`;
    segments.push(
      `[0:a]atrim=start=${start.toFixed(3)}:end=${end.toFixed(3)},asetpts=PTS-STARTPTS[${lbl}]`,
    );
    labels.push(`[${lbl}]`);
  };
  for (const s of silences) {
    const silStart = Math.max(0, Math.min(s.start, totalDur));
    const silEnd = Math.max(silStart, Math.min(s.end, totalDur));
    addSegment(cursor, silStart, "keep");
    addSegment(silStart, Math.min(silStart + maxSilenceSec, silEnd), "sil");
    cursor = silEnd;
  }
  addSegment(cursor, totalDur, "keep");

  if (labels.length === 0) {
    await runFfmpeg(
      [...WAV_INPUT_FORMAT_ARGS, "-i", params.inputPath, "-c:a", "copy", params.outputPath],
      "trim-excess-silence copy",
    );
    return { maxVolumeDb, thresholdDb, silenceCount: silences.length };
  }

  const filterGraph = [
    ...segments,
    `${labels.join("")}concat=n=${labels.length}:v=0:a=1[out]`,
  ].join(";");
  await runFfmpeg(
    [
      ...WAV_INPUT_FORMAT_ARGS,
      "-i",
      params.inputPath,
      "-filter_complex",
      filterGraph,
      "-map",
      "[out]",
      "-ar",
      String(sampleRate),
      "-c:a",
      "pcm_s16le",
      params.outputPath,
    ],
    "trim excess silence",
  );
  return { maxVolumeDb, thresholdDb, silenceCount: silences.length };
}
