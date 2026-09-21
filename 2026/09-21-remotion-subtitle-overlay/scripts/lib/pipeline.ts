import path from "node:path";
import type { HeadlessBrowser } from "@remotion/renderer";
import type { SceneProps } from "../../src/compositions/Scene";
import { BACKGROUND_FILENAME, FIGURE_FILENAME } from "../generate-assets";
import { copyIntoServedDir } from "./servedAssets";
import {
  concatVideo,
  overlayOntoBaseVideo,
  renderScene,
  renderTransparentSubtitles,
} from "./remotionRunner";
import type { ResultsStore } from "./resultsStore";
import { concurrencyLabel, type ConditionId, type LongRunRecord } from "./types";
import type { MeasureConfig } from "./env";

const ORDERED_CONDITIONS: readonly ConditionId[] = [
  "P",
  "W",
  "X",
  "X-video",
  "Y",
  "Z-vp9",
  "Z-prores",
];

function buildSceneProps(args: {
  condition: ConditionId;
  durationSec: number;
  backgroundUrl: string;
  figureUrl: string;
  bakedVideoUrl?: string;
}): SceneProps {
  const { condition, durationSec, backgroundUrl, figureUrl, bakedVideoUrl } = args;
  switch (condition) {
    case "X":
      return { durationSec, backgroundUrl, figureUrl, figureMode: "offthread", showSubtitles: true };
    case "X-video":
      return { durationSec, backgroundUrl, figureUrl, figureMode: "media", showSubtitles: true };
    case "P":
      return { durationSec, backgroundUrl, figureUrl, figureMode: "offthread", showSubtitles: false };
    case "W":
      return { durationSec, backgroundUrl, showSubtitles: true };
    case "Y":
      if (!bakedVideoUrl) {
        throw new Error("buildSceneProps: Y requires bakedVideoUrl");
      }
      return { durationSec, bakedVideoUrl, showSubtitles: true };
    default:
      throw new Error(`buildSceneProps: unsupported condition ${condition}`);
  }
}

function renderOutputPath(args: {
  renderDir: string;
  condition: ConditionId;
  concurrency: string;
  rep: number;
  durationSec: number;
}): string {
  const { renderDir, condition, concurrency, rep, durationSec } = args;
  const safeCondition = condition.toLowerCase();
  return path.join(renderDir, `${safeCondition}_d${durationSec}_c${concurrency}_r${rep}.mp4`);
}

export async function runMainPipeline(args: {
  config: MeasureConfig;
  bundleLocation: string;
  store: ResultsStore;
  puppeteerInstance: HeadlessBrowser;
}): Promise<{ pOutputForDependents: string | null }> {
  const { config, bundleLocation, store, puppeteerInstance } = args;
  const backgroundUrl = await copyIntoServedDir({
    bundleLocation,
    sourcePath: path.join(config.assetsDir, BACKGROUND_FILENAME),
  });
  const figureUrl = await copyIntoServedDir({
    bundleLocation,
    sourcePath: path.join(config.assetsDir, FIGURE_FILENAME),
  });

  const requested = new Set(config.conditions);
  const needsPInput = requested.has("Y") || requested.has("Z-vp9") || requested.has("Z-prores");

  let pOutputForDependents: string | null = null;
  let pOutputServedUrl: string | null = null;

  if (needsPInput) {
    console.log("[measure] preparing P output as the input for Y/Z ...");
    const prepPath = path.join(config.renderDir, `p-input-for-dependents_d${config.durationSec}.mp4`);
    const sceneProps = buildSceneProps({
      condition: "P",
      durationSec: config.durationSec,
      backgroundUrl,
      figureUrl,
    });
    const record = await renderScene({
      bundleLocation,
      outputPath: prepPath,
      durationSec: config.durationSec,
      concurrency: "default",
      sceneProps,
      condition: "P",
      rep: 0,
      puppeteerInstance,
    });
    if (record.error) {
      throw new Error(`failed to prepare P input for Y/Z: ${record.error}`);
    }
    pOutputForDependents = prepPath;
    pOutputServedUrl = await copyIntoServedDir({ bundleLocation, sourcePath: prepPath });
    console.log(`[measure] P input ready -> ${prepPath} (served as ${pOutputServedUrl})`);
  }

  const orderedRequested = ORDERED_CONDITIONS.filter((condition) => requested.has(condition));

  for (const condition of orderedRequested) {
    for (const concurrency of config.concurrencies) {
      for (let rep = 1; rep <= config.reps; rep += 1) {
        console.log(
          `[measure] start ${condition} concurrency=${concurrencyLabel(concurrency)} rep=${rep}/${config.reps}`,
        );

        const outputPath = renderOutputPath({
          renderDir: config.renderDir,
          condition,
          concurrency: concurrencyLabel(concurrency),
          rep,
          durationSec: config.durationSec,
        });

        if (condition === "Z-vp9" || condition === "Z-prores") {
          const codec = condition === "Z-vp9" ? "vp9" : "prores";
          const drawExt = codec === "vp9" ? "webm" : "mov";
          const drawPath = outputPath.replace(/\.mp4$/, `.${drawExt}`);
          const drawRecord = await renderTransparentSubtitles({
            bundleLocation,
            outputPath: drawPath,
            durationSec: config.durationSec,
            concurrency,
            codec,
            condition,
            rep,
            puppeteerInstance,
          });
          await store.addRun(drawRecord);
          if (!drawRecord.error) {
            if (!pOutputForDependents) {
              throw new Error("internal error: P input missing for Z overlay");
            }
            const overlayRecord = await overlayOntoBaseVideo({
              baseVideoPath: pOutputForDependents,
              overlayVideoPath: drawPath,
              overlayCodec: codec,
              outputPath,
              durationSec: config.durationSec,
              condition,
              rep,
              concurrency,
            });
            await store.addRun(overlayRecord);
            console.log(
              `[measure] done  ${condition} draw=${drawRecord.wallTimeMs.toFixed(0)}ms overlay=${overlayRecord.wallTimeMs.toFixed(0)}ms error=${overlayRecord.error ?? "none"}`,
            );
          } else {
            console.log(`[measure] done  ${condition} FAILED at draw step: ${drawRecord.error}`);
          }
          continue;
        }

        const sceneProps = buildSceneProps({
          condition,
          durationSec: config.durationSec,
          backgroundUrl,
          figureUrl,
          bakedVideoUrl: condition === "Y" && pOutputServedUrl ? pOutputServedUrl : undefined,
        });
        const record = await renderScene({
          bundleLocation,
          outputPath,
          durationSec: config.durationSec,
          concurrency,
          sceneProps,
          condition,
          rep,
          puppeteerInstance,
        });
        await store.addRun(record);
        console.log(
          `[measure] done  ${condition} concurrency=${concurrencyLabel(concurrency)} rep=${rep}/${config.reps} wallTimeMs=${record.wallTimeMs.toFixed(0)} error=${record.error ?? "none"}`,
        );
      }
    }
  }

  return { pOutputForDependents };
}

