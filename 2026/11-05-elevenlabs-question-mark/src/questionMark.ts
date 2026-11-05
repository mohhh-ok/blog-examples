// ElevenLabs に送る直前に、全角の「？」を半角の「?」にする。画面に出す文は変えない。
// - 続く「？？」は 1 つにまとめる
// - 「？」の後ろに文が続くときは空白を 1 つ挟み、記号と次の語がつながって読まれないようにする
// - 後ろが閉じ括弧や感嘆符のときは文の続きではないので空白を挟まない
export function toHalfWidthQuestionMarks(text: string): string {
  return text.replace(/？+/g, "？").replace(/？(?=[^\s」』）)\]！!?])/g, "? ").replace(/？/g, "?");
}
