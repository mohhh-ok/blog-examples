# Remotion 字幕オーバーレイ: 描き分け vs 焼き込み動画 + 字幕重ね

Remotion で字幕の ON/OFF だけを切り替えたいとき、どの作り方が速いかを計測する。

## 背景・問い

透過 webm (人物などのレイヤー) を含む動画に字幕を付けるとき、素朴には毎回
「背景 + レイヤー + 字幕」を Remotion で全部描き直す。しかし字幕を差し替えるだけなら、
レイヤーまで含めて一度焼き込んだ動画を使い回し、字幕だけを重ねる方が速いのではないか。
この検証はその速度差を、同じ字幕コンポーネントを使った複数の作り方で比較する。

## 比較対象

- **X**: 背景動画 + 透過 webm (人物の代わりの図形) + 字幕を、Remotion で全部描いて h264 で出す
- **P**: X から字幕を抜いたもの (背景 + webm)。「webm 焼き込み済み動画」として Y・Z の入力にする
- **Y**: P を動画 1 本として Remotion に読み込み、その上に字幕を描いて h264 で出す
- **Z**: 字幕だけを透過で Remotion に描き (PNG キャプチャ + アルファ対応コーデック。VP9 と ProRes 4444 の 2 通り)、ffmpeg の overlay で P に重ねる。「描く時間」と「重ねる時間」を分けて計測する
- **W** (分解用): 背景 + 字幕 (webm なし)。X との差が透過 webm のデコードコスト
- **X-video** (参考): 透過 webm の描画を `OffthreadVideo` ではなく `@remotion/media` の `<Video>` で行った X。ブラウザが WebGL2 を使えず内部で `OffthreadVideo` にフォールバックした場合はその旨を記録する

X・Y・Z はすべて同じ字幕コンポーネント (`src/subtitles/SubtitleOverlay.tsx`) を使う。

## 手法

- 素材はすべて ffmpeg の合成で自作する (`scripts/generate-assets.ts`)。人物動画の取得や
  matting は行わない
  - 背景: `gradients` ソースフィルタで作る動くグラデーション (1080x1920, 30fps, 60秒)
  - 透過 webm: 画面の約半分を占める、縁をフェザーした半透明の円がリサージュ曲線状に動く図形
    (`geq` フィルタで RGBA を直接計算し VP9 + `yuva420p` でエンコード)
- 1080x1920 (縦) 30fps。尺は 60 秒を基本に各条件 n=3。20 分は P を 20 回つないだもの
  (ffmpeg concat demuxer、再エンコードなし) に対して Y と Z を 1 回ずつ測る。X の 20 分は、
  60 秒実測の秒/秒の中央値から外挿して 1 時間を超える見込みなら実行せず、外挿値を記録する
  (`scripts/lib/pipeline.ts` の `runLongPipeline`)
- `concurrency` は 1 と Remotion の既定値の両方で測る
- 計測は所要時間 (秒) と動画 1 秒あたりの処理秒数、出力ファイルサイズ。bundle は 1 回だけ
  作って全条件で使い回し、render とは別に時間を記録する
- ブラウザ (Chrome Headless Shell) も計測全体で 1 つを使い回す
  (`scripts/lib/remotionRunner.ts` の `openSharedBrowser`)。字幕フォント
  (Noto Sans JP) は "japanese" subset だけで 100 チャンク超に分かれており、
  `renderMedia` のたびに新しいブラウザを起動すると毎回フォントを再ダウンロード
  してしまい、ネットワーク時間が描画コストの比較に混入するため
- X・Y・Z の出力から同じ時刻のフレームを抜いて `results/frames/` に並べ、字幕の位置・大きさが
  一致しているかを画像で残す

## 実装で判明した注意点 (未文書化のはまりどころ)

検証の途中で 4 つ、ドキュメントに書かれていない挙動を実機で確認した。うち 1 つ
(4) は自分のコンポーネント実装のミスで、Remotion 自体の問題ではない。

