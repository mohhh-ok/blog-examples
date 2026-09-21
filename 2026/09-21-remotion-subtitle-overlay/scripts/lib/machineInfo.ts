import os from "node:os";
import { execFileSync } from "node:child_process";
import type { MachineInfo } from "./types";

function safeExec(cmd: string, args: string[]): string {
  try {
    return execFileSync(cmd, args, { encoding: "utf8" }).trim();
  } catch (error) {
    return `unavailable (${(error as Error).message})`;
  }
}

// OS のバージョン文字列。macOS では sw_vers、Linux では /etc/os-release の
// PRETTY_NAME を使う。どちらも取れなければ os.release() にフォールバックする。
function osVersionString(): string {
  if (os.platform() === "darwin") {
    return safeExec("sw_vers", ["-productVersion"]);
  }
  try {
    return execFileSync(
      "sh",
      ["-c", "grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '\"'"],
      { encoding: "utf8" },
    ).trim();
  } catch {
    return os.release();
  }
}

export function collectMachineInfo(): MachineInfo {
  const cpus = os.cpus();
  const ffmpegBin = process.env["FFMPEG_BIN"] ?? "ffmpeg";
  const ffmpegVersionOutput = safeExec(ffmpegBin, ["-version"]);
  const ffmpegFirstLine = ffmpegVersionOutput.split("\n")[0] ?? ffmpegVersionOutput;

  return {
    platform: os.platform(),
    arch: os.arch(),
    cpuModel: cpus[0]?.model ?? "unknown",
    cpuCount: cpus.length,
    totalMemoryBytes: os.totalmem(),
    macosVersion: osVersionString(),
    bunVersion: safeExec("bun", ["--version"]),
    nodeVersion: safeExec("node", ["--version"]),
    ffmpegVersion: ffmpegFirstLine,
    collectedAt: new Date().toISOString(),
  };
}
