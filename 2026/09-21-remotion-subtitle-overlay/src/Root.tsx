import React from "react";
import { Composition } from "remotion";
import { Scene, type SceneProps } from "./compositions/Scene";
import { SubtitlesOnly, type SubtitlesOnlyProps } from "./compositions/SubtitlesOnly";
import { FPS, WIDTH, HEIGHT } from "./constants";

const DEFAULT_DURATION_SEC = 5;

const defaultSceneProps: SceneProps = {
  durationSec: DEFAULT_DURATION_SEC,
  showSubtitles: true,
};

const defaultSubtitlesOnlyProps: SubtitlesOnlyProps = {
  durationSec: DEFAULT_DURATION_SEC,
};

// scene: X / X-video / P / W / Y が使う共通コンポジション
// subtitles-only: Z (透過キャプチャ) 用コンポジション
// duration は props.durationSec から calculateMetadata で都度計算する
// (5 秒の動作確認・60 秒の本番・20 分の長尺をすべて同じコンポジションでまかなう)
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="scene"
        component={Scene}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        durationInFrames={Math.round(DEFAULT_DURATION_SEC * FPS)}
        defaultProps={defaultSceneProps}
        calculateMetadata={async ({ props }) => ({
          durationInFrames: Math.round(props.durationSec * FPS),
        })}
      />
      <Composition
        id="subtitles-only"
        component={SubtitlesOnly}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        durationInFrames={Math.round(DEFAULT_DURATION_SEC * FPS)}
        defaultProps={defaultSubtitlesOnlyProps}
        calculateMetadata={async ({ props }) => ({
          durationInFrames: Math.round(props.durationSec * FPS),
        })}
      />
    </>
  );
};
