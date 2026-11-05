import { expect, test } from "bun:test";
import { toHalfWidthQuestionMarks } from "./questionMark.ts";

test.each([
  ["あした ひま？", "あした ひま?"],
  ["あした ひま？？", "あした ひま?"],
  ["あした ひま？ あそぼう。", "あした ひま? あそぼう。"],
  ["あした ひま？あそぼう。", "あした ひま? あそぼう。"],
  ["すし、好き?", "すし、好き?"],
  ["こんにちは。", "こんにちは。"],
  ["「ひま？」って", "「ひま?」って"],
  ["なに？！", "なに?！"],
])("%s → %s", (input, expected) => {
  expect(toHalfWidthQuestionMarks(input)).toBe(expected);
});
