# RVM vs MatAnyone 2 — Green Background Halo Comparison

対応記事: 2026-07-02 「RVMとMatAnyone2でグリーンバックの緑ハロー比較」

Mac M2 で RVM (mobilenetv3) と MatAnyone 2 を同じグリーンバック入力に通して halo 具合を A/B した記録です。

## 環境

- Mac M2 24GB（MPS）
- Python 3.11
- torch 2.12 + torchvision (MPS)

## 依存

`pyproject.toml` 参照。MatAnyone 2 の GUI/eval 系（`cchardet` / `PySide6` / `hickle`）はビルドで詰まるので入れていません。推論のみで動きます。

`torchvision.io.read_video` は新しめの torchvision で無くなっているので、`patch_matanyone2.py` で PyAV 実装に差し替えます（`run.py` から自動で当たります）。

## セットアップ

```bash
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -e .

# MatAnyone 2 と RVM の repo を隣に clone
git clone --depth 1 https://github.com/pq-yang/MatAnyone2.git ../MatAnyone2
git clone --depth 1 https://github.com/PeterL1n/RobustVideoMatting.git ../RVM

# サンプル動画（mixkit の緑背景 talking head）
curl -L -o input.mp4 https://assets.mixkit.co/videos/28287/28287-720.mp4
```

## 実行

```bash
python run.py
```

`output/` に:
- `source.webp` — 入力フレーム
- `side_white.webp`, `side_white_crop.webp` — 白背景に straight alpha 合成した A/B
- `side_red.webp` — 赤背景に合成（緑カブり強調）
- `side_fgr.webp` — fgr の raw RGB
- `side_alpha.webp` — alpha channel
- `metrics.csv` — 定量結果

## 結論（記事参照）

緑バック入力に対しては両モデルとも edge ΔG ≒ +12 の緑カブりを残します。ただし追加検証として natural background の talking head を通すと:

- **RVM**: ΔG −5.5（緑カブりが消える、わずかに赤紫寄り）
- **MatAnyone 2**: ΔG +13（緑バック時と変わらず、推論スクリプトの `bgr = [120, 255, 155]` が edge に染み出してる副作用）

つまり緑バック halo の正体は:

- RVM 側は **撮影時の物理的 green spill**（緑光が被写体に回り込む反射光）
- MatAnyone 2 側は上記に加えて **推論スクリプトのハードコード緑塗り**の残り

なのでモデル差し替えでは緑 halo は消えず、matting 後段の despill（`G = min(G, (R+B)/2)`）を alpha-gated で入れるのが実務解です。詳細は記事参照。
