// Jev × キャラクター: 性格は自由入力の文章のまま持つ。来客が来るたびに
// 「性格 + 今の状況 + 今来た来客 1 人」を渡して反応の確率分布を受け取り、サイコロはコード側で振る。
// API 呼び出しは来客 1 回につき 1 回（キャラ 3 × 状況 2 × 来客 5 = 30 回）。
import { TypeSafeClient, choice } from "@typesafe-ai/sdk";

// 性格は if-then の規則ではなく気質で書く。来客ごとの答えは書かない。
const characters = {
  mikan: {
    name: "みかん（猫）",
    personality:
      "警戒心が強いが好奇心も強い。物音に敏感。落ち着いている相手には少しずつ近づく。甘えたいときは自分から来る。",
  },
  goma: {
    name: "ごま（犬）",
    personality:
      "とにかく人が好きで、来客は全部イベント。ただし飽きっぽく、相手が構ってくれないとすぐ興味を失う。",
  },
  tome: {
    name: "トメ（同居人のおばあちゃん）",
    personality:
      "口は悪いが世話好き。礼儀にうるさく、挨拶をしない相手には冷たい。子どもと動物には甘い。疲れていると誰にも会いたがらない。",
  },
} as const;

// 同じ来客でも状況で分布が動くかを見るため、状況を 2 つ用意する
const situations = {
  afternoon: "昼下がり。家の中は静かで、みんな暇をもてあましている。",
  night: "夜 10 時。昼から来客が続いて、全員疲れて眠い。",
} as const;

// 来客は性格文に書いていない状況にする（気質からしか答えが出ないように）
const visitors = {
  kid: "泣きながら迷子の猫を探しに来た近所の子ども",
  salesman: "笑顔で挨拶もせずにいきなりパンフレットを差し出す営業の人",
  regular_cat: "毎日来る隣の家の猫。今日は魚をくわえている",
  quiet: "小声で丁寧に挨拶して、玄関で待っている見知らぬ大人",
  band: "楽器ケースを持って、玄関先で音合わせを始めた学生 3 人",
} as const;

const reactions = {
  approach: "自分から近寄る、歓迎する",
  watch: "距離を置いて様子を見る",
  hide: "隠れる、部屋に引っ込む、応対しない",
} as const;
type VisitorId = keyof typeof visitors;
type Reaction = keyof typeof reactions;

const client = new TypeSafeClient();

const question = choice("`situation` のとき `visitor` が来た。`character` はどう反応するか？", reactions);

function sample(probabilities: Record<Reaction, number>, rand = Math.random()): Reaction {
  let acc = 0;
  for (const [label, p] of Object.entries(probabilities) as [Reaction, number][]) {
    acc += p;
    if (rand < acc) return label;
  }
  return "watch";
}

const cell = (p: Record<Reaction, number>) =>
  `${Math.round(p.approach * 100)}/${Math.round(p.watch * 100)}/${Math.round(p.hide * 100)}`;

let inputTokens = 0;
let outputTokens = 0;
const latencies: number[] = [];

for (const character of Object.values(characters)) {
  console.log(`\n## ${character.name}`);
  console.log(`| 来客 | 昼下がり（近寄る/様子見/隠れる） | 今日 | 夜・疲れ（同） | 今日 |`);
  console.log(`|---|---:|---|---:|---|`);
  const rows: Record<VisitorId, string[]> = { kid: [], salesman: [], regular_cat: [], quiet: [], band: [] };
  for (const situation of Object.values(situations)) {
    for (const id of Object.keys(visitors) as VisitorId[]) {
      const t0 = performance.now();
      const { answers, usage } = await client.systemOne({
        state: { character, situation, visitor: visitors[id] },
        questions: { reaction: question },
      });
      latencies.push(Math.round(performance.now() - t0));
      inputTokens += usage.input_tokens;
      outputTokens += usage.output_tokens;
      const { probabilities } = answers.reaction;
      rows[id].push(cell(probabilities), sample(probabilities));
    }
  }
  for (const id of Object.keys(visitors) as VisitorId[]) {
    console.log(`| ${id} | ${rows[id].join(" | ")} |`);
  }
}

const sorted = [...latencies].sort((a, b) => a - b);
console.log(`\ncalls=${latencies.length} latency(ms): first=${latencies[0]} min=${sorted[0]} median=${sorted[Math.floor(sorted.length / 2)]} max=${sorted[sorted.length - 1]}`);
console.log(`tokens: input=${inputTokens} output=${outputTokens}`);
