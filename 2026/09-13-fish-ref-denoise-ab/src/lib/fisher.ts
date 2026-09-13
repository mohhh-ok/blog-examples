// Fisher の正確検定 (両側)。2x2 分割表:
//   group1: ng=a, ok=b
//   group2: ng=c, ok=d
// 超幾何分布の実装で p を出す (外部統計ライブラリに依存しない)。
// アルゴリズム: 周辺合計を固定したまま取りうる全テーブルの確率を計算し、
// 観測テーブルの確率以下 (数値誤差を吸収する相対許容差つき) のものを合算する
// (R の fisher.test と同じ「二側 = 確率の和」定義)。

const logFactorialCache: number[] = [0]; // logFactorialCache[0] = log(0!) = 0

function logFactorial(n: number): number {
  if (n < 0) throw new Error(`logFactorial: negative argument ${n}`);
  while (logFactorialCache.length <= n) {
    const i = logFactorialCache.length;
    logFactorialCache.push(logFactorialCache[i - 1]! + Math.log(i));
  }
  return logFactorialCache[n]!;
}

function logChoose(n: number, k: number): number {
  if (k < 0 || k > n) return Number.NEGATIVE_INFINITY;
  return logFactorial(n) - logFactorial(k) - logFactorial(n - k);
}

// 2x2 表 (a, b / c, d) の超幾何分布下での確率 (周辺固定)。
function hyperLogProb(a: number, rowSum1: number, colSum1: number, total: number): number {
  // a は (1,1) セル。行合計 rowSum1 = a+b、列合計 colSum1 = a+c、total = a+b+c+d。
  return (
    logChoose(rowSum1, a) + logChoose(total - rowSum1, colSum1 - a) - logChoose(total, colSum1)
  );
}

export type FisherResult = {
  pValue: number;
  a: number;
  b: number;
  c: number;
  d: number;
};

export function fisherExactTest(a: number, b: number, c: number, d: number): FisherResult {
  const rowSum1 = a + b;
  const colSum1 = a + c;
  const total = a + b + c + d;

  const lowA = Math.max(0, rowSum1 - (total - colSum1));
  const highA = Math.min(rowSum1, colSum1);

  const observedLogP = hyperLogProb(a, rowSum1, colSum1, total);
  // 数値誤差の相対許容差 (1e-7)。observedLogP 以下 = より極端、を log 空間で判定する。
  const EPS = 1e-7;

  let pValue = 0;
  for (let x = lowA; x <= highA; x++) {
    const logP = hyperLogProb(x, rowSum1, colSum1, total);
    if (logP <= observedLogP + EPS) {
      pValue += Math.exp(logP);
    }
  }
  return { pValue: Math.min(1, pValue), a, b, c, d };
}
