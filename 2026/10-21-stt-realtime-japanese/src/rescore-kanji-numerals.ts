// 参考値の採点: 漢数字 (位・つ・歳・世・人・枚・種・本・球・ラン の前) を算用数字に直してから、40 本の合計の文字誤り率を出す。
// 使い方: node src/rescore-kanji-numerals.ts <一覧の tsv> <jsonl...>
import { readFileSync } from "node:fs";
import { editDistance, normalizeText, splitGraphemes } from "./normalize.ts";
const D: Record<string, number> = { 〇: 0, 一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9 };
function k2n(s: string): number {
  let total = 0, cur = 0;
  for (const ch of s) {
    if (ch in D) cur = D[ch]!;
    else { const u = ch === "十" ? 10 : ch === "百" ? 100 : 1000; total += (cur || 1) * u; cur = 0; }
  }
  return total + cur;
}
const conv = (t: string) => t.replace(/[〇一二三四五六七八九十百千]+(?=(位|つ|歳|世|人|枚|種|本|球|ラン))/g, (m) => String(k2n(m)));
const manifest = new Map(readFileSync(process.argv[2]!, "utf8").split("\n").slice(1).filter(Boolean).map((l) => { const [id, text] = l.split("\t"); return [id!, text!]; }));
for (const f of process.argv.slice(3)) {
  let e = 0, r = 0, changed = 0;
  for (const line of readFileSync(f, "utf8").split("\n").filter(Boolean)) {
    const rec = JSON.parse(line);
    const hyp0 = rec.segments.map((s: any) => s.text).join("");
    const hyp = conv(hyp0); if (hyp !== hyp0) changed++;
    const ref = normalizeText(conv(manifest.get(rec.id)!), rec.language);
    const rg = splitGraphemes(ref, rec.language);
    e += editDistance(rg, splitGraphemes(normalizeText(hyp, rec.language), rec.language)); r += rg.length;
  }
  console.log(f.split("/").pop(), "edits", e, "ref", r, "CER", (100 * e / r).toFixed(1) + "%", "changed", changed);
}
