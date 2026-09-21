// 一般的な日本語の短文を並べただけの、字幕表示のダミー原稿。
// 60 秒のブロックとしてループさせる前提で作っている (LOOP_DURATION_SEC 参照)。
// 各行は「開始・終了 (ループ内の秒数)」と「単語ハイライト用のセグメント配列」を持つ。
// テキスト本体はセグメントの結合から導出するので、テキストとセグメントがずれることはない。

export type SubtitleLine = {
  start: number;
  end: number;
  segments: readonly string[];
};

const RAW_LINES: ReadonlyArray<{
  start: number;
  end: number;
  segments: readonly string[];
}> = [
  {
    start: 0.5,
    end: 5.3,
    segments: ["今日は", "朝から", "天気が", "良くて、", "散歩に", "出かけました。"],
  },
  {
    start: 5.8,
    end: 10.4,
    segments: ["近くの", "公園には", "桜の木が", "たくさん", "並んでいます。"],
  },
  {
    start: 10.9,
    end: 15.9,
    segments: ["少し歩くと", "川沿いの道に", "出て、", "風がとても", "心地よかったです。"],
  },
  {
    start: 16.4,
    end: 21.6,
    segments: ["途中で", "コーヒーを", "買って、", "ベンチに", "座って", "一休みしました。"],
  },
  {
    start: 22.1,
    end: 26.7,
    segments: ["遠くの空には", "大きな雲が", "ゆっくりと", "流れていました。"],
  },
  {
    start: 27.2,
    end: 32.4,
    segments: ["帰り道では", "商店街を", "通って、", "いろいろな", "お店を眺めました。"],
  },
  {
    start: 32.9,
    end: 37.9,
    segments: ["夕方になると", "空の色が", "少しずつ", "橙色に", "変わっていきます。"],
  },
  {
    start: 38.4,
    end: 42.8,
    segments: ["家に着く頃には、", "すっかり", "日が暮れていました。"],
  },
  {
    start: 43.3,
    end: 48.1,
    segments: ["今日一日を", "振り返ると、", "穏やかで", "良い一日でした。"],
  },
  {
    start: 48.6,
    end: 53.6,
    segments: ["明日は", "どんな天気に", "なるか、", "少し楽しみです。"],
  },
];

export const LOOP_DURATION_SEC = 60;

function validateLines(lines: ReadonlyArray<SubtitleLine>): void {
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    if (!line) {
      throw new Error(`subtitle line at index ${i} is missing`);
    }
    if (line.end <= line.start) {
      throw new Error(`subtitle line ${i} has end <= start: ${JSON.stringify(line)}`);
    }
    if (line.segments.length === 0) {
      throw new Error(`subtitle line ${i} has no segments`);
    }
    if (i > 0) {
      const previous = lines[i - 1];
      if (previous && line.start < previous.end) {
        throw new Error(
          `subtitle line ${i} overlaps with previous line: ${JSON.stringify(previous)} -> ${JSON.stringify(line)}`,
        );
      }
    }
  }
  const last = lines[lines.length - 1];
  if (last && last.end > LOOP_DURATION_SEC) {
    throw new Error(
      `last subtitle line ends at ${last.end}s, which is after the loop duration ${LOOP_DURATION_SEC}s`,
    );
  }
}

export const SUBTITLE_LINES: ReadonlyArray<SubtitleLine> = RAW_LINES;
validateLines(SUBTITLE_LINES);

export function getLineText(line: SubtitleLine): string {
  return line.segments.join("");
}

export function getActiveLine(loopTimeSec: number): SubtitleLine | null {
  return (
    SUBTITLE_LINES.find((line) => loopTimeSec >= line.start && loopTimeSec < line.end) ?? null
  );
}

export type WordTiming = {
  text: string;
  start: number;
  end: number;
};

export function getWordTimings(line: SubtitleLine): WordTiming[] {
  const totalChars = line.segments.reduce((sum, segment) => sum + segment.length, 0);
  const duration = line.end - line.start;
  let cursor = line.start;
  return line.segments.map((segment) => {
    const share = totalChars === 0 ? 0 : (segment.length / totalChars) * duration;
    const start = cursor;
    const end = cursor + share;
    cursor = end;
    return { text: segment, start, end };
  });
}
