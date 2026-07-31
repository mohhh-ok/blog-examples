# AI 動画着せ替え — 全段 OSS vs クローズドの方式比較

対応記事: 2026-07-31 (執筆中)

実写風動画の人物の服を参照画像の服に差し替える処理を「静止画着せ替え → モーション移植」の 2 段に分解し、OSS 構成 (Qwen-Image-Edit + Wan2.2-Animate) とクローズド (Seedream / Kling O3 edit) を同一の自前生成素材で比較した記録です。人物・服とも生成モデル製なので権利的にクリーンです。

## 使用 endpoint (fal.ai)

| 役割 | endpoint | ライセンス/種別 | 単価 (検証時) |
|---|---|---|---|
| 素材 T2I | fal-ai/flux/dev | open weights | $0.025/MP |
| 素材 I2V | fal-ai/wan-i2v | open weights | $0.40/本 |
| 静止画 try-on (VTON 特化) | fal-ai/kling/v1-5/kolors-virtual-try-on | クローズド | $0.07/枚 |
| 静止画編集 (instruction) | bytedance/seedream/v5/lite/edit | クローズド | $0.035/枚 |
| 静止画編集 (instruction) | fal-ai/qwen-image-edit-2509 | Apache-2.0 | $0.03/MP |
| 動画・同シルエット | fal-ai/wan/v2.2-14b/animate/replace | open weights | $0.08/秒 |
| 動画・シルエット変化 | fal-ai/wan/v2.2-14b/animate/move | open weights | $0.08/秒 |
| 動画・クローズド対照 | fal-ai/kling-video/o3/standard/video-to-video/edit | クローズド | $0.14/秒 |

検証全体 (静止画 5 ケース + 動画 5 本 + 素材生成・再ロール込み) の実測コストは約 $3.5。

## 実行

```bash
uv venv && source .venv/bin/activate
uv pip install fal-client
FAL_KEY=... python run_pipeline.py
```

動画 1 本あたりキュー待ち込みで数分〜十数分かかります。

## 結果の要点

- 同シルエット (タータンブレザー) は全段 OSS で成立。Qwen-Image-Edit → Wan2.2-Animate replace で、柄・顔・指定外領域ともクローズド (Kling) と遜色ない
- シルエット変化 (着物) は静止画段が律速。Qwen は広袖・帯は再現するが丈が届かず、その欠陥は move mode の動画に 1 フレーム目から最終フレームまでそのまま伝播する。動画段は静止画の欠陥を救済しない
- VTON 特化型 (Kolors) は学習分布外の服型 (着物) で完全に破綻する。分布内 (ブレザー) は正確
- 品質ゲートは安い静止画段に置く。種静止画の顔品質・服の完成度が動画品質の天井を決める

## 注意

- スクリプト内のプロンプトは検証時の意図を再構成したもので、一字一句同じ文言ではありません。モデルは非決定的なので出力も検証時と完全一致はしません
- flux/dev はシードによって画像全体に強いソフトフォーカスがかかることがあります (プロンプトでは直らない)。ぼやけたらシードを引き直してください
- Kolors の入力は「人物画像 + 服画像」、Seedream / Qwen は「複数画像 + instruction」、Kling edit は「動画 + (任意で参照画像) + instruction」と入力契約が違います。schema は fal のモデルページで確認してください
