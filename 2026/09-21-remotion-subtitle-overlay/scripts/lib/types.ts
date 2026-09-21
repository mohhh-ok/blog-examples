export type ConditionId = "X" | "X-video" | "P" | "W" | "Y" | "Z-vp9" | "Z-prores";

export const ALL_CONDITIONS: readonly ConditionId[] = [
  "X",
  "X-video",
  "P",
  "W",
  "Y",
  "Z-vp9",
  "Z-prores",
];

export type ConcurrencySetting = "default" | number;

export function concurrencyLabel(concurrency: ConcurrencySetting): string {
  return concurrency === "default" ? "default" : String(concurrency);
}

export type RunRecord = {
  condition: ConditionId;
  phase: "render" | "overlay";
  rep: number;
  concurrency: ConcurrencySetting;
  durationSec: number;
  fps: number;
  width: number;
  height: number;
  wallTimeMs: number;
  outputPath: string;
  outputBytes: number | null;
  secondsPerSecond: number | null;
  browserLogs?: string[];
  notes?: string[];
  timestamp: string;
  error?: string;
};

export type BundleRecord = {
  phase: "bundle";
  wallTimeMs: number;
  timestamp: string;
};

export type LongRunRecord = {
  condition: ConditionId;
  longMinutes: number;
  ran: boolean;
  reason?: string;
  extrapolatedSeconds?: number;
  runs: RunRecord[];
};

export type MachineInfo = {
  platform: string;
  arch: string;
  cpuModel: string;
  cpuCount: number;
  totalMemoryBytes: number;
  macosVersion: string;
  bunVersion: string;
  nodeVersion: string;
  ffmpegVersion: string;
  collectedAt: string;
};
