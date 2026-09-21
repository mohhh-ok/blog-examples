// コンポジション (Root.tsx) と計測スクリプト (scripts/) の両方から参照する定数。
// 二重管理を避けるためここに集約する。

export const FPS = 30;
export const WIDTH = 1080;
export const HEIGHT = 1920;

// generate-assets.ts が background.mp4 / figure.webm を生成する長さ。
// 字幕データ (subtitles/script.ts) の LOOP_DURATION_SEC とも一致させている。
export const ASSET_LOOP_DURATION_SEC = 60;
