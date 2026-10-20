// 文字誤り率を出す前の正規化。言語ごとの決まり (数字の読み・かなと漢字の言い換えなど) は入れず、どの言語にも同じ規則を当てる。
// 1. Unicode NFKC (全角英数・半角カナをそろえる)
// 2. 小文字にする
// 3. 句読点 (\p{P})・記号 (\p{S})・空白 (\p{Z} と \s) を消す
// 数字の書き方の違い (三十 と 30) は誤りとして数える。
export function normalizeText(text: string, language: string): string {
  return text
    .normalize("NFKC")
    .toLocaleLowerCase(language)
    .replace(/[\p{P}\p{S}\p{Z}\s]/gu, "");
}

// 書記素 (見た目の 1 文字) に分ける。結合文字やサロゲートペアを 1 文字として数えるため。
export function splitGraphemes(text: string, language: string): string[] {
  const segmenter = new Intl.Segmenter(language, { granularity: "grapheme" });
  return Array.from(segmenter.segment(text), (segment) => segment.segment);
}

export function editDistance(reference: string[], hypothesis: string[]): number {
  let previous = Array.from({ length: hypothesis.length + 1 }, (_, index) => index);
  for (let row = 1; row <= reference.length; row++) {
    const current = [row];
    for (let column = 1; column <= hypothesis.length; column++) {
      const cost = reference[row - 1] === hypothesis[column - 1] ? 0 : 1;
      current.push(Math.min((previous[column] ?? 0) + 1, (current[column - 1] ?? 0) + 1, (previous[column - 1] ?? 0) + cost));
    }
    previous = current;
  }
  return previous[hypothesis.length] ?? 0;
}
