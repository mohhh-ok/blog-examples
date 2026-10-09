// アプリ全体で 1 つの AudioContext を持ち、画面が一度隠れたら次のタップで作り直す。
//
// iOS の Capacitor アプリ（WKWebView）では、画面をロックして戻ると AudioContext が
// state を "running" のまま currentTime だけ止まり、何を鳴らしても音が出なくなる。
// state では見分けられないので、resume() では戻らない。
//
// ノードを持つ側は、ノードの context が getAppAudioContext() と違えば作り直すこと。
// デコード済みの AudioBuffer はコンテキストに縛られないので使い回せる。

let appAudioContext: AudioContext | null = null;
let hiddenSinceCreated = false;

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden" && appAudioContext) hiddenSinceCreated = true;
});

export function getAppAudioContext(): AudioContext {
  if (!appAudioContext) {
    appAudioContext = new AudioContext();
    hiddenSinceCreated = false;
  }
  return appAudioContext;
}

/** タップのハンドラの同期部分で呼ぶ。 */
export function resumeAppAudio(): AudioContext {
  if (appAudioContext && hiddenSinceCreated) {
    const old = appAudioContext;
    appAudioContext = null;
    void old.close().catch(() => {});
  }
  const ctx = getAppAudioContext();
  const state: string = ctx.state;
  // "suspended" だけでなく、iOS の "interrupted" でも resume する
  if (state !== "running" && state !== "closed") void ctx.resume();
  return ctx;
}

/** 同梱の音声を fetch した応答が使えるか。iOS の Capacitor は同梱の音声ファイルに
 *  HTTP ではない応答を返すので、status が 0 になる。 */
export function isAudioResponseOk(res: Pick<Response, "ok" | "status">): boolean {
  return res.ok || res.status === 0;
}

// 使う側の例: 出口のノードを今のコンテキストに合わせる
let output: GainNode | null = null;

export async function playBundled(url: string): Promise<void> {
  const ctx = resumeAppAudio();
  const res = await fetch(url);
  if (!isAudioResponseOk(res)) throw new Error(`HTTP ${res.status}`);
  const buffer = await ctx.decodeAudioData(await res.arrayBuffer());
  if (!output || output.context !== ctx) {
    output = ctx.createGain();
    output.connect(ctx.destination);
  }
  const source = ctx.createBufferSource();
  source.buffer = buffer;
  source.connect(output);
  source.start();
}
