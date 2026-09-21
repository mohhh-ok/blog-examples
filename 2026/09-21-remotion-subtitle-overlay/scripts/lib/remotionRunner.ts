import fs from "node:fs/promises";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition, openBrowser, type HeadlessBrowser } from "@remotion/renderer";
import { FPS, WIDTH, HEIGHT } from "../../src/constants";
import type { SceneProps } from "../../src/compositions/Scene";
import type { SubtitlesOnlyProps } from "../../src/compositions/SubtitlesOnly";
import type { ConcurrencySetting, ConditionId, RunRecord } from "./types";

const execFileAsync = promisify(execFile);
// 既定は PATH 上の ffmpeg を使う (Homebrew/apt どちらでも動く)。別の場所にある
// 場合だけ FFMPEG_BIN で上書きする。
const FFMPEG_BIN = process.env["FFMPEG_BIN"] ?? "ffmpeg";
const ENTRY_POINT = path.join(import.meta.dir, "..", "..", "src", "index.ts");

async function statOrNull(filePath: string): Promise<number | null> {
  try {
    const stat = await fs.stat(filePath);
    return stat.size;
  } catch {
    return null;
  }
}

function resolveConcurrency(concurrency: ConcurrencySetting): number | undefined {
  return concurrency === "default" ? undefined : concurrency;
}

export async function bundleOnce(): Promise<{ bundleLocation: string; wallTimeMs: number }> {
  const start = performance.now();
  const bundleLocation = await bundle({ entryPoint: ENTRY_POINT });
  const wallTimeMs = performance.now() - start;
  return { bundleLocation, wallTimeMs };
}

// 計測全体で 1 つのブラウザを使い回す。理由: Google Fonts (Noto Sans JP) は
// "japanese" subset だけで 100 チャンク超に分かれており、renderMedia のたびに
// 新しいブラウザを起動すると毎回フォントを再ダウンロードしてしまい、
// フォント取得のネットワーク時間が描画コストの比較に混入してしまう
// (実機で 1 タブあたり 100+ リクエストを確認)。同一ブラウザを使い回せば
// 初回以降は HTTP キャッシュが効き、以降の計測はレンダリング自体の時間に
// 近づく。
export async function openSharedBrowser(): Promise<HeadlessBrowser> {
  return openBrowser("chrome");
}

export async function closeSharedBrowser(browser: HeadlessBrowser): Promise<void> {
  await browser.close({ silent: true });
}

export async function renderScene(args: {
  bundleLocation: string;
  outputPath: string;
  durationSec: number;
  concurrency: ConcurrencySetting;
  sceneProps: SceneProps;
  condition: ConditionId;
  rep: number;
  puppeteerInstance?: HeadlessBrowser;
}): Promise<RunRecord> {
  const {
    bundleLocation,
    outputPath,
    durationSec,
    concurrency,
    sceneProps,
    condition,
    rep,
    puppeteerInstance,
  } = args;
  await fs.mkdir(path.dirname(outputPath), { recursive: true });

  const browserLogs: string[] = [];
  let error: string | undefined;
  const start = performance.now();
  try {
    const composition = await selectComposition({
      serveUrl: bundleLocation,
      id: "scene",
      inputProps: sceneProps,
      puppeteerInstance,
    });
    await renderMedia({
      composition,
      serveUrl: bundleLocation,
      codec: "h264",
      outputLocation: outputPath,
      inputProps: sceneProps,
      overwrite: true,
      concurrency: resolveConcurrency(concurrency),
      logLevel: "verbose",
      puppeteerInstance,
      onBrowserLog: (log) => {
        browserLogs.push(`[${log.type}] ${log.text}`);
      },
    });
  } catch (err) {
    error = (err as Error).message;
  }
  const wallTimeMs = performance.now() - start;
  const outputBytes = error ? null : await statOrNull(outputPath);

  return {
    condition,
    phase: "render",
    rep,
    concurrency,
    durationSec,
    fps: FPS,
    width: WIDTH,
    height: HEIGHT,
    wallTimeMs,
    outputPath,
    outputBytes,
    secondsPerSecond: wallTimeMs / 1000 / durationSec,
    browserLogs: browserLogs.length > 0 ? browserLogs : undefined,
    timestamp: new Date().toISOString(),
    error,
  };
}

