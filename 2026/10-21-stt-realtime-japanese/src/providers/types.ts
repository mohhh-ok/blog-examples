// 1 本の音声を 1 つのプロバイダのリアルタイムの API に流した結果。
export type TranscribeInput = {
  pcm: Buffer;
  language: string;
  // 語のヒント。undefined なら何も渡さない。
  terms: string[] | undefined;
};

export type FinalSegment = {
  text: string;
  // 送り始めから、この確定が届くまでの時間。
  receivedAtMs: number;
  // 音声を送り終えて、終わりを明示した後に届いた確定か (プロバイダが自分で区切らなかった)。
  isForced: boolean;
};

export type TranscribeResult = {
  segments: FinalSegment[];
  error: string | null;
};

export type Provider = {
  name: string;
  // 計測の文書に載せる、送った設定。鍵は含めない。
  describeSettings: (input: { language: string; hasTerms: boolean }) => Record<string, unknown>;
  transcribe: (input: TranscribeInput) => Promise<TranscribeResult>;
};
