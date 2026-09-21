import React from "react";
import { AbsoluteFill, Loop, OffthreadVideo, useVideoConfig } from "remotion";
import { Video } from "@remotion/media";
import { SubtitleOverlay } from "../subtitles/SubtitleOverlay";
import { ASSET_LOOP_DURATION_SEC } from "../constants";

// 背景・図形(webm)・字幕を組み合わせる 1 つのコンポーネント。
// X / X-video / P / W / Y はすべてこれを使い、props で層を出し分ける
// (専用コンポーネントを条件ごとに新設しない)。
//
// - X:       background + figure(offthread) + subtitles
// - X-video: background + figure(media)      + subtitles
// - P:       background + figure(offthread)  (subtitles なし = 「webm 焼き込み済み動画」)
// - W:       background                      + subtitles (figure なし。X との差分計測用)
// - Y:       bakedVideo (P の出力)            + subtitles

export type SceneFigureMode = "offthread" | "media";

// 素材 (background.mp4 / figure.webm) は ASSET_LOOP_DURATION_SEC 秒で生成している。
// durationSec がこれを超える場合 (X の 20 分条件) は Loop で引き伸ばす。

export type SceneProps = {
  durationSec: number;
  backgroundUrl?: string;
  figureUrl?: string;
  figureMode?: SceneFigureMode;
  bakedVideoUrl?: string;
  showSubtitles: boolean;
};

export const Scene: React.FC<SceneProps> = ({
  durationSec,
  backgroundUrl,
  figureUrl,
  figureMode,
  bakedVideoUrl,
  showSubtitles,
}) => {
  const { fps } = useVideoConfig();
  const needsAssetLoop = durationSec > ASSET_LOOP_DURATION_SEC;
  const assetLoopFrames = Math.round(ASSET_LOOP_DURATION_SEC * fps);

  // 重要: AbsoluteFill は既定で display:flex; flexDirection:column なので、
  // 複数のレイヤーを素の子要素として並べると縦に並んでしまい重ならない
  // (SubtitleOverlay は自身が AbsoluteFill = position:absolute を持つため
  // flex flow から外れて偶然重なって見えていただけだった。実機検証で発見)。
  // レイヤーは 1 つずつ AbsoluteFill で包んで position:absolute にし、
  // 確実に重ねる。

  const backgroundLayer = backgroundUrl ? (
    <AbsoluteFill>
      <OffthreadVideo src={backgroundUrl} muted />
    </AbsoluteFill>
  ) : null;

  const figureLayer =
    figureUrl && figureMode === "offthread" ? (
      <AbsoluteFill>
        <OffthreadVideo src={figureUrl} transparent muted />
      </AbsoluteFill>
    ) : null;

  const figureMediaLayer =
    figureUrl && figureMode === "media" ? (
      <AbsoluteFill>
        <Video src={figureUrl} muted fallbackOffthreadVideoProps={{ transparent: true }} />
      </AbsoluteFill>
    ) : null;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      {bakedVideoUrl ? (
        <AbsoluteFill>
          <OffthreadVideo src={bakedVideoUrl} muted />
        </AbsoluteFill>
      ) : null}
      {needsAssetLoop ? (
        <Loop durationInFrames={assetLoopFrames}>
          <AbsoluteFill>
            {backgroundLayer}
            {figureLayer}
            {figureMediaLayer}
          </AbsoluteFill>
        </Loop>
      ) : (
        <>
          {backgroundLayer}
          {figureLayer}
          {figureMediaLayer}
        </>
      )}
      {showSubtitles ? <SubtitleOverlay /> : null}
    </AbsoluteFill>
  );
};
