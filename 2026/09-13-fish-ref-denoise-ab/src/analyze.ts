// results.jsonl を集計し、セル別統計・Fisher 正確検定 (N vs D, N vs R, R vs D) を
// pooled / 変種別 / 台本別に出して summary.md + summary.json を書く。
// 詳細は README の「手法」節参照。
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fisherExactTest, type FisherResult } from "./lib/fisher";

const OUT_DIR = process.env.OUT_DIR ?? "./output";

type ResultRecord = {
  rep: number;
  ref: string;
  speaker: string;
  variant: string;
  script: "short" | "long";
  cond: "N" | "D" | "R";
  actualDurationSec: number | null;
  overflow: boolean | null;
  ng: boolean | null;
  collapse: boolean | null;
  error: string | null;
};

type CellStats = {
  key: string;
  n: number;
  ngCount: number;
  collapseCount: number;
  overflowCount: number;
  errorCount: number;
  durationMedianSec: number | null;
  durationMaxSec: number | null;
};

function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1]! + sorted[mid]!) / 2 : sorted[mid]!;
}

function summarizeGroup(records: ResultRecord[]): Omit<CellStats, "key"> {
  const n = records.length;
  const ngCount = records.filter((r) => r.ng === true).length;
  const collapseCount = records.filter((r) => r.collapse === true).length;
  const overflowCount = records.filter((r) => r.overflow === true).length;
  const errorCount = records.filter((r) => r.error !== null).length;
  const durations = records
    .map((r) => r.actualDurationSec)
    .filter((d): d is number => d !== null && Number.isFinite(d));
  return {
    n,
    ngCount,
    collapseCount,
    overflowCount,
    errorCount,
    durationMedianSec: median(durations),
    durationMaxSec: durations.length > 0 ? Math.max(...durations) : null,
  };
}

function ngFisher(groupA: ResultRecord[], groupB: ResultRecord[]): FisherResult {
  const aNg = groupA.filter((r) => r.ng === true).length;
  const aOk = groupA.length - aNg;
  const bNg = groupB.filter((r) => r.ng === true).length;
  const bOk = groupB.length - bNg;
  return fisherExactTest(aNg, aOk, bNg, bOk);
}

