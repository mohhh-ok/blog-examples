// 話者ごとに 4 変種 (loud_clean / quiet_clean / loud_noise / quiet_noise) を作り、
// それぞれから 3 条件 (N: denoise なし, D: denoise 強制, R: 16kHz mono 化のみ) の
// prepared ref wav を作る。詳細は README の「手法」節参照。
//
// 入力: env REF_SPEAKERS = "label=path,label=path,..." (話者 wav へのフルパス)
// 出力: env OUT_DIR 配下の refs/<label>_<variant>/{variant.wav, truncated.wav, N.wav, D.wav, R.wav}
//       と refs/manifest.json
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { denoiseWavFile } from "./lib/denoise";
import {
  getAudioSampleRate,
  getWavDurationSec,
  measureIntegratedLufs,
  measureMaxVolumeDb,
  measureMeanVolumeDb,
  measureNoiseFloorDb,
  runFfmpeg,
  runProcessCapture,
  WAV_INPUT_FORMAT_ARGS,
} from "./lib/ffmpeg";

const OUT_DIR = process.env.OUT_DIR ?? "./output";
const REF_TRUNCATE_SEC = 15;
const NOISE_TARGET_OFFSET_DB = 20; // pink noise RMS = clean の max_volume - 20dB
const NOISE_SEED = 1234;

const DENOISE_SNR_THRESHOLD_DB = 30;
const DENOISE_MIN_MAX_VOLUME_DB = -15;
// noise 加算後 (amix) の max_volume がこれを超えたら clipping とみなして即座に止める
// (fail-loud)。loud_clean を TP=-3dB (3dB ヘッドルーム) にした上で noise を加算しても、
// 加算後のピークがここを超えるなら headroom 設計自体を見直す必要がある。
const NOISE_MIXED_MAX_VOLUME_LIMIT_DB = -0.5;

type SpeakerVariant = "loud_clean" | "quiet_clean" | "loud_noise" | "quiet_noise";
const VARIANTS: SpeakerVariant[] = ["loud_clean", "quiet_clean", "loud_noise", "quiet_noise"];

type RefManifestEntry = {
  speaker: string;
  variant: SpeakerVariant;
  sampleRate: number;
  durationSec: number;
  maxVolumeDb: number | undefined;
  meanVolumeDb: number | undefined;
  noiseFloorDb: number | undefined;
  snrDb: number | undefined;
  lufsIntegrated: number | undefined;
  wouldDenoise: boolean | undefined;
  // loud_noise / quiet_noise のみ: pink noise 加算直後 (truncate 前、フル尺) の
  // max_volume。clipping (0dBFS 張り付き) が起きていないかの診断用。clean 変種は undefined。
  postNoiseMaxVolumeDb: number | undefined;
};

async function measureOverallRmsDb(filePath: string): Promise<number | undefined> {
  const stderr = await runProcessCapture(
    "ffmpeg",
    ["-hide_banner", ...WAV_INPUT_FORMAT_ARGS, "-i", filePath, "-af", "astats", "-f", "null", "-"],
    "astats-overall-rms",
    { captureStderr: true },
  );
  const m = /RMS level dB:\s*(-?[\d.]+)/.exec(stderr);
  if (!m) return undefined;
  const value = Number(m[1]);
  return Number.isFinite(value) ? value : undefined;
}

async function makeLoudClean(params: { inputPath: string; outputPath: string }): Promise<void> {
  // loudnorm は内部で 192kHz にアップサンプルするため、-ar を明示しないと出力が 192kHz に
  // なり「元のサンプルレート維持」の仕様が壊れる (実運用の TTS パイプラインの loudness
  // 正規化処理でも同じ罠が知られている)。
  const sourceSampleRate = await getAudioSampleRate(params.inputPath);
  await runFfmpeg(
    [
      ...WAV_INPUT_FORMAT_ARGS,
      "-i",
      params.inputPath,
      "-af",
      // TP=-4dB (4dB ヘッドルーム、team-lead 指摘対応 2回目): TP=-1.5dB だと noise 加算後の
      // ピークが 0dBFS に張り付いてクリップした。TP=-3dB へ緩和した後も実話者 (M1) の
      // loud_noise で post-mix max が -0.4dB となり fail-loud 閾値 (-0.5dB) を超過したため、
      // さらに 1dB ヘッドルームを広げた。
      "loudnorm=I=-16:TP=-4:LRA=11",
      "-ar",
      String(sourceSampleRate),
      "-c:a",
      "pcm_s16le",
      params.outputPath,
    ],
    "prepare-refs: loud_clean (loudnorm)",
  );
}

