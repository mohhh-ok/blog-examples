// TTS 出力尺の推定・上限ゲートの再実装。
// 実運用の TTS パイプライン側の同等ロジック (script 自身の文字種から推定する話速テーブル・
// 上限秒数ゲート) と同じ文字種範囲・係数を使う (本番実装の該当関数と突合済み)。
// このプロジェクトは常に「script 自身の文字種から推定する」方式のみを使う。申告言語を
// 信用する別モードはここでは扱わない。

export type ScriptLetterCounts = { cjk: number; alphabetic: number };

const CJK_RANGES: ReadonlyArray<readonly [number, number]> = [
  [0x3040, 0x309f], // Hiragana
  [0x30a0, 0x30ff], // Katakana
  [0x31f0, 0x31ff], // Katakana Phonetic Extensions
  [0x4e00, 0x9fff], // CJK Unified Ideographs
  [0x3400, 0x4dbf], // CJK Unified Ideographs Extension A
  [0xf900, 0xfaff], // CJK Compatibility Ideographs
  [0x1100, 0x11ff], // Hangul Jamo
  [0x3130, 0x318f], // Hangul Compatibility Jamo
  [0xac00, 0xd7af], // Hangul Syllables
  [0xff21, 0xff3a], // Fullwidth Latin Capital Letters
  [0xff41, 0xff5a], // Fullwidth Latin Small Letters
];

const ALPHABETIC_RANGES: ReadonlyArray<readonly [number, number]> = [
  [0x0041, 0x005a], // A-Z
  [0x0061, 0x007a], // a-z
  [0x00c0, 0x024f], // Latin-1 Supplement (letters) + Latin Extended-A/B
  [0x0400, 0x04ff], // Cyrillic
];

const NON_LETTER_EXCLUSIONS = new Set([0x00d7, 0x00f7]); // × ÷

function isInRanges(codePoint: number, ranges: ReadonlyArray<readonly [number, number]>): boolean {
  return ranges.some(([start, end]) => codePoint >= start && codePoint <= end);
}

export function countScriptLetters(text: string): ScriptLetterCounts {
  let cjk = 0;
  let alphabetic = 0;
  for (const char of text) {
    const codePoint = char.codePointAt(0);
    if (codePoint === undefined) continue;
    if (isInRanges(codePoint, CJK_RANGES)) {
      cjk += 1;
    } else if (!NON_LETTER_EXCLUSIONS.has(codePoint) && isInRanges(codePoint, ALPHABETIC_RANGES)) {
      alphabetic += 1;
    }
  }
  return { cjk, alphabetic };
}

export const codePointLength = (script: string): number => [...script].length;

export const CHARS_PER_SEC_LOWER_BY_FAMILY = {
  cjk: 6,
  alphabetic: 8,
} as const;

export const estimateTtsOutputSecondsByScript = (script: string): number => {
  const cjkLetters = countScriptLetters(script).cjk;
  const nonCjkCodePoints = codePointLength(script) - cjkLetters;
  return (
    cjkLetters / CHARS_PER_SEC_LOWER_BY_FAMILY.cjk +
    nonCjkCodePoints / CHARS_PER_SEC_LOWER_BY_FAMILY.alphabetic
  );
};

export const AVATAR_TTS_OUTPUT_GATE_CONFIG = {
  safetyFactor: 2,
  fixedMarginSec: 5,
} as const;

export const computeTtsOutputUpperBoundSec = (text: string): number => {
  return (
    estimateTtsOutputSecondsByScript(text) * AVATAR_TTS_OUTPUT_GATE_CONFIG.safetyFactor +
    AVATAR_TTS_OUTPUT_GATE_CONFIG.fixedMarginSec
  );
};

export const isOverflow = (args: { actualDurationSec: number; text: string }): boolean => {
  return args.actualDurationSec > computeTtsOutputUpperBoundSec(args.text);
};