export async function runLongPipeline(args: {
  config: MeasureConfig;
  bundleLocation: string;
  store: ResultsStore;
  pOutputForDependents: string | null;
  xMedianSecondsPerSecond: number | null;
  puppeteerInstance: HeadlessBrowser;
}): Promise<void> {
  const {
    config,
    bundleLocation,
    store,
    pOutputForDependents,
    xMedianSecondsPerSecond,
    puppeteerInstance,
  } = args;
  if (!config.longEnabled) {
    return;
  }

  const longDurationSec = config.longMinutes * 60;
  const backgroundUrl = await copyIntoServedDir({
    bundleLocation,
    sourcePath: path.join(config.assetsDir, BACKGROUND_FILENAME),
  });
  const figureUrl = await copyIntoServedDir({
    bundleLocation,
    sourcePath: path.join(config.assetsDir, FIGURE_FILENAME),
  });

  let pBasePath = pOutputForDependents;
  if (!pBasePath) {
    console.log("[measure][long] rendering P (60s) to build the looped input");
    const prepPath = path.join(config.renderDir, "p-input-for-long.mp4");
    const sceneProps = buildSceneProps({ condition: "P", durationSec: 60, backgroundUrl, figureUrl });
    const record = await renderScene({
      bundleLocation,
      outputPath: prepPath,
      durationSec: 60,
      concurrency: "default",
      sceneProps,
      condition: "P",
      rep: 0,
      puppeteerInstance,
    });
    if (record.error) {
      throw new Error(`failed to render P for long pipeline: ${record.error}`);
    }
    pBasePath = prepPath;
  }

  console.log(`[measure][long] concatenating P x${config.longMinutes} ...`);
  const p20Path = path.join(config.renderDir, `p-looped-${config.longMinutes}min.mp4`);
  const concatStart = performance.now();
  await concatVideo({ inputPath: pBasePath, times: config.longMinutes, outputPath: p20Path });
  console.log(`[measure][long] concat done in ${((performance.now() - concatStart) / 1000).toFixed(1)}s`);
  const p20ServedUrl = await copyIntoServedDir({ bundleLocation, sourcePath: p20Path });

  const longRecords: LongRunRecord[] = [];

  if (config.longConditions.includes("Y")) {
    console.log(`[measure][long] start Y (${config.longMinutes} min)`);
    const ySceneProps = buildSceneProps({
      condition: "Y",
      durationSec: longDurationSec,
      backgroundUrl,
      figureUrl,
      bakedVideoUrl: p20ServedUrl,
    });
    const yOutputPath = path.join(config.renderDir, `y_long_${config.longMinutes}min.mp4`);
    const yRecord = await renderScene({
      bundleLocation,
      outputPath: yOutputPath,
      durationSec: longDurationSec,
      concurrency: "default",
      sceneProps: ySceneProps,
      condition: "Y",
      rep: 1,
      puppeteerInstance,
    });
    longRecords.push({ condition: "Y", longMinutes: config.longMinutes, ran: true, runs: [yRecord] });
    console.log(`[measure][long] done  Y wallTimeMs=${yRecord.wallTimeMs.toFixed(0)} error=${yRecord.error ?? "none"}`);
  } else {
    longRecords.push({
      condition: "Y",
      longMinutes: config.longMinutes,
      ran: false,
      reason: "LONG_CONDITIONS で指定されなかったため実行せず",
      runs: [],
    });
  }

  const zLongConditions = (["Z-vp9", "Z-prores"] as const).filter((condition) =>
    config.longConditions.includes(condition),
  );
  const zSkippedConditions = (["Z-vp9", "Z-prores"] as const).filter(
    (condition) => !config.longConditions.includes(condition),
  );
  for (const condition of zSkippedConditions) {
    longRecords.push({
      condition,
      longMinutes: config.longMinutes,
      ran: false,
      reason: "LONG_CONDITIONS で指定されなかったため実行せず",
      runs: [],
    });
  }

  for (const condition of zLongConditions) {
    console.log(`[measure][long] start ${condition} (${config.longMinutes} min)`);
    const codec = condition === "Z-vp9" ? "vp9" : "prores";
    const drawExt = codec === "vp9" ? "webm" : "mov";
    const drawPath = path.join(config.renderDir, `${condition.toLowerCase()}_long_draw.${drawExt}`);
    const drawRecord = await renderTransparentSubtitles({
      bundleLocation,
      outputPath: drawPath,
      durationSec: longDurationSec,
      concurrency: "default",
      codec,
      condition,
      rep: 1,
      puppeteerInstance,
    });
    const runs = [drawRecord];
    if (!drawRecord.error) {
      const overlayPath = path.join(config.renderDir, `${condition.toLowerCase()}_long.mp4`);
      const overlayRecord = await overlayOntoBaseVideo({
        baseVideoPath: p20Path,
        overlayVideoPath: drawPath,
        overlayCodec: codec,
        outputPath: overlayPath,
        durationSec: longDurationSec,
        condition,
        rep: 1,
        concurrency: "default",
      });
      runs.push(overlayRecord);
    }
    longRecords.push({ condition, longMinutes: config.longMinutes, ran: true, runs });
    console.log(`[measure][long] done  ${condition}`);
  }

  const projectedSeconds =
    xMedianSecondsPerSecond !== null ? xMedianSecondsPerSecond * longDurationSec : null;
  if (projectedSeconds === null) {
    longRecords.push({
      condition: "X",
      longMinutes: config.longMinutes,
      ran: false,
      reason: "X の 60 秒実測がないため外挿できない (conditions に X を含めて先に実行すること)",
      runs: [],
    });
  } else if (projectedSeconds > 3600) {
    const medianSps = xMedianSecondsPerSecond ?? 0;
    longRecords.push({
      condition: "X",
      longMinutes: config.longMinutes,
      ran: false,
      reason: `60秒実測の秒/秒中央値 (${medianSps.toFixed(3)}) から外挿すると約 ${(projectedSeconds / 60).toFixed(1)} 分かかる見込みのため実行しない (1時間超)`,
      extrapolatedSeconds: projectedSeconds,
      runs: [],
    });
  } else {
    console.log(
      `[measure][long] start X (${config.longMinutes} min) — projected ${(projectedSeconds / 60).toFixed(1)} min, running for real`,
    );
    const xSceneProps = buildSceneProps({
      condition: "X",
      durationSec: longDurationSec,
      backgroundUrl,
      figureUrl,
    });
    const xOutputPath = path.join(config.renderDir, `x_long_${config.longMinutes}min.mp4`);
    const xRecord = await renderScene({
      bundleLocation,
      outputPath: xOutputPath,
      durationSec: longDurationSec,
      concurrency: "default",
      sceneProps: xSceneProps,
      condition: "X",
      rep: 1,
      puppeteerInstance,
    });
    longRecords.push({ condition: "X", longMinutes: config.longMinutes, ran: true, runs: [xRecord] });
    console.log(`[measure][long] done  X wallTimeMs=${xRecord.wallTimeMs.toFixed(0)} error=${xRecord.error ?? "none"}`);
  }

  await store.setLongRecords(longRecords);
}
