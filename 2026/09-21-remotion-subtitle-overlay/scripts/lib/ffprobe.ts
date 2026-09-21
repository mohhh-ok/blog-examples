import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

// 既定は PATH 上の ffprobe を使う (Homebrew/apt どちらでも動く)。別の場所にある
// 場合だけ FFPROBE_BIN で上書きする。
const FFPROBE_BIN = process.env["FFPROBE_BIN"] ?? "ffprobe";

export type FfprobeStream = Record<string, unknown> & {
  codec_type?: string;
  pix_fmt?: string;
  codec_name?: string;
  tags?: Record<string, string>;
};

export type FfprobeResult = {
  format: Record<string, unknown>;
  streams: FfprobeStream[];
};

export async function ffprobe(filePath: string): Promise<FfprobeResult> {
  const { stdout } = await execFileAsync(FFPROBE_BIN, [
    "-v",
    "error",
    "-print_format",
    "json",
    "-show_format",
    "-show_streams",
    filePath,
  ]);
  return JSON.parse(stdout) as FfprobeResult;
}

export async function ffprobeRaw(filePath: string): Promise<string> {
  const { stdout } = await execFileAsync(FFPROBE_BIN, [
    "-v",
    "error",
    "-print_format",
    "json",
    "-show_format",
    "-show_streams",
    filePath,
  ]);
  return stdout;
}