1. **`OffthreadVideo` / `<Video>` の `src` に `file://` を渡しても読めない。**
   `remotion/dist/cjs/absolute-src.js` は `file://` をそのまま通す (URL 書き換えをしない) が、
   実際のフレーム取得は `renderMedia` が立てるローカルサーバー経由の
   `/proxy?src=...` エンドポイントを必ず通り、その先のダウンローダーは
   `http://` / `https://` しか受け付けない (`Can only download URLs starting with
   http:// or https://` で失敗する)。そのため `/tmp` に置いた素材は bundle 出力
   ディレクトリ配下にコピーし、レンダー用ローカルサーバーの相対パス
   (`/served/xxx.mp4`) 経由で参照する (`scripts/lib/servedAssets.ts`)。
2. **libvpx-vp9 の `-b:v 0` (無制限 Constant Quality) で作った透過 webm は、
   `OffthreadVideo` の `transparent` では読めない。** ffmpeg 自身の
   `-c:v libvpx-vp9` デコーダでは正しくアルファが読めるにもかかわらず、
   Remotion の内部コンポジタ経由だとアルファが全面 0 (透明) として扱われ、
   図形が完全に消える (エラーは出ない)。Remotion 自身が `renderMedia` で
   VP9 アルファを書き出すときの内部 ffmpeg コマンドは `-b:v` を指定せず
   `-crf` だけを使っている (`-c:v libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0
   -crf 28`)。同じ流儀 (`-b:v` を付けない) に倣うことで解決した
   (`scripts/generate-assets.ts` の `generateFigure`)。
3. **ffmpeg で透過 VP9 webm を `overlay` フィルタに読ませるときは
   `-c:v libvpx-vp9` を明示しないとアルファが無視される。** ffmpeg の既定の
   `vp9` デコーダは VP9 の (BlockAdditional に格納された) アルファ側チャンネルを
   読まないため、アルファが全面不透明として扱われ、重ねる側の背景が黒く塗り
   つぶされる。overlay の入力側だけ `-c:v libvpx-vp9` を指定してデコードする
   (`scripts/lib/remotionRunner.ts` の `overlayOntoBaseVideo`)。ProRes 4444 の
   アルファは単一ビットストリーム内の 4 枚目のプレーンなので、この指定は不要。
4. **(自分のバグ) `<AbsoluteFill>` を複数の動画レイヤーの共通の親として
   そのまま使うと、レイヤーが重ならず縦に並んでしまう。** `AbsoluteFill` は
   既定で `display:flex; flexDirection:column` を持つコンテナで
   (`remotion/dist/cjs/AbsoluteFill.js`)、それ自体は `position:absolute` だが
   **子要素を自動で重ねてはくれない**。`OffthreadVideo` (`<Img>` 経由) は
   `position:absolute` を持たないため、複数の `OffthreadVideo` を素の兄弟要素
   として並べると flex column の別の行に配置され、2 つめ以降が画面外や潰れた
   高さに追いやられて見えなくなる。字幕コンポーネント
   (`src/subtitles/SubtitleOverlay.tsx`) は自身の中で `<AbsoluteFill>` を
   使っていたために偶然 flex flow から外れて正しく重なって見えていただけで、
   背景 + 透過 webm の 2 層 (X・P で使う) では完全に無反応 (図形が一切見えない)
   になった。レイヤーは 1 つずつ個別の `<AbsoluteFill>` で包んで
   `position:absolute` にすることで解決した (`src/compositions/Scene.tsx`)。

## 参照した一次情報

- `OffthreadVideo` の `transparent` prop: `node_modules/remotion/dist/cjs/video/props.d.ts`
- `@remotion/media` の `<Video>` と `fallbackOffthreadVideoProps`:
  `node_modules/@remotion/media/dist/video/props.d.ts`
- `renderMedia` / `selectComposition` のオプション:
  `node_modules/@remotion/renderer/dist/render-media.d.ts`,
  `node_modules/@remotion/renderer/dist/select-composition.d.ts`
- `pixelFormat` / `codec` / `proResProfile` の組み合わせ:
  `node_modules/@remotion/renderer/dist/pixel-format.js`,
  `node_modules/@remotion/renderer/dist/prores-profile.js`,
  `node_modules/@remotion/renderer/dist/get-prores-profile-name.js`
