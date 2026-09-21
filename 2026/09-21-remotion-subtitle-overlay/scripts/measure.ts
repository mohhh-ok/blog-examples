// 1 コマンドで通す本体: 素材生成 → bundle → 各条件 (X/X-video/P/W/Y/Z-vp9/Z-prores) を
// n 回 → (指定時のみ) 長尺 → フレーム比較 → results/*.json + results/summary.md。
//
// duration・reps・conditions・concurrency は CLI 引数 (--duration=60 等) か
// 同名の環境変数 (DURATION_SEC 等) で上書きできる (scripts/lib/env.ts 参照)。
// 既定値が本番の計測 (60秒・n=3・全条件・concurrency 1,default)。

import path from "node:path";
import { loadMeasureConfig } from "./lib/env";
import { collectMachineInfo } from "./lib/machineInfo";
import { ResultsStore } from "./lib/resultsStore";
import { bundleOnce, openSharedBrowser, closeSharedBrowser } from "./lib/remotionRunner";
import { runMainPipeline, runLongPipeline } from "./lib/pipeline";
import { buildSummaryMarkdown } from "./lib/summary";
import { generateAssets } from "./generate-assets";
import { extractFrameFromVideo } from "./extract-frames";
import { ASSET_LOOP_DURATION_SEC } from "../src/constants";
import type { ConditionId } from "./lib/types";

const FRAME_COMPARISON_CONDITIONS: readonly ConditionId[] = [
  "X",
  "X-video",
  "P",
  "W",
  "Y",
  "Z-vp9",
  "Z-prores",
];

async function extractComparisonFrames(args: {
  store: ResultsStore;
  outDir: string;
  frameTimestampSec: number;
}): Promise<void> {
  const { store, outDir, frameTimestampSec } = args;
  const allRuns = store.getAllRuns();
  const framesDir = path.join(outDir, "frames");

  for (const condition of FRAME_COMPARISON_CONDITIONS) {
    const wantedPhase = condition === "Z-vp9" || condition === "Z-prores" ? "overlay" : "render";
    const candidates = allRuns.filter(
      (run) =>
        run.condition === condition &&
        run.phase === wantedPhase &&
        !run.error &&
        run.outputBytes !== null,
    );
    const chosen = candidates[candidates.length - 1];
    if (!chosen) {
      console.log(`[measure] no successful output for ${condition}, skipping frame extraction`);
      continue;
    }
    const outputPngPath = path.join(framesDir, `${condition.toLowerCase()}.png`);
    console.log(`[measure] extracting frame for ${condition} @ ${frameTimestampSec}s -> ${outputPngPath}`);
    await extractFrameFromVideo({
      videoPath: chosen.outputPath,
      timestampSec: frameTimestampSec,
      outputPngPath,
    });
  }
}

async function main(): Promise<void> {
  const config = loadMeasureConfig();
  console.log("[measure] config", config);

  await generateAssets({ assetsDir: config.assetsDir, durationSec: ASSET_LOOP_DURATION_SEC });

  const store = new ResultsStore(config.outDir);
  await store.init();

  const machineInfo = collectMachineInfo();
  await store.writeMachineInfo(machineInfo);

  console.log("[measure] bundling ...");
  const { bundleLocation, wallTimeMs: bundleWallTimeMs } = await bundleOnce();
  await store.setBundleRecord({
    phase: "bundle",
    wallTimeMs: bundleWallTimeMs,
    timestamp: new Date().toISOString(),
  });
  console.log(`[measure] bundle done in ${(bundleWallTimeMs / 1000).toFixed(1)}s -> ${bundleLocation}`);

  // ブラウザは計測全体で 1 つを使い回す (フォント再ダウンロードを避けるため。
  // scripts/lib/remotionRunner.ts の openSharedBrowser 参照)。
  console.log("[measure] opening shared browser ...");
  const puppeteerInstance = await openSharedBrowser();
  try {
    const { pOutputForDependents } = await runMainPipeline({
      config,
      bundleLocation,
      store,
      puppeteerInstance,
    });

    const xSpsValues = store
      .getAllRuns()
      .filter((run) => run.condition === "X" && run.phase === "render" && !run.error)
      .map((run) => run.secondsPerSecond)
      .filter((value): value is number => value !== null)
      .sort((a, b) => a - b);
    const xMedianSecondsPerSecond =
      xSpsValues.length > 0 ? (xSpsValues[Math.floor(xSpsValues.length / 2)] ?? null) : null;

    await runLongPipeline({
      config,
      bundleLocation,
      store,
      pOutputForDependents,
      xMedianSecondsPerSecond,
      puppeteerInstance,
    });
  } finally {
    await closeSharedBrowser(puppeteerInstance);
  }

  await extractComparisonFrames({ store, outDir: config.outDir, frameTimestampSec: config.frameTimestampSec });

  const summaryMarkdown = buildSummaryMarkdown({
    machineInfo,
    bundleRecord: store.getBundleRecord(),
    runs: store.getAllRuns(),
    longRecords: store.getLongRecords(),
    config,
  });
  await store.writeSummaryMarkdown(summaryMarkdown);

  console.log(`[measure] all done. results in ${config.outDir}`);
}

main().catch((error: unknown) => {
  console.error("[measure] failed", error);
  process.exit(1);
});
