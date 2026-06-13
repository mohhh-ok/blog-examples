import 'dotenv/config';
import { db } from './db';
import { postsTable } from "./db/schema";
import { embed } from './ollama';

// 短文（ベイト・対照群）
// 「京都」単体や近接都市・関連トピックを単独で持つ短文。長文よりこちらが上位に来てしまえば希釈効果の証拠になる
const SHORT_TEXTS = [
  '京都が好きだ',
  '京都に旅行に行きたい',
  '大阪の下町を散歩した', // 京都に近い別都市。検索「京都」でどう振る舞うか
  '抹茶アイスを食べた', // 京都に関係ない関連トピック
  '職人の手仕事に憧れる', // 京都に関係ない関連トピック
];

// 長文（本来ヒットしてほしい本命）
// それぞれタイトルとしては「京都の○○」だが、本文は○○の専門用語で固める。
// 結果として埋め込みベクトルは○○方向に強く引っ張られ、「京都」クエリでヒットしにくくなる現象を狙う
const LONG_TEXTS = [
  // 本来: 京都の和菓子文化（京都への言及はわずか、本文は和菓子製法に支配される）
  `練り切りは白餡に求肥を加え木べらで季節の花を象る。寒梅粉や道明寺粉は吸水と粘りで使い分け、羊羹は寒天と砂糖の配合で口溶けが決まる。京都の店ではこの伝統が受け継がれている。`,

  // 本来: 京都の伝統工芸職人の哲学（京都はわずか、本文は職人論に支配される）
  `若い職人は数年を道具の手入れと素材の見極めに費やす。徒弟制度では親方の技を盗むことが求められ、暗黙知の蓄積が厚みを生む。後継者不足は伝統工芸共通の課題だ。京都の工房もこの中で模索を続けている。`,

  // 本来: 京都の地下鉄延伸計画（京都はわずか、本文は都市計画・土木に支配される）
  `地下鉄延伸の採算性評価は需要予測と建設費の精度に左右される。シールド工法は地盤でセグメント設計が変わり、駅部の開削は交通規制が必要だ。京都市の構想もこの枠組みで検討されている。`,
];

const TEST_DATA = [...SHORT_TEXTS, ...LONG_TEXTS];

async function reseed() {
  console.log('Deleting existing rows...');
  await db.delete(postsTable);
  for (const testData of TEST_DATA) {
    const preview = testData.length > 30 ? `${testData.slice(0, 30)}…` : testData;
    console.log(`Inserting (${testData.length} chars): ${preview}`);
    const embedding = await embed(testData);
    await db.insert(postsTable).values({
      content: testData,
      embedding,
    });
  }
}

reseed();