- `<Composition>` の `calculateMetadata`: `node_modules/remotion/dist/cjs/Composition.d.ts`
- `<AbsoluteFill>` の既定スタイル (`display:flex; flexDirection:column`):
  `node_modules/remotion/dist/cjs/AbsoluteFill.js`
- `@remotion/google-fonts` の `loadFont` が内部で `delayRender`/`continueRender`
  を呼ぶこと: `node_modules/@remotion/google-fonts/dist/cjs/base.js`
- Remotion 公式ドキュメント: https://www.remotion.dev/docs/transparent-videos ,
  https://www.remotion.dev/docs/offthreadvideo ,
  https://www.remotion.dev/docs/videos/transparency
  (いずれも「Remotion からの書き出し方」は書かれているが、外部で作った
  透過 webm を `OffthreadVideo` に読ませる際の推奨エンコード設定は明記されて
  いなかった。上記の注意点 2 は実機検証で見つけた)

## 前提

- ランタイムは [bun](https://bun.sh/)。Remotion は `4.0.459` に固定
- ffmpeg / ffprobe は既定で PATH 上のものを使う (libx264・libvpx-vp9・prores_ks
  が有効なビルドが必要)。別の場所にある場合は環境変数 `FFMPEG_BIN` /
  `FFPROBE_BIN` でパスを上書きする

## 再現手順

```sh
bun install

# 素材生成 (背景 + 透過 webm。/tmp/blog-examples/assets/ に生成。既定 60 秒)
bun run assets

# 本番計測 (既定: 60秒 x n=3 x 全条件 x concurrency 1,default + 20分の Y/Z/X)
bun run measure
```

`bun run measure` は素材生成 → bundle → 各条件のレンダー → (指定時) 長尺 →
フレーム比較 → `results/*.json` + `results/summary.md` まで 1 コマンドで通る。

尺・回数・対象条件・concurrency・長尺の有無は CLI 引数か環境変数で上書きできる
(既定値が本番の計測)。

| 環境変数 | CLI 引数 | 既定値 | 内容 |
|---|---|---|---|
| `DURATION_SEC` | `--duration` | `60` | 1 条件あたりの尺 (秒) |
| `REPS` | `--reps` | `3` | 各条件の繰り返し回数 |
| `CONDITIONS` | `--conditions` | 全条件 | カンマ区切り (`X,X-video,P,W,Y,Z-vp9,Z-prores`) |
| `CONCURRENCIES` | `--concurrency` | `1,default` | カンマ区切り (`1,4,default` 等) |
| `OUT_DIR` | `--out-dir` | `results/` | JSON・summary.md・frames の出力先 |
| `ASSETS_DIR` | `--assets-dir` | `/tmp/blog-examples/assets` | 素材の置き場 |
| `RENDER_DIR` | `--render-dir` | `/tmp/blog-examples/out` | レンダー出力 (動画本体) の置き場 |
| `LONG` | `--long` | `0` | `1` で 20 分条件 (Y/Z 実測・X は外挿判定) も実行 |
| `LONG_MINUTES` | `--long-minutes` | `20` | 長尺条件の尺 (分) |
| `LONG_CONDITIONS` | `--long-conditions` | `Y,Z-vp9,Z-prores` | 20 分条件で実際に実行する対象 (`Y`/`Z-vp9`/`Z-prores` の部分集合。X は 60 秒実測からの外挿判定なので対象外) |
| `FFMPEG_BIN` | - | `ffmpeg` (PATH) | ffmpeg バイナリのパス |
| `FFPROBE_BIN` | - | `ffprobe` (PATH) | ffprobe バイナリのパス |

例 (動作確認用に短尺・1 回だけ回す):

```sh
DURATION_SEC=5 REPS=1 CONDITIONS=X,P,W bun run measure
```

フレーム抽出だけを単体で使う場合:

```sh
VIDEO_PATH=results/frames/... OUTPUT_PATH=/tmp/out.png TIMESTAMP_SEC=2 bun run frames
```

## 動作確認 (smoke test)

構築段階では、5 秒尺・n=1 で全条件を通す動作確認のみ行い、本番の実測
(60 秒 n=3・20 分) は実行していない。実測はこのマシンの他の作業を止めてから
別途実行する。
