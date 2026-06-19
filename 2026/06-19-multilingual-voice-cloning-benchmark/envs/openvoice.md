# OpenVoice v2 セットアップ

## 環境

- Python 3.10 推奨（3.11 でも動くが MeloTTS の依存で警告が出る場合あり）

## 手順

```bash
cd envs
python3.10 -m venv openvoice
source openvoice/bin/activate

# 1. OpenVoice 本体
git clone https://github.com/myshell-ai/OpenVoice
cd OpenVoice
pip install -e .

# 2. MeloTTS (ベース音声生成)
pip install git+https://github.com/myshell-ai/MeloTTS.git
python -m unidic download   # 日本語形態素解析辞書

# 3. checkpoints をダウンロード
# Hugging Face: myshell-ai/OpenVoiceV2
# checkpoints_v2/ ディレクトリを OpenVoice 直下に配置
# 必要なのは:
#   checkpoints_v2/converter/{config.json, checkpoint.pth}
#   checkpoints_v2/base_speakers/ses/{en,es,fr,zh,jp,kr}.pth
huggingface-cli download myshell-ai/OpenVoiceV2 \
  --local-dir checkpoints_v2 --local-dir-use-symlinks False

cd ../..
```

## 実行

```bash
source envs/openvoice/bin/activate
export OPENVOICE_ROOT=$(pwd)/envs/OpenVoice
python scripts/generate_openvoice.py
```

## サポート言語

- en / es / fr / zh / ja / ko: 対応
- **de: MeloTTS が未対応のためスキップ**

## 既知の落とし穴

- `melo.api` の import 時に nltk のデータダウンロードが走る。初回はネット必要
- ja は MeloTTS 内部で `JP` を使う。マッピングは `MELO_LANG` を参照
- `se_extractor.get_se` は VAD で参照音声を分割するので、参照音声が極端に短いと失敗する。10秒以上を推奨