export async function renderTransparentSubtitles(args: {
  bundleLocation: string;
  outputPath: string;
  durationSec: number;
  concurrency: ConcurrencySetting;
  codec: "vp9" | "prores";
  condition: ConditionId;
  rep: number;
  puppeteerInstance?: HeadlessBrowser;
}): Promise<RunRecord> {
  const {
    bundleLocation,
    outputPath,
    durationSec,
    concurrency,
    codec,
    condition,
    rep,
    puppeteerInstance,
  } = args;
  await fs.mkdir(path.dirname(outputPath), { recursive: true });

  const subtitlesOnlyProps: SubtitlesOnlyProps = { durationSec };
  const pixelFormat = codec === "vp9" ? "yuva420p" : "yuva444p10le";

  const browserLogs: string[] = [];
  let error: string | undefined;
  const start = performance.now();
  try {
    const composition = await selectComposition({
      serveUrl: bundleLocation,
      id: "subtitles-only",
      inputProps: subtitlesOnlyProps,
      puppeteerInstance,
    });
    await renderMedia({
      composition,
      serveUrl: bundleLocation,
      codec,
      proResProfile: codec === "prores" ? "4444" : undefined,
      imageFormat: "png",
      pixelFormat,
      outputLocation: outputPath,
      inputProps: subtitlesOnlyProps,
      overwrite: true,
      concurrency: resolveConcurrency(concurrency),
      logLevel: "verbose",
      puppeteerInstance,
      onBrowserLog: (log) => {
        browserLogs.push(`[${log.type}] ${log.text}`);
      },
    });
  } catch (err) {
    error = (err as Error).message;
  }
  const wallTimeMs = performance.now() - start;
  const outputBytes = error ? null : await statOrNull(outputPath);

  return {
    condition,
    phase: "render",
    rep,
    concurrency,
    durationSec,
    fps: FPS,
    width: WIDTH,
    height: HEIGHT,
    wallTimeMs,
    outputPath,
    outputBytes,
    secondsPerSecond: wallTimeMs / 1000 / durationSec,
    browserLogs: browserLogs.length > 0 ? browserLogs : undefined,
    timestamp: new Date().toISOString(),
    error,
  };
}

// Z 条件の「重ねる」段階: 透過字幕動画を P (背景+webm 焼き込み済み) の上に
// ffmpeg の overlay で合成する。描く時間 (renderTransparentSubtitles) とは別に計測する。
//
// 重要: ffmpeg の既定の "vp9" デコーダは VP9 の (BlockAdditional に格納された)
// アルファ側チャンネルを読まず、アルファが全面不透明として扱われて背景が黒く
// 塗りつぶされる (実機検証で確認済み)。overlay 側の入力が VP9 のときは
// 明示的に `-c:v libvpx-vp9` を指定してデコードする必要がある。ProRes 4444 の
// アルファは単一ビットストリーム内の 4 枚目のプレーンなので、既定のデコーダで
// 問題なく読める (指定不要)。
export async function overlayOntoBaseVideo(args: {
  baseVideoPath: string;
  overlayVideoPath: string;
  overlayCodec: "vp9" | "prores";
  outputPath: string;
  durationSec: number;
  condition: ConditionId;
  rep: number;
  concurrency: ConcurrencySetting;
}): Promise<RunRecord> {
  const {
    baseVideoPath,
    overlayVideoPath,
    overlayCodec,
    outputPath,
    durationSec,
    condition,
    rep,
    concurrency,
  } = args;
  await fs.mkdir(path.dirname(outputPath), { recursive: true });

  let error: string | undefined;
  const start = performance.now();
  try {
    await execFileAsync(FFMPEG_BIN, [
      "-y",
      "-hide_banner",
      "-loglevel",
      "error",
      "-i",
      baseVideoPath,
      ...(overlayCodec === "vp9" ? ["-c:v", "libvpx-vp9"] : []),
      "-i",
      overlayVideoPath,
      "-filter_complex",
      "[0:v][1:v]overlay=format=auto",
      "-c:v",
      "libx264",
      "-crf",
      "18",
      "-preset",
      "veryfast",
      "-pix_fmt",
      "yuv420p",
      "-movflags",
      "+faststart",
      outputPath,
    ]);
  } catch (err) {
    const stderr = (err as { stderr?: string }).stderr;
    error = `${(err as Error).message}${stderr ? `\n${stderr}` : ""}`;
  }
  const wallTimeMs = performance.now() - start;
  const outputBytes = error ? null : await statOrNull(outputPath);

  return {
    condition,
    phase: "overlay",
    rep,
    concurrency,
    durationSec,
    fps: FPS,
    width: WIDTH,
    height: HEIGHT,
    wallTimeMs,
    outputPath,
    outputBytes,
    secondsPerSecond: wallTimeMs / 1000 / durationSec,
    timestamp: new Date().toISOString(),
    error,
  };
}

// P (60秒などの短尺) を times 回つないだ長尺動画を作る (ffmpeg concat demuxer、再エンコードなし)。
// 20 分条件の Y / Z の入力に使う。
export async function concatVideo(args: {
  inputPath: string;
  times: number;
  outputPath: string;
}): Promise<void> {
  const { inputPath, times, outputPath } = args;
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const listPath = `${outputPath}.concat-list.txt`;
  const line = `file '${inputPath.replace(/'/g, "'\\''")}'\n`;
  await fs.writeFile(listPath, line.repeat(times));
  await execFileAsync(FFMPEG_BIN, [
    "-y",
    "-hide_banner",
    "-loglevel",
    "error",
    "-f",
    "concat",
    "-safe",
    "0",
    "-i",
    listPath,
    "-c",
    "copy",
    outputPath,
  ]);
  await fs.rm(listPath, { force: true });
}