async function makeQuietClean(params: { inputPath: string; outputPath: string }): Promise<void> {
  await runFfmpeg(
    // -10dB (team-lead 指摘対応 2回目): loud_clean が TP=-4dB になったことに合わせ、quiet の
    // max が本番ゲートの下限 (max>=-15dB) の内側 (-14dB 付近) を維持するよう調整
    // (TP=-4 + volume=-10dB = -14dB、TP=-3 + volume=-11dB = -14dB と同じ狙い値を維持)。
    [...WAV_INPUT_FORMAT_ARGS, "-i", params.inputPath, "-af", "volume=-10dB", "-c:a", "pcm_s16le", params.outputPath],
    "prepare-refs: quiet_clean (volume -10dB)",
  );
}

async function makeNoisyVariant(params: {
  cleanPath: string;
  outputPath: string;
  workDir: string;
  tag: string;
}): Promise<number> {
  const sampleRate = await getAudioSampleRate(params.cleanPath);
  const durationSec = await getWavDurationSec(params.cleanPath);
  const cleanMaxVolumeDb = await measureMaxVolumeDb(params.cleanPath);
  if (cleanMaxVolumeDb === undefined) {
    throw new Error(`makeNoisyVariant: volumedetect failed for ${params.cleanPath}`);
  }
  const targetRmsDb = cleanMaxVolumeDb - NOISE_TARGET_OFFSET_DB;

  const rawNoisePath = path.join(params.workDir, `${params.tag}.noise_raw.wav`);
  await runFfmpeg(
    [
      "-f",
      "lavfi",
      "-i",
      `anoisesrc=color=pink:seed=${NOISE_SEED}:sample_rate=${sampleRate}:duration=${durationSec.toFixed(3)}`,
      "-af",
      "lowpass=f=8000",
      "-c:a",
      "pcm_s16le",
      rawNoisePath,
    ],
    "prepare-refs: generate pink noise",
  );

  const measuredNoiseRmsDb = await measureOverallRmsDb(rawNoisePath);
  if (measuredNoiseRmsDb === undefined) {
    throw new Error(`makeNoisyVariant: astats RMS measurement failed for ${rawNoisePath}`);
  }
  const gainDb = targetRmsDb - measuredNoiseRmsDb;

  const adjustedNoisePath = path.join(params.workDir, `${params.tag}.noise_adjusted.wav`);
  await runFfmpeg(
    [
      ...WAV_INPUT_FORMAT_ARGS,
      "-i",
      rawNoisePath,
      "-af",
      `volume=${gainDb.toFixed(3)}dB`,
      "-c:a",
      "pcm_s16le",
      adjustedNoisePath,
    ],
    "prepare-refs: adjust pink noise gain",
  );

  await runFfmpeg(
    [
      ...WAV_INPUT_FORMAT_ARGS,
      "-i",
      params.cleanPath,
      ...WAV_INPUT_FORMAT_ARGS,
      "-i",
      adjustedNoisePath,
      "-filter_complex",
      "[0][1]amix=inputs=2:normalize=0",
      "-c:a",
      "pcm_s16le",
      params.outputPath,
    ],
    "prepare-refs: mix clean + pink noise",
  );

  // fail-loud (team-lead 指摘対応): noise 加算でピークが 0dBFS に張り付く (clipping) と
  // denoise 以外の変数 (歪み) が ref に混入する。加算直後に max_volume を測り、
  // NOISE_MIXED_MAX_VOLUME_LIMIT_DB を超えていたら (未測定を含め) 例外で即座に止める。
  const postNoiseMaxVolumeDb = await measureMaxVolumeDb(params.outputPath);
  if (postNoiseMaxVolumeDb === undefined || postNoiseMaxVolumeDb > NOISE_MIXED_MAX_VOLUME_LIMIT_DB) {
    throw new Error(
      `makeNoisyVariant: post-mix max_volume ${postNoiseMaxVolumeDb ?? "undefined"}dB exceeds limit ${NOISE_MIXED_MAX_VOLUME_LIMIT_DB}dB for ${params.outputPath} (clipping suspected)`,
    );
  }
  return postNoiseMaxVolumeDb;
}

async function truncateTo15s(params: { inputPath: string; outputPath: string }): Promise<void> {
  await runFfmpeg(
    [
      ...WAV_INPUT_FORMAT_ARGS,
      "-i",
      params.inputPath,
      "-af",
      `atrim=end=${REF_TRUNCATE_SEC.toFixed(3)}`,
      "-c:a",
      "pcm_s16le",
      params.outputPath,
    ],
    "prepare-refs: truncate to 15s",
  );
}

