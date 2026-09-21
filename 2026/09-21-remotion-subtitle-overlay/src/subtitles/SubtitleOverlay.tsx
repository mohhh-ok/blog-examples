import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont, fontFamily } from "@remotion/google-fonts/NotoSansJP";
import { LOOP_DURATION_SEC, getActiveLine, getLineText, getWordTimings } from "./script";
import { measureTextWidthPx } from "./measureText";

// loadFont() は内部で delayRender()/continueRender() を呼ぶので、
// ここで呼んでおけばレンダリングはフォント読み込み完了まで自動的に待つ。
// 実際に使う太さは 700 だけ (下記 FONT_WEIGHT)。"japanese" subset は Noto Sans JP
// では 100 個超のチャンクに分かれるため、使わない weight を含めると読み込み
// リクエスト数が単純に倍になる。
loadFont("normal", { weights: ["700"], subsets: ["japanese", "latin"] });

const BASE_FONT_SIZE_PX = 64;
const MIN_FONT_SIZE_PX = 30;
const MAX_TEXT_WIDTH_PX = 900;
const FONT_WEIGHT = 700;

// X・Y・Z すべてで同じこのコンポーネントを使う。
// 行ごとの表示・単語ハイライト・幅に合わせたフォント縮小をここで行う。
export const SubtitleOverlay: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTimeSec = frame / fps;
  const loopTimeSec = currentTimeSec % LOOP_DURATION_SEC;
  const activeLine = getActiveLine(loopTimeSec);

  const fontSizePx = useMemo(() => {
    if (!activeLine) {
      return BASE_FONT_SIZE_PX;
    }
    const text = getLineText(activeLine);
    const measuredWidth = measureTextWidthPx({
      text,
      fontFamily,
      fontWeight: FONT_WEIGHT,
      fontSizePx: BASE_FONT_SIZE_PX,
    });
    if (measuredWidth <= 0) {
      return BASE_FONT_SIZE_PX;
    }
    const scale = Math.min(1, MAX_TEXT_WIDTH_PX / measuredWidth);
    return Math.max(MIN_FONT_SIZE_PX, Math.round(BASE_FONT_SIZE_PX * scale));
  }, [activeLine]);

  if (!activeLine) {
    return null;
  }

  const words = getWordTimings(activeLine);
  const activeWordIndex = words.findIndex(
    (word) => loopTimeSec >= word.start && loopTimeSec < word.end,
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 180,
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          maxWidth: MAX_TEXT_WIDTH_PX,
          fontFamily,
          fontWeight: FONT_WEIGHT,
          fontSize: fontSizePx,
          lineHeight: 1.4,
          textAlign: "center",
        }}
      >
        {activeLine.segments.map((segment, index) => (
          <span
            key={`${index}-${segment}`}
            style={{
              color: index === activeWordIndex ? "#ffd23f" : "#ffffff",
              textShadow: "0 0 12px rgba(0,0,0,0.9), 0 2px 4px rgba(0,0,0,0.9)",
              padding: "0 2px",
              whiteSpace: "pre",
            }}
          >
            {segment}
          </span>
        ))}
      </div>
    </AbsoluteFill>
  );
};
