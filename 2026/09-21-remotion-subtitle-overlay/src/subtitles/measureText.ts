// キャンバスでテキスト幅を測る。Remotion のレンダリングは実際の Chromium 内で
// React ツリーを評価するので、コンポーネントの description 内で document を
// 直接使って構わない (SSR は行われない)。

export function measureTextWidthPx(args: {
  text: string;
  fontFamily: string;
  fontWeight: number;
  fontSizePx: number;
}): number {
  const { text, fontFamily, fontWeight, fontSizePx } = args;
  if (typeof document === "undefined") {
    throw new Error("measureTextWidthPx requires a browser environment (document is undefined)");
  }
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("2D canvas context is unavailable");
  }
  context.font = `${fontWeight} ${fontSizePx}px ${fontFamily}`;
  return context.measureText(text).width;
}
