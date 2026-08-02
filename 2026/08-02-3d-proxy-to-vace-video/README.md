# 3D プロキシから fal.ai v2v へ

Three.js で 3D の粘土 (clay) 動画 + depth pass を出し、fal.ai の Kling O3 Edit と Wan VACE 14B depth に食わせて質感を差し替えるパイプラインの記録。

## 構成

- `index.html` / `main.js` — Three.js シーン。`?pass=depth` で depth 出力に切り替え
- `capture.mjs` — Playwright headless で 1 フレームずつ PNG 化。使い方: `node capture.mjs rgb` or `node capture.mjs depth`

## 動かし方

```sh
pnpm add -D playwright three
pnpm exec playwright install chromium

# Soldier.glb を三.js リポから取得して assets/ に置く (無料 / MIT)
mkdir -p assets
curl -o assets/Soldier.glb \
  https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/models/gltf/Soldier.glb

# 3D 動画レンダリング (RGB pass)
node capture.mjs rgb
ffmpeg -y -framerate 30 -i frames/%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 out-rgb.mp4

# depth pass
node capture.mjs depth
ffmpeg -y -framerate 30 -i frames-depth/%04d.png -c:v libx264 -pix_fmt yuv420p -crf 14 out-depth.mp4
```

## v2v へ渡す

fal.ai の `fal-ai/wan-vace-14b/depth` に `video_url = out-depth.mp4`、`ref_image_urls = [参照 jpg 群]`、`preprocess=false`、`match_input_frames_per_second=true`、`match_input_num_frames=true` で投入。詳細は blog 本文参照。

## 出力

`output/` に各世代の生成物 (animated webp)。

| ファイル | 内容 |
|---|---|
| `01-3d-clay-rgb.webp` | Three.js の RGB pass (5s、フィルされたシーン) |
| `02-3d-depth.webp` | depth pass (near=白 / far=黒、VACE 用) |
| `03-ref-cinematic-full.webp` | FLUX Pro Ultra の初回参照 (シーン全体) |
| `04-ref-soldier.webp` / `05-ref-airplane.webp` / `06-ref-field.webp` | 役割別参照 |
| `10-kling-v1-single-ref.webp` | Kling O3 Edit + 参照 1 枚 |
| `11-kling-v2-three-refs-duplicates.webp` | Kling + 参照 3 枚 (2 人・2 機の失敗) |
| `12-vace-8s-airplane-early.webp` | VACE 初回 (飛行機が冒頭から漏れる) |
| `13-vace-5s-retimed-opposite-plane.webp` | 5s + 飛行機タイミング前倒し (逆方向から追加の 1 機) |
| `14-vace-5s-filled-scene.webp` | 空を雲・地面を起伏・遠景に木で埋めた最終版 |
