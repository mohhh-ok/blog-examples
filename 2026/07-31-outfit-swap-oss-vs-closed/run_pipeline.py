"""AI 動画着せ替え: 全段 OSS パイプライン vs クローズドモデルの比較検証。

素材 (服・人物) をすべて生成モデルで自前調達し、
  1. 静止画段: 服参照画像を人物静止画に着せ替える
  2. 動画段: 着せ替え済み静止画を元動画のモーションで動画化する
の 2 段分解で、OSS (Qwen-Image-Edit + Wan2.2-Animate) と
クローズド (Seedream / Kling O3 edit) を同一素材で比較する。

実行には環境変数 FAL_KEY が必要。
    uv pip install fal-client
    FAL_KEY=... python run_pipeline.py
"""

import fal_client

OUT = {}


def gen(name: str, endpoint: str, arguments: dict) -> dict:
    """fal endpoint を同期実行して結果 (url を含む dict) を返す。"""
    print(f"[{name}] {endpoint} ...")
    result = fal_client.subscribe(endpoint, arguments=arguments)
    OUT[name] = result
    print(f"[{name}] done")
    return result


def first_url(result: dict) -> str:
    for key in ("images", "image", "video"):
        value = result.get(key)
        if isinstance(value, list):
            return value[0]["url"]
        if isinstance(value, dict):
            return value["url"]
    raise KeyError(f"no media url in result: {list(result)}")


# ---------------------------------------------------------------
# Phase 1: 素材の自前生成 (権利クリーン化のため人物・服とも生成物)
# ---------------------------------------------------------------

# 服参照画像は「前を閉じた flat lay・白背景・服単体・マネキン不可視」で作る。
# マネキンが写っていると胴体・首がインナーや白線として出力に漏れる。
ref_tartan = gen("ref_tartan", "fal-ai/flux/dev", {
    "prompt": (
        "product photography flat lay of a tartan check blazer, "
        "red navy and yellow plaid pattern, gold buttons, fully buttoned, "
        "garment only, no mannequin, no person, pure white background, sharp focus"
    ),
    "image_size": "square_hd",
})

# flux/dev はシード次第で画像全体に強いソフトフォーカスがかかることがある
# (プロンプトでは直らない)。ぼやけたらシードを変えて引き直す。
ref_kimono = gen("ref_kimono", "fal-ai/flux/dev", {
    "prompt": (
        "product photography flat lay of a traditional japanese kimono, "
        "navy blue fabric with dark red obi belt, ankle-length, wide sleeves, "
        "garment only, no mannequin, no person, pure white background, sharp focus"
    ),
    "image_size": "square_hd",
    "num_inference_steps": 45,
    "seed": 101,
})

# 種静止画。顔の品質・解像度が最終動画の品質を支配するため、
# ここが唯一の品質ゲート。複数枚生成して最良を選ぶ。
seed_portrait = gen("seed_portrait", "fal-ai/flux/dev", {
    "prompt": (
        "full body studio photograph of a woman standing, "
        "plain dark jacket and dark trousers, white studio background, "
        "face clearly visible, natural pose, sharp focus"
    ),
    "image_size": "portrait_16_9",
    "num_inference_steps": 40,
})

# 種静止画を 5 秒動画化。このモーションが動画段の共通入力になる。
source_video = gen("source_video", "fal-ai/wan-i2v", {
    "prompt": "the woman sways gently and moves her arms naturally, white studio",
    "image_url": first_url(seed_portrait),
    "resolution": "720p",
    "aspect_ratio": "9:16",
})

# ---------------------------------------------------------------
# Phase 2: 静止画着せ替え (人物静止画 x 服参照画像)
# ---------------------------------------------------------------

# VTON 特化型: 洋服 (学習分布内) は正確、着物 (分布外) は破綻する。
s1_kolors_tartan = gen("s1", "fal-ai/kling/v1-5/kolors-virtual-try-on", {
    "human_image_url": first_url(seed_portrait),
    "garment_image_url": first_url(ref_tartan),
})
s2_kolors_kimono = gen("s2", "fal-ai/kling/v1-5/kolors-virtual-try-on", {
    "human_image_url": first_url(seed_portrait),
    "garment_image_url": first_url(ref_kimono),
})

# instruction 編集型 (クローズド): シルエットが変わる服も扱える。
s3_seedream_kimono = gen("s3", "bytedance/seedream/v5/lite/edit", {
    "prompt": (
        "dress the woman in the ankle-length navy kimono with the red obi belt "
        "from the second image, keep her face, hair and the background unchanged"
    ),
    "image_urls": [first_url(seed_portrait), first_url(ref_kimono)],
})

# instruction 編集型 (OSS, Apache-2.0): 全段 OSS 化の鍵。
s4_qwen_tartan = gen("s4", "fal-ai/qwen-image-edit-2509", {
    "prompt": (
        "dress the woman in the tartan blazer from the second image, "
        "keep her face, hair, trousers and the background unchanged"
    ),
    "image_urls": [first_url(seed_portrait), first_url(ref_tartan)],
})
s5_qwen_kimono = gen("s5", "fal-ai/qwen-image-edit-2509", {
    "prompt": (
        "dress the woman in the ankle-length navy kimono with the red obi belt "
        "from the second image, keep her face, hair and the background unchanged"
    ),
    "image_urls": [first_url(seed_portrait), first_url(ref_kimono)],
})

# ---------------------------------------------------------------
# Phase 3: 動画着せ替え
# ---------------------------------------------------------------

# replace mode: 元動画の人物マスク内に合成する。背景・画作りを完全保持するが、
# 元の服の輪郭から外に出る服 (着物の袂・裾) は構造的に描けない。
# → 同シルエットの差し替え専用。
v1 = gen("v1_replace_tartan", "fal-ai/wan/v2.2-14b/animate/replace", {
    "video_url": first_url(source_video),
    "image_url": first_url(s4_qwen_tartan),
    "resolution": "720p",
})

# move (animation) mode: 種静止画の世界をベースにモーションだけ移植する。
# シルエット拘束が無い代わりに、種静止画の欠陥もそのまま動画化される
# (丈が足りない等は動画段では救済されない)。
v2 = gen("v2_move_kimono_seedream", "fal-ai/wan/v2.2-14b/animate/move", {
    "video_url": first_url(source_video),
    "image_url": first_url(s3_seedream_kimono),
    "resolution": "720p",
})
v5 = gen("v5_move_kimono_qwen", "fal-ai/wan/v2.2-14b/animate/move", {
    "video_url": first_url(source_video),
    "image_url": first_url(s5_qwen_kimono),
    "resolution": "720p",
})

# クローズド対照: Kling O3 edit は 1 endpoint で参照画像もプロンプトも
# シルエット変化も吸収する。
v3 = gen("v3_kling_tartan", "fal-ai/kling-video/o3/standard/video-to-video/edit", {
    "video_url": first_url(source_video),
    "image_urls": [first_url(ref_tartan)],
    "prompt": (
        "replace her jacket with the tartan blazer from @Image1, "
        "keep her face, trousers, background and motion unchanged"
    ),
})
v4 = gen("v4_kling_kimono", "fal-ai/kling-video/o3/standard/video-to-video/edit", {
    "video_url": first_url(source_video),
    "prompt": (
        "replace her outfit with an ankle-length navy kimono with a red obi belt, "
        "keep her face, background and motion unchanged"
    ),
})

for name, result in OUT.items():
    print(name, first_url(result))
