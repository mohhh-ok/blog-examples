import type {
  BundleRecord,
  ConcurrencySetting,
  ConditionId,
  LongRunRecord,
  MachineInfo,
  RunRecord,
} from "./types";
import { concurrencyLabel } from "./types";
import type { MeasureConfig } from "./env";

function median(values: number[]): number | null {
  if (values.length === 0) {
    return null;
  }
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    const a = sorted[mid - 1];
    const b = sorted[mid];
    if (a === undefined || b === undefined) {
      return null;
    }
    return (a + b) / 2;
  }
  return sorted[mid] ?? null;
}

function formatSeconds(ms: number): string {
  return (ms / 1000).toFixed(2);
}

function formatBytes(bytes: number | null): string {
  if (bytes === null) {
    return "n/a";
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KiB`;
  }
  return `${(bytes / 1024 / 1024).toFixed(2)} MiB`;
}

function groupKey(condition: ConditionId, concurrency: ConcurrencySetting): string {
  return `${condition}__${concurrencyLabel(concurrency)}`;
}

function renderRunTable(runs: RunRecord[], phase: "render" | "overlay"): string {
  const filtered = runs.filter((run) => run.phase === phase);
  if (filtered.length === 0) {
    return "(no runs)\n";
  }
  const groups = new Map<string, RunRecord[]>();
  for (const run of filtered) {
    const key = groupKey(run.condition, run.concurrency);
    const list = groups.get(key) ?? [];
    list.push(run);
    groups.set(key, list);
  }

  const lines: string[] = [];
  lines.push("| condition | concurrency | n | wall time (s), raw | median (s) | s/s median | output |");
  lines.push("|---|---|---|---|---|---|---|");
  for (const [, group] of groups) {
    const first = group[0];
    if (!first) {
      continue;
    }
    const rawSeconds = group.map((run) => Number(formatSeconds(run.wallTimeMs)));
    const med = median(rawSeconds);
    const spsValues = group
      .map((run) => run.secondsPerSecond)
      .filter((value): value is number => value !== null);
    const spsMed = median(spsValues);
    const errored = group.filter((run) => run.error).length;
    const outputBytes = group.find((run) => run.outputBytes !== null)?.outputBytes ?? null;
    lines.push(
      `| ${first.condition} | ${concurrencyLabel(first.concurrency)} | ${group.length}${errored > 0 ? ` (${errored} error)` : ""} | ${rawSeconds.join(", ")} | ${med?.toFixed(2) ?? "n/a"} | ${spsMed?.toFixed(3) ?? "n/a"} | ${formatBytes(outputBytes)} |`,
    );
  }
  return `${lines.join("\n")}\n`;
}

function renderZCombinedTable(runs: RunRecord[]): string {
  const zConditions: ConditionId[] = ["Z-vp9", "Z-prores"];
  const lines: string[] = [];
  lines.push("| condition | concurrency | rep | draw (s) | overlay (s) | draw+overlay (s) |");
  lines.push("|---|---|---|---|---|---|");
  for (const condition of zConditions) {
    const renders = runs.filter((run) => run.condition === condition && run.phase === "render");
    const overlays = runs.filter((run) => run.condition === condition && run.phase === "overlay");
    for (const renderRun of renders) {
      const overlayRun = overlays.find(
        (run) => run.rep === renderRun.rep && run.concurrency === renderRun.concurrency,
      );
      const drawSec = Number(formatSeconds(renderRun.wallTimeMs));
      const overlaySec = overlayRun ? Number(formatSeconds(overlayRun.wallTimeMs)) : null;
      const combined = overlaySec !== null ? (drawSec + overlaySec).toFixed(2) : "n/a";
      lines.push(
        `| ${condition} | ${concurrencyLabel(renderRun.concurrency)} | ${renderRun.rep} | ${drawSec.toFixed(2)} | ${overlaySec?.toFixed(2) ?? "n/a"} | ${combined} |`,
      );
    }
  }
  return `${lines.join("\n")}\n`;
}

function renderLongSection(longRecords: LongRunRecord[]): string {
  if (longRecords.length === 0) {
    return "(long-duration runs not executed in this invocation)\n";
  }
  const lines: string[] = [];
  for (const record of longRecords) {
    lines.push(`### ${record.condition} (${record.longMinutes} min)`);
    lines.push("");
    if (!record.ran) {
      lines.push(`実行せず。理由: ${record.reason ?? "(no reason recorded)"}`);
      if (record.extrapolatedSeconds !== undefined) {
        lines.push(`外挿した所要時間: 約 ${(record.extrapolatedSeconds / 60).toFixed(1)} 分`);
      }
      lines.push("");
      continue;
    }
    for (const run of record.runs) {
      lines.push(
        `- ${run.phase}: ${formatSeconds(run.wallTimeMs)}s (s/s=${run.secondsPerSecond?.toFixed(3) ?? "n/a"}, output=${formatBytes(run.outputBytes)}${run.error ? `, ERROR: ${run.error}` : ""})`,
      );
    }
    lines.push("");
  }
  return lines.join("\n");
}

export function buildSummaryMarkdown(args: {
  machineInfo: MachineInfo;
  bundleRecord: BundleRecord | null;
  runs: RunRecord[];
  longRecords: LongRunRecord[];
  config: MeasureConfig;
}): string {
  const { machineInfo, bundleRecord, runs, longRecords, config } = args;

  const lines: string[] = [];
  lines.push("# Remotion 字幕オーバーレイ計測結果");
  lines.push("");
  lines.push(`生成日時: ${new Date().toISOString()}`);
  lines.push("");
  lines.push("## 実行設定");
  lines.push("");
  lines.push(`- duration: ${config.durationSec}s`);
  lines.push(`- reps: ${config.reps}`);
  lines.push(`- conditions: ${config.conditions.join(", ")}`);
  lines.push(`- concurrencies: ${config.concurrencies.map(concurrencyLabel).join(", ")}`);
  lines.push(`- long duration enabled: ${config.longEnabled ? `yes (${config.longMinutes} min)` : "no"}`);
  lines.push("");
  lines.push("## マシン情報");
  lines.push("");
  lines.push(`- CPU: ${machineInfo.cpuModel} (${machineInfo.cpuCount} cores)`);
  lines.push(`- メモリ: ${(machineInfo.totalMemoryBytes / 1024 / 1024 / 1024).toFixed(1)} GiB`);
  lines.push(`- macOS: ${machineInfo.macosVersion}`);
  lines.push(`- bun: ${machineInfo.bunVersion}`);
  lines.push(`- node: ${machineInfo.nodeVersion}`);
  lines.push(`- ffmpeg: ${machineInfo.ffmpegVersion}`);
  lines.push("");
  lines.push("## bundle");
  lines.push("");
  lines.push(bundleRecord ? `${formatSeconds(bundleRecord.wallTimeMs)}s` : "(not recorded)");
  lines.push("");
  lines.push("## render (draw)");
  lines.push("");
  lines.push(renderRunTable(runs, "render"));
  lines.push("## overlay (Z のみ)");
  lines.push("");
  lines.push(renderRunTable(runs, "overlay"));
  lines.push("## Z: 描く時間 + 重ねる時間 (rep 単位)");
  lines.push("");
  lines.push(renderZCombinedTable(runs));
  lines.push(`## 長尺 (${config.longMinutes} 分) の Y / Z / X`);
  lines.push("");
  lines.push(renderLongSection(longRecords));

  return lines.join("\n");
}
