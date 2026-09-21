import React from "react";
import { AbsoluteFill } from "remotion";
import { SubtitleOverlay } from "../subtitles/SubtitleOverlay";

// Z 条件用: 字幕だけを透過背景に描く。AbsoluteFill に backgroundColor を
// 指定しないので、アルファ対応コーデック (VP9 / ProRes 4444) + png キャプチャで
// 書き出すと背景が透明のまま残る。
export type SubtitlesOnlyProps = {
  durationSec: number;
};

export const SubtitlesOnly: React.FC<SubtitlesOnlyProps> = () => {
  return (
    <AbsoluteFill>
      <SubtitleOverlay />
    </AbsoluteFill>
  );
};
