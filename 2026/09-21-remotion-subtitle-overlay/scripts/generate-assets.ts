// 背景動画・透過 webm (人物の代わりの図形) をすべて ffmpeg の合成だけで作る。
// 人物動画の取得や matting は行わない。
//
// - background.mp4: 動くグラデーション (ffmpeg の gradients ソースフィルタ)
// - figure.webm:     画面の 1/3〜1/2 程度を占める、縁がフェザーされた半透明の円が
//                     リサージュ曲線状に動く図形。geq フィルタで RGBA を直接計算し、
//                     VP9 + yuva420p でエンコードする。

import { execFile } from "node:child_process";
import { promisify } from "node:util";
import fs from "node:fs/promises";
import path from "node:path";
import { ffprobe } from "./lib/ffprobe";

const execFileAsync = promisify(execFile);

// 既定は PATH 上の ffmpeg を使う (Homebrew/apt どちらでも動く)。別の場所にある
// 場合だけ FFMPEG_BIN で上書きする。
const FFMPEG_BIN = process.env["FFMPEG_BIN"] ?? "ffmpeg";

const WIDTH = 1080;
const HEIGHT = 1920;
const FPS = 30;

export const BACKGROUND_FILENAME = "background.mp4";
export const FIGURE_FILENAME = "figure.webm";

async function runFfmpeg(args: string[]): Promise<void> {
  try {
    await execFileAsync(FFMPEG_BIN, ["-y", "-hide_banner", "-loglevel", "error", ...args]);
  } catch (error) {
    const stderr = (error as { stderr?: string }).stderr;
    throw new Error(`ffmpeg failed: ${(error as Error).message}\n${stderr ?? ""}`);
  }
}

async function fileDurationMatches(filePath: string, expectedDurationSec: number): Promise<boolean> {
  try {
    const probed = await ffprobe(filePath);
    const durationRaw = probed.format["duration"];
    const duration = typeof durationRaw === "string" ? Number(durationRaw) : NaN;
    return Number.isFinite(duration) && Math.abs(duration - expectedDurationSec) < 0.5;
  } catch {
    return false;
  }
}

async function generateBackground(args: { outputPath: string; durationSec: number }): Promise<void> {
  const { outputPath, durationSec } = args;
  // 動くグラデーション。2 色の帯がゆっくり回転する程度の合成背景。
  // seed を固定し、生成のたびに絵が変わらないようにする (再現性のため)。
  const gradients = `gradients=size=${WIDTH}x${HEIGHT}:rate=${FPS}:duration=${durationSec}:speed=0.03:nb_colors=3:c0=0x14213d:c1=0x274472:c2=0x0d1b2a:seed=42`;
  await runFfmpeg([
    "-f",
    "lavfi",
    "-i",
    gradients,
    "-t",
    String(durationSec),
    "-pix_fmt",
    "yuv420p",
    "-c:v",
    "libx264",
    "-crf",
    "18",
    "-preset",
    "veryfast",
    "-movflags",
    "+faststart",
    outputPath,
  ]);
}

async function generateFigure(args: { outputPath: string; durationSec: number }): Promise<void> {
  const { outputPath, durationSec } = args;

  // 画面の 1/3〜1/2 ほどを占める円。中心をリサージュ曲線で動かし、
  // 縁を FEATHER px でフェザーして半透明のアンチエイリアス部分を作る。
  const radius = 260; // 直径 520px, 画面幅 1080px の約48%
  const feather = 60;
  const centerX = `(${WIDTH / 2}+300*sin(2*PI*(N/${FPS})/13))`;
  const centerY = `(${HEIGHT / 2}+480*cos(2*PI*(N/${FPS})/17))`;
  const dist = `hypot(X-${centerX},Y-${centerY})`;
  const alphaExpr = `min(255,max(0,255*((${radius}+${feather}-${dist})/${feather})))`;

  // format=rgba を geq の前に挟まないと、geq がアルファ非対応のピクセルフォーマットを
  // 選んでしまい a_expr が無視される (中間フレームで確認済み)。
  const geq = `format=rgba,geq=r=210:g=95:b=55:a='${alphaExpr}'`;

  // 注意: `-b:v 0` (無制限 Constant Quality) を付けると、ffmpeg 自身の
  // libvpx-vp9 デコーダ (`-c:v libvpx-vp9` 明示指定時) では正しく読めるのに
  // Remotion の OffthreadVideo (内部の Rust コンポジタ) 経由だとアルファが
  // 全面 0 (透明) として扱われ図形が消えることを実機で確認した
  // (docs 未記載、smoke テストで発見)。Remotion 自身が VP9 アルファを書き出す
  // ときの内部 ffmpeg 呼び出し (`-crf 28` のみ、`-b:v` 指定なし) に倣い、
  // ここでも `-b:v` を付けず `-crf` だけを使う (Constrained Quality)。
  await runFfmpeg([
    "-f",
    "lavfi",
    "-i",
    `color=size=${WIDTH}x${HEIGHT}:rate=${FPS}:duration=${durationSec}:color=black`,
    "-vf",
    geq,
    "-t",
    String(durationSec),
    "-pix_fmt",
    "yuva420p",
    "-c:v",
    "libvpx-vp9",
    "-crf",
    "32",
    "-cpu-used",
    "4",
    "-auto-alt-ref",
    "0",
    outputPath,
  ]);
}

export async function generateAssets(args: {
  assetsDir: string;
  durationSec: number;
  force?: boolean;
}): Promise<{ backgroundPath: string; figurePath: string }> {
  const { assetsDir, durationSec, force = false } = args;
  await fs.mkdir(assetsDir, { recursive: true });

  const backgroundPath = path.join(assetsDir, BACKGROUND_FILENAME);
  const figurePath = path.join(assetsDir, FIGURE_FILENAME);

  const backgroundOk = !force && (await fileDurationMatches(backgroundPath, durationSec));
  if (backgroundOk) {
    console.log(`[assets] background already up to date: ${backgroundPath}`);
  } else {
    console.log(`[assets] generating background (${durationSec}s) -> ${backgroundPath}`);
    await generateBackground({ outputPath: backgroundPath, durationSec });
    console.log(`[assets] background done`);
  }

  const figureOk = !force && (await fileDurationMatches(figurePath, durationSec));
  if (figureOk) {
    console.log(`[assets] figure already up to date: ${figurePath}`);
  } else {
    console.log(`[assets] generating figure webm (${durationSec}s) -> ${figurePath}`);
    await generateFigure({ outputPath: figurePath, durationSec });
    console.log(`[assets] figure done`);
  }

  return { backgroundPath, figurePath };
}

if (import.meta.main) {
  const assetsDir = process.env["ASSETS_DIR"] ?? "/tmp/blog-examples/assets";
  const durationSec = Number(process.env["ASSET_DURATION_SEC"] ?? "60");
  const force = process.env["FORCE"] === "1";
  generateAssets({ assetsDir, durationSec, force })
    .then((result) => {
      console.log("[assets] all done", result);
    })
    .catch((error: unknown) => {
      console.error("[assets] failed", error);
      process.exit(1);
    });
}