async function densify(params: { inputPath: string; outputPath: string }): Promise<void> {
  const filter =
    "silenceremove=start_periods=1:start_silence=0.2:start_threshold=-40dB:detection=peak:stop_periods=-1:stop_silence=0.3:stop_threshold=-40dB,loudnorm=I=-18:TP=-1.5:LRA=11";
  await runFfmpeg(
    [...WAV_INPUT_FORMAT_ARGS, "-i", params.inputPath, "-af", filter, "-c:a", "pcm_s16le", params.outputPath],
    "prepare-refs: densify (silenceremove + loudnorm)",
  );
}

async function padTail(params: { inputPath: string; outputPath: string }): Promise<void> {
  await runFfmpeg(
    [
      ...WAV_INPUT_FORMAT_ARGS,
      "-i",
      params.inputPath,
      "-af",
      "apad=pad_dur=0.500",
      "-c:a",
      "pcm_s16le",
      params.outputPath,
    ],
    "prepare-refs: pad tail silence",
  );
}

async function resampleTo16kMono(params: { inputPath: string; outputPath: string }): Promise<void> {
  await runFfmpeg(
    [...WAV_INPUT_FORMAT_ARGS, "-i", params.inputPath, "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", params.outputPath],
    "prepare-refs: resample to 16kHz mono",
  );
}

type GateMeasurement = {
  durationSec: number;
  sampleRate: number;
  maxVolumeDb: number | undefined;
  meanVolumeDb: number | undefined;
  noiseFloorDb: number | undefined;
  snrDb: number | undefined;
  lufsIntegrated: number | undefined;
  wouldDenoise: boolean | undefined;
};

async function measureGate(filePath: string): Promise<GateMeasurement> {
  const [durationSec, sampleRate, maxVolumeDb, meanVolumeDb, lufsIntegrated] = await Promise.all([
    getWavDurationSec(filePath),
    getAudioSampleRate(filePath),
    measureMaxVolumeDb(filePath),
    measureMeanVolumeDb(filePath),
    measureIntegratedLufs(filePath),
  ]);
  const noiseFloorDb = maxVolumeDb === undefined ? undefined : await measureNoiseFloorDb(filePath);
  const snrDb = maxVolumeDb !== undefined && noiseFloorDb !== undefined ? maxVolumeDb - noiseFloorDb : undefined;
  const wouldDenoise =
    snrDb !== undefined && maxVolumeDb !== undefined
      ? snrDb < DENOISE_SNR_THRESHOLD_DB && maxVolumeDb >= DENOISE_MIN_MAX_VOLUME_DB
      : undefined;
  return { durationSec, sampleRate, maxVolumeDb, meanVolumeDb, noiseFloorDb, snrDb, lufsIntegrated, wouldDenoise };
}

async function parseRefSpeakers(): Promise<Array<{ label: string; path: string }>> {
  const raw = process.env.REF_SPEAKERS;
  if (!raw) {
    throw new Error(
      "REF_SPEAKERS env is required (comma-separated label=path pairs, e.g. speaker1=/path/to.wav,speaker2=/path/to2.wav)",
    );
  }
  return raw.split(",").map((entry) => {
    const idx = entry.indexOf("=");
    if (idx < 0) throw new Error(`REF_SPEAKERS: invalid entry "${entry}", expected label=path`);
    return { label: entry.slice(0, idx).trim(), path: entry.slice(idx + 1).trim() };
  });
}

