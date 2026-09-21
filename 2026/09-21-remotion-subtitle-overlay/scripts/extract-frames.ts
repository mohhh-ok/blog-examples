import { execFile } from "node:child_process";
import { promisify } from "node:util";
import fs from "node:fs/promises";
import path from "node:path";

const execFileAsync = promisify(execFile);
// 既定は PATH 上の ffmpeg を使う (Homebrew/apt どちらでも動く)。別の場所にある
// 場合だけ FFMPEG_BIN で上書きする。
const FFMPEG_BIN = process.env["FFMPEG_BIN"] ?? "ffmpeg";

// -ss を -i の後ろに置く (正確シーク)。今回の素材は短尺で本数も少ないため、
// 高速シークの keyframe ずれより正確さを優先する。
export async function extractFrameFromVideo(args: {
  videoPath: string;
  timestampSec: number;
  outputPngPath: string;
}): Promise<void> {
  const { videoPath, timestampSec, outputPngPath } = args;
  await fs.mkdir(path.dirname(outputPngPath), { recursive: true });
  await execFileAsync(FFMPEG_BIN, [
    "-y",
    "-hide_banner",
    "-loglevel",
    "error",
    "-i",
    videoPath,
    "-ss",
    String(timestampSec),
    "-frames:v",
    "1",
    outputPngPath,
  ]);
}

if (import.meta.main) {
  const videoPath = process.env["VIDEO_PATH"];
  const timestampSec = Number(process.env["TIMESTAMP_SEC"] ?? "2");
  const outputPngPath = process.env["OUTPUT_PATH"];
  if (!videoPath || !outputPngPath) {
    console.error(
      "usage: VIDEO_PATH=<file> OUTPUT_PATH=<png> [TIMESTAMP_SEC=2] bun run scripts/extract-frames.ts",
    );
    process.exit(1);
  }
  extractFrameFromVideo({ videoPath, timestampSec, outputPngPath })
    .then(() => {
      console.log(`[frames] wrote ${outputPngPath}`);
    })
    .catch((error: unknown) => {
      console.error("[frames] failed", error);
      process.exit(1);
    });
}