async function main(): Promise<void> {
  const resultsPath = path.join(OUT_DIR, "results.jsonl");
  const content = await readFile(resultsPath, "utf-8");
  const records: ResultRecord[] = content
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line));

  const conds = ["N", "D", "R"] as const;

  // 1. セル別 (ref x script x cond)
  const cellKeys = new Set<string>();
  for (const r of records) cellKeys.add(`${r.ref}|${r.script}|${r.cond}`);
  const cells: CellStats[] = [...cellKeys].sort().map((key) => {
    const [ref, script, cond] = key.split("|");
    const group = records.filter((r) => r.ref === ref && r.script === script && r.cond === cond);
    return { key, ...summarizeGroup(group) };
  });

  // 2. pooled 全体 (全 ref x script まとめて cond ごと)
  const pooledByCond: Record<string, ResultRecord[]> = {};
  for (const cond of conds) pooledByCond[cond] = records.filter((r) => r.cond === cond);
  const pooledComparisons = {
    N_vs_D: ngFisher(pooledByCond.N!, pooledByCond.D!),
    N_vs_R: ngFisher(pooledByCond.N!, pooledByCond.R!),
    R_vs_D: ngFisher(pooledByCond.R!, pooledByCond.D!),
  };

  // 3. 変種別 (variant ごとに 話者 x 台本 pooled)
  const variants = [...new Set(records.map((r) => r.variant))].sort();
  const byVariant: Record<string, { n: Record<string, number>; comparisons: Record<string, FisherResult> }> = {};
  for (const variant of variants) {
    const byCond: Record<string, ResultRecord[]> = {};
    for (const cond of conds) byCond[cond] = records.filter((r) => r.variant === variant && r.cond === cond);
    byVariant[variant] = {
      n: Object.fromEntries(conds.map((c) => [c, byCond[c]!.length])),
      comparisons: {
        N_vs_D: ngFisher(byCond.N!, byCond.D!),
        N_vs_R: ngFisher(byCond.N!, byCond.R!),
        R_vs_D: ngFisher(byCond.R!, byCond.D!),
      },
    };
  }

  // 4. 台本別 (script ごとに 全 ref pooled)
  const scripts = [...new Set(records.map((r) => r.script))].sort();
  const byScript: Record<string, { n: Record<string, number>; comparisons: Record<string, FisherResult> }> = {};
  for (const script of scripts) {
    const byCond: Record<string, ResultRecord[]> = {};
    for (const cond of conds) byCond[cond] = records.filter((r) => r.script === script && r.cond === cond);
    byScript[script] = {
      n: Object.fromEntries(conds.map((c) => [c, byCond[c]!.length])),
      comparisons: {
        N_vs_D: ngFisher(byCond.N!, byCond.D!),
        N_vs_R: ngFisher(byCond.N!, byCond.R!),
        R_vs_D: ngFisher(byCond.R!, byCond.D!),
      },
    };
  }

  const summary = {
    totalRecords: records.length,
    cells,
    pooled: {
      n: Object.fromEntries(conds.map((c) => [c, pooledByCond[c]!.length])),
      comparisons: pooledComparisons,
    },
    byVariant,
    byScript,
  };

  await writeFile(path.join(OUT_DIR, "summary.json"), JSON.stringify(summary, null, 2), "utf-8");

  const md: string[] = [];
  md.push("# denoise A/B summary");
  md.push("");
  md.push(`total records: ${records.length}`);
  md.push("");
  md.push("## セル別 (ref x script x cond)");
  md.push("");
  md.push("| ref | script | cond | n | ng | collapse | overflow | error | duration median(s) | duration max(s) |");
  md.push("|---|---|---|---|---|---|---|---|---|---|");
  for (const c of cells) {
    const [ref, script, cond] = c.key.split("|");
    md.push(
      `| ${ref} | ${script} | ${cond} | ${c.n} | ${c.ngCount} | ${c.collapseCount} | ${c.overflowCount} | ${c.errorCount} | ${c.durationMedianSec?.toFixed(2) ?? "-"} | ${c.durationMaxSec?.toFixed(2) ?? "-"} |`,
    );
  }
  md.push("");
  md.push("## pooled 全体 (N vs D, N vs R, R vs D)");
  md.push("");
  md.push(`n: N=${summary.pooled.n.N} D=${summary.pooled.n.D} R=${summary.pooled.n.R}`);
  md.push("");
  for (const [label, result] of Object.entries(pooledComparisons)) {
    md.push(
      `- ${label}: a=${result.a} b=${result.b} c=${result.c} d=${result.d} p=${result.pValue.toFixed(6)}`,
    );
  }
  md.push("");
  md.push("## 変種別 (話者2 x 台本2 pooled)");
  md.push("");
  for (const [variant, data] of Object.entries(byVariant)) {
    md.push(`### ${variant}`);
    md.push(`n: N=${data.n.N} D=${data.n.D} R=${data.n.R}`);
    for (const [label, result] of Object.entries(data.comparisons)) {
      md.push(
        `- ${label}: a=${result.a} b=${result.b} c=${result.c} d=${result.d} p=${result.pValue.toFixed(6)}`,
      );
    }
    md.push("");
  }
  md.push("## 台本別 (全 ref pooled)");
  md.push("");
  for (const [script, data] of Object.entries(byScript)) {
    md.push(`### ${script}`);
    md.push(`n: N=${data.n.N} D=${data.n.D} R=${data.n.R}`);
    for (const [label, result] of Object.entries(data.comparisons)) {
      md.push(
        `- ${label}: a=${result.a} b=${result.b} c=${result.c} d=${result.d} p=${result.pValue.toFixed(6)}`,
      );
    }
    md.push("");
  }

  await writeFile(path.join(OUT_DIR, "summary.md"), md.join("\n"), "utf-8");
  console.log(`[analyze] wrote ${path.join(OUT_DIR, "summary.json")} and summary.md`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
