// TTS 完走チェック (LCS 比率) の再実装。
// 実運用の TTS パイプライン側の完走判定ロジックと前処理・文字集合・DP を完全に一致させる
// (本番実装の該当関数と突合済み)。

const TTS_COMPLETION_CHECK_PUNCT_CHARS =
  "。、，,．.！!？?「」『』（）()：:；;〜~…・-—―\"'　";
const TTS_COMPLETION_CHECK_PUNCT_CHAR_SET = new Set([...TTS_COMPLETION_CHECK_PUNCT_CHARS]);

export function preprocessForTtsCompletionCheck(text: string): string {
  const normalized = text.normalize("NFKC");
  const noWhitespace = normalized.replace(/\s+/g, "");
  return [...noWhitespace].filter((ch) => !TTS_COMPLETION_CHECK_PUNCT_CHAR_SET.has(ch)).join("");
}

function lcsLength(a: readonly string[], b: readonly string[]): number {
  const n = a.length;
  const m = b.length;
  if (n === 0 || m === 0) return 0;
  let prev = new Array<number>(m + 1).fill(0);
  for (let i = 1; i <= n; i++) {
    const cur = new Array<number>(m + 1).fill(0);
    const ai = a[i - 1];
    for (let j = 1; j <= m; j++) {
      cur[j] = ai === b[j - 1] ? (prev[j - 1] ?? 0) + 1 : Math.max(prev[j] ?? 0, cur[j - 1] ?? 0);
    }
    prev = cur;
  }
  return prev[m] ?? 0;
}

export type TtsContentCheckComparison = {
  lcsRatio: number;
  coverage: number;
  asrChars: number;
  scriptChars: number;
};

export function computeTtsContentCheckMetrics(args: {
  asrText: string;
  script: string;
}): TtsContentCheckComparison {
  const asrChars = [...preprocessForTtsCompletionCheck(args.asrText)];
  const scriptChars = [...preprocessForTtsCompletionCheck(args.script)];

  if (scriptChars.length === 0) {
    return { lcsRatio: 0, coverage: 0, asrChars: asrChars.length, scriptChars: 0 };
  }

  const lcsLen = lcsLength(asrChars, scriptChars);
  return {
    lcsRatio: lcsLen / scriptChars.length,
    coverage: asrChars.length / scriptChars.length,
    asrChars: asrChars.length,
    scriptChars: scriptChars.length,
  };
}

export const TTS_CONTENT_CHECK_LCS_RATIO_THRESHOLD = 0.95;
export const TTS_CONTENT_CHECK_MIN_SLACK_CHARS = 2;
export const TTS_CONTENT_CHECK_COLLAPSE_RATIO = 0.5;

export function resolveActLineContentCheckThreshold(scriptChars: number): number {
  return Math.min(
    TTS_CONTENT_CHECK_LCS_RATIO_THRESHOLD,
    (scriptChars - TTS_CONTENT_CHECK_MIN_SLACK_CHARS) / scriptChars,
  );
}

export function isNg(lcsRatio: number, threshold: number): boolean {
  return lcsRatio < threshold;
}

export function isCollapse(lcsRatio: number): boolean {
  return lcsRatio < TTS_CONTENT_CHECK_COLLAPSE_RATIO;
}
