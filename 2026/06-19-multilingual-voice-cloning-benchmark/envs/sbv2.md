# Style-Bert-VITS2 JP-Extra セットアップ

> **このベンチでの役割**: 日本語の上限を示す参考値。日本語のみ生成し、F5-TTS / XTTS / OpenVoice の日本語と聴き比べる。

## 環境

- Python 3.10 推奨

## 重要: ゼロショットクローンではない

SBV2 は fine-tune 前提。「参照音声を渡すだけで声がコピーできる」F5-TTS / XTTS / OpenVoice とは違い、**数分の音声を使った学習が必要**。

そのため：

- 参照音声は **1〜3分程度の素材**が望ましい (`reference/ref_long.wav`)
- 学習に GPU 推奨。CPU でも回せるが時間がかかる

## 手順

```bash
cd envs
python3.10 -m venv sbv2
source sbv2/bin/activate

git clone https://github.com/litagin02/Style-Bert-VITS2
cd Style-Bert-VITS2
pip install -e .

# 事前学習済み bert と JP-Extra ベースモデルを取得
python initialize.py

# 1. 音声を slice (無音区切りで分割)
mkdir -p inputs/ref
cp ../../reference/ref_long.wav inputs/ref/
python slice.py --model_name ref --input_dir inputs/ref

# 2. 文字起こし (Whisper を内部で呼ぶ)
python transcribe.py --model_name ref

# 3. 学習用前処理
python preprocess_all.py --model_name ref --use_jp_extra true

# 4. 学習 (デフォルト 100 epoch、5〜30分目安)
python train_ms_jp_extra.py --config_path Data/ref/config.json

# モデルは model_assets/ref/ に出力される
cd ../..
```

## 実行

```bash
source envs/sbv2/bin/activate
python scripts/generate_style_bert_vits2.py
```

## このベンチでの位置づけ

- 「F5-TTS の日本語が壊滅した時の比較対象」
- SBV2 で出した日本語と、F5-TTS / XTTS / OpenVoice / ElevenLabs の日本語を **同じ Whisper パイプラインに通す**ことで、機械評価の上限を確認する
- 学習コストが他と非対称なのは承知の上。「ゼロショット同士の比較」と「fine-tune 込みのベスト日本語」を別軸として並べる
