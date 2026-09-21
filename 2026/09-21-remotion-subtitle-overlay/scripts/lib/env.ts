import path from "node:path";
import { ALL_CONDITIONS, type ConcurrencySetting, type ConditionId } from "./types";

const LONG_CAPABLE_CONDITIONS = ["Y", "Z-vp9", "Z-prores"] as const;
type LongCapableConditionId = (typeof LONG_CAPABLE_CONDITIONS)[number];

export type MeasureConfig = {
  durationSec: number;
  reps: number;
  conditions: ConditionId[];
  concurrencies: ConcurrencySetting[];
  outDir: string;
  assetsDir: string;
  renderDir: string;
  longEnabled: boolean;
  longMinutes: number;
  // 20分パイプラインで実行する条件 (Y/Z-vp9/Z-prores の部分集合)。X は別枠
  // (60秒実測からの外挿判定) なのでここには含まれない。既定は3つとも実行
  // (これまでの挙動を変えない)。
  longConditions: LongCapableConditionId[];
  frameTimestampSec: number;
};

function parseArgs(): Record<string, string> {
  const out: Record<string, string> = {};
  for (const arg of process.argv.slice(2)) {
    const match = /^--([^=]+)=(.*)$/.exec(arg);
    if (match?.[1] !== undefined && match[2] !== undefined) {
      out[match[1]] = match[2];
    }
  }
  return out;
}

function pick(args: Record<string, string>, argKey: string, envKey: string, fallback: string): string {
  return args[argKey] ?? process.env[envKey] ?? fallback;
}

function parseConditions(raw: string): ConditionId[] {
  const parsed = raw
    .split(",")
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0);
  for (const entry of parsed) {
    if (!ALL_CONDITIONS.includes(entry as ConditionId)) {
      throw new Error(
        `unknown condition "${entry}". valid conditions: ${ALL_CONDITIONS.join(", ")}`,
      );
    }
  }
  return parsed as ConditionId[];
}

function parseLongConditions(raw: string): LongCapableConditionId[] {
  const parsed = raw
    .split(",")
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0);
  for (const entry of parsed) {
    if (!LONG_CAPABLE_CONDITIONS.includes(entry as LongCapableConditionId)) {
      throw new Error(
        `unknown long condition "${entry}". valid: ${LONG_CAPABLE_CONDITIONS.join(", ")}`,
      );
    }
  }
  return parsed as LongCapableConditionId[];
}

function parseConcurrencies(raw: string): ConcurrencySetting[] {
  return raw
    .split(",")
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0)
    .map((entry) => {
      if (entry === "default") {
        return "default" as const;
      }
      const value = Number(entry);
      if (!Number.isInteger(value) || value <= 0) {
        throw new Error(`invalid concurrency value "${entry}" (expected a positive integer or "default")`);
      }
      return value;
    });
}

export function loadMeasureConfig(): MeasureConfig {
  const args = parseArgs();

  const durationSec = Number(pick(args, "duration", "DURATION_SEC", "60"));
  if (!Number.isFinite(durationSec) || durationSec <= 0) {
    throw new Error(`invalid --duration / DURATION_SEC: ${durationSec}`);
  }

  const reps = Number(pick(args, "reps", "REPS", "3"));
  if (!Number.isInteger(reps) || reps <= 0) {
    throw new Error(`invalid --reps / REPS: ${reps}`);
  }

  const conditions = parseConditions(pick(args, "conditions", "CONDITIONS", ALL_CONDITIONS.join(",")));
  const concurrencies = parseConcurrencies(pick(args, "concurrency", "CONCURRENCIES", "1,default"));

  const outDir = path.resolve(
    pick(args, "out-dir", "OUT_DIR", path.join(import.meta.dir, "..", "..", "results")),
  );
  const assetsDir = path.resolve(pick(args, "assets-dir", "ASSETS_DIR", "/tmp/blog-examples/assets"));
  const renderDir = path.resolve(pick(args, "render-dir", "RENDER_DIR", "/tmp/blog-examples/out"));

  const longEnabled = pick(args, "long", "LONG", "0") === "1";
  const longMinutes = Number(pick(args, "long-minutes", "LONG_MINUTES", "20"));
  if (!Number.isFinite(longMinutes) || longMinutes <= 0) {
    throw new Error(`invalid --long-minutes / LONG_MINUTES: ${longMinutes}`);
  }
  const longConditions = parseLongConditions(
    pick(args, "long-conditions", "LONG_CONDITIONS", LONG_CAPABLE_CONDITIONS.join(",")),
  );

  const frameTimestampSec = Math.min(2, durationSec * 0.4);

  return {
    durationSec,
    reps,
    conditions,
    concurrencies,
    outDir,
    assetsDir,
    renderDir,
    longEnabled,
    longMinutes,
    longConditions,
    frameTimestampSec,
  };
}