async function main(): Promise<void> {
  const speakers = await parseRefSpeakers();
  const falKey = process.env.FAL_KEY;
  if (!falKey) throw new Error("FAL_KEY env is required");

  const refsDir = path.join(OUT_DIR, "refs");
  await mkdir(refsDir, { recursive: true });

  const manifest: Record<string, RefManifestEntry> = {};

  for (const speaker of speakers) {
    console.log(`[prepare-refs] speaker=${speaker.label} input=${speaker.path}`);

    const speakerWorkDir = path.join(refsDir, `${speaker.label}_work`);
    await mkdir(speakerWorkDir, { recursive: true });

    const loudCleanPath = path.join(speakerWorkDir, "loud_clean.wav");
    await makeLoudClean({ inputPath: speaker.path, outputPath: loudCleanPath });

    const quietCleanPath = path.join(speakerWorkDir, "quiet_clean.wav");
    await makeQuietClean({ inputPath: loudCleanPath, outputPath: quietCleanPath });

    const loudNoisePath = path.join(speakerWorkDir, "loud_noise.wav");
    const loudNoisePostMixMaxVolumeDb = await makeNoisyVariant({
      cleanPath: loudCleanPath,
      outputPath: loudNoisePath,
      workDir: speakerWorkDir,
      tag: "loud",
    });

    const quietNoisePath = path.join(speakerWorkDir, "quiet_noise.wav");
    const quietNoisePostMixMaxVolumeDb = await makeNoisyVariant({
      cleanPath: quietCleanPath,
      outputPath: quietNoisePath,
      workDir: speakerWorkDir,
      tag: "quiet",
    });

    const variantPaths: Record<SpeakerVariant, string> = {
      loud_clean: loudCleanPath,
      quiet_clean: quietCleanPath,
      loud_noise: loudNoisePath,
      quiet_noise: quietNoisePath,
    };
    const postNoiseMaxVolumeDbByVariant: Partial<Record<SpeakerVariant, number>> = {
      loud_noise: loudNoisePostMixMaxVolumeDb,
      quiet_noise: quietNoisePostMixMaxVolumeDb,
    };

    for (const variant of VARIANTS) {
      const refKey = `${speaker.label}_${variant}`;
      const refDir = path.join(refsDir, refKey);
      await mkdir(refDir, { recursive: true });

      const variantOut = path.join(refDir, "variant.wav");
      await runFfmpeg(
        [...WAV_INPUT_FORMAT_ARGS, "-i", variantPaths[variant], "-c:a", "copy", variantOut],
        `prepare-refs: copy ${refKey} variant.wav`,
      );

      const truncatedPath = path.join(refDir, "truncated.wav");
      await truncateTo15s({ inputPath: variantOut, outputPath: truncatedPath });

      const gate = await measureGate(truncatedPath);
      const postNoiseMaxVolumeDb = postNoiseMaxVolumeDbByVariant[variant];
      manifest[refKey] = {
        speaker: speaker.label,
        variant,
        sampleRate: gate.sampleRate,
        durationSec: gate.durationSec,
        maxVolumeDb: gate.maxVolumeDb,
        meanVolumeDb: gate.meanVolumeDb,
        noiseFloorDb: gate.noiseFloorDb,
        snrDb: gate.snrDb,
        lufsIntegrated: gate.lufsIntegrated,
        wouldDenoise: gate.wouldDenoise,
        postNoiseMaxVolumeDb,
      };
      console.log(
        `[prepare-refs] ${refKey}: max=${gate.maxVolumeDb?.toFixed(2)}dB mean=${gate.meanVolumeDb?.toFixed(2)}dB floor=${gate.noiseFloorDb?.toFixed(2)}dB snr=${gate.snrDb?.toFixed(2)}dB lufs=${gate.lufsIntegrated?.toFixed(2)} wouldDenoise=${gate.wouldDenoise}${postNoiseMaxVolumeDb !== undefined ? ` postNoiseMax=${postNoiseMaxVolumeDb.toFixed(2)}dB` : ""}`,
      );

      // N: truncate -> densify -> pad
      const nDensified = path.join(refDir, "N.densified.wav");
      await densify({ inputPath: truncatedPath, outputPath: nDensified });
      await padTail({ inputPath: nDensified, outputPath: path.join(refDir, "N.wav") });

      // R: truncate -> 16kHz mono -> densify -> pad
      const rResampled = path.join(refDir, "R.resampled.wav");
      await resampleTo16kMono({ inputPath: truncatedPath, outputPath: rResampled });
      const rDensified = path.join(refDir, "R.densified.wav");
      await densify({ inputPath: rResampled, outputPath: rDensified });
      await padTail({ inputPath: rDensified, outputPath: path.join(refDir, "R.wav") });

      // D: truncate -> fal deepfilternet3 -> 16kHz mono -> densify -> pad
      const dDenoised = path.join(refDir, "D.denoised_raw.wav");
      await denoiseWavFile({ inputPath: truncatedPath, outputPath: dDenoised, falKey });
      const dResampled = path.join(refDir, "D.resampled.wav");
      await resampleTo16kMono({ inputPath: dDenoised, outputPath: dResampled });
      const dDensified = path.join(refDir, "D.densified.wav");
      await densify({ inputPath: dResampled, outputPath: dDensified });
      await padTail({ inputPath: dDensified, outputPath: path.join(refDir, "D.wav") });
    }
  }

  await writeFile(path.join(refsDir, "manifest.json"), JSON.stringify(manifest, null, 2), "utf-8");
  console.log(`[prepare-refs] done. manifest: ${path.join(refsDir, "manifest.json")}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
