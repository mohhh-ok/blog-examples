# Fun-CosyVoice 3 セットアップ

Apache 2.0 ライセンス、商用可。Alibaba FunAudioLLM。
multilingual zero-shot voice clone、9 言語 (zh/en/ja/ko/de/es/fr/it/ru) + 18+ 中国方言を公式サポート。
2025-12 正式リリース、bi-directional streaming ~150ms。

## 環境

- Python 3.10 推奨 (公式 README に明記)。本リポは pyenv の 3.11.8 で動作確認
- Mac (CPU 推論) で動く。**本リポは Mac CPU のみ前提**。GPU 検証は別プロジェクトで扱う
- ディスク 〜10GB (model 0.5B + Matcha-TTS 等の依存)
- **weights は `/Volumes/UGREEN_1TB/models/cosyvoice/` に集約**し、プロジェクト側からは `envs/CosyVoice/pretrained_models/` 配下の symlink で参照する (内蔵 SSD 温存。実行前にマウントガード必須)

## GPU 対応の方針 (本リポでは触らない)

`generate_cosyvoice3.py` は CPU 固定で書いてある。GPU 化は本プロジェクトのスコープ外。
理由を残しておく:

- CosyVoice 3 の device 判定は `cuda if torch.cuda.is_available() else cpu` の二択。
  Apple Silicon の **MPS パスは無い** ので、Mac では CPU しか選べない
- fp16 / TensorRT / vLLM などの最適化フラグは CUDA 専用 (`load_vllm=False`,
  `load_trt=False`, `fp16=False` を明示)
- CUDA GPU を使う場合は本リポではなく別プロジェクト (production 想定) で
  Modal / RunPod / Lambda / Colab A100 などにデプロイして検証する
- 本プロジェクトの目的は「商用 voice clone provider の品質比較」なので、
  推論速度は判定基準に入れていない (slot 上限・単価・WER のみで判定)

## DL に時間がかかることについて

`pretrained_models/Fun-CosyVoice3-0.5B` は **~6GB 強**。modelscope.cn 経由で
日本から落とすと、ファイルによって速度が **200kB/s〜5MB/s と最大 25 倍ぶれる**
(本リポの実走で確認)。トータル **30 分〜90 分**を見込んでおくこと。

時間短縮の選択肢:

- **HuggingFace ミラーから DL**: `huggingface-cli download FunAudioLLM/Fun-CosyVoice3-0.5B-2512 \
  --local-dir pretrained_models/Fun-CosyVoice3-0.5B` で modelscope と同じ重みが取れる。
  日本からは HF の方が速いことが多い
- **`llm.rl.pt` をスキップ**: RL 強化版 (~1.89GB)。base 推論には不要なので
  `ignore_file_pattern=['llm.rl.pt']` を `snapshot_download()` に渡すと
  ~30 分節約できる。品質比較する場合のみ DL する

## 手順

```bash
cd envs
# venv 名は `cosyvoice-venv`。`cosyvoice` だと case-insensitive APFS で
# 後の `git clone CosyVoice` (大文字) と衝突する。
python3.11 -m venv cosyvoice-venv
source cosyvoice-venv/bin/activate

# pip の build-isolation 内で最新 setuptools が使われ、
# openai-whisper==20231117 の setup.py が pkg_resources 不在で落ちる。
# venv 側で setuptools<76 を入れ、以後 --no-build-isolation で固定する。
pip install --upgrade pip wheel 'setuptools<76'

# 1. 本体 + 必須サブモジュール (Matcha-TTS は third_party/ に入る)
git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice
# サブモジュール忘れた場合
git submodule update --init --recursive

# 2. 依存
# requirements.txt の numpy==1.26.4 / torch==2.3.1 を先に pin して入れる。
# (whisper を裸で入れると numpy 2.x が来て pyworld 0.3.4 のビルドが壊れる)
pip install 'numpy==1.26.4' 'torch==2.3.1' 'torchaudio==2.3.1'
pip install --no-build-isolation -r requirements.txt

# 3. pretrained_models をダウンロード (~6GB、30〜90 分)
# Fun-CosyVoice 3.0 (multilingual zero-shot, 9 言語)
# llm.rl.pt は RL 強化版で base 推論には不要なのでスキップする
# weights は UGREEN_1TB に集約し、プロジェクト側は symlink で参照する。
[ -d /Volumes/UGREEN_1TB/models ] || { echo "UGREEN_1TB not mounted"; exit 1; }
mkdir -p /Volumes/UGREEN_1TB/models/cosyvoice pretrained_models
python -c "from modelscope import snapshot_download; \
  snapshot_download('FunAudioLLM/Fun-CosyVoice3-0.5B-2512', \
    local_dir='/Volumes/UGREEN_1TB/models/cosyvoice/Fun-CosyVoice3-0.5B', \
    ignore_file_pattern=['llm.rl.pt'])"
ln -sf /Volumes/UGREEN_1TB/models/cosyvoice/Fun-CosyVoice3-0.5B \
  pretrained_models/Fun-CosyVoice3-0.5B

# CosyVoice 2 を併用する場合 (本ベンチでは JA 用に v2 も使う)
# python -c "from modelscope import snapshot_download; \
#   snapshot_download('iic/CosyVoice2-0.5B', \
#     local_dir='/Volumes/UGREEN_1TB/models/cosyvoice/CosyVoice2-0.5B')"
# ln -sf /Volumes/UGREEN_1TB/models/cosyvoice/CosyVoice2-0.5B \
#   pretrained_models/CosyVoice2-0.5B

cd ../..
```

## 実行

```bash
source envs/cosyvoice-venv/bin/activate
export COSYVOICE_ROOT=$(pwd)/envs/CosyVoice
python scripts/generate_cosyvoice3.py
```

## サポート言語

- 公式 9 言語: zh / en / ja / ko / de / es / fr / it / ru
- 中国方言 18+: 広東 / 閩南 / 四川 / 東北 etc
- 06-19 の 7 言語 (zh/en/ja/ko/de/es/fr) は全て公式カバー範囲内

## 既知の落とし穴

- **APFS case-insensitive 衝突**: venv 名 `cosyvoice` と `git clone CosyVoice`
  が同じパスに着地して失敗する。venv 側を `cosyvoice-venv` にする。
- **setuptools 82 で `pkg_resources` 削除**: pip の build-isolation 内で
  最新 setuptools が拾われ、`openai-whisper==20231117` の setup.py がロードできず
  build wheel が落ちる。`pip install 'setuptools<76'` を venv に入れた上で
  `pip install --no-build-isolation -r requirements.txt` で venv 側 setuptools を使わせる。
- **numpy 2.x で pyworld 0.3.4 が壊れる**: `_PyArray_Descr.subarray` 削除の
  影響で C++ build がエラー。requirements.txt の `numpy==1.26.4` / `torch==2.3.1` を
  先に pin で入れてから -r する。
- `third_party/Matcha-TTS` を sys.path に通さないと `cosyvoice.cli.cosyvoice` の
  import が落ちる。`generate_cosyvoice3.py` で先頭に入れている。
- vLLM/TensorRT 系の最適化フラグは Mac で動かないので `load_vllm=False`,
  `load_trt=False`, `fp16=False` を明示する。
- 06-19 で見送った F5-TTS と同じく、reference のサンプリングレートは 16kHz。
  `load_wav(str(REF), 16000)` で揃える。

## ライセンス

Apache 2.0。code (GitHub `FunAudioLLM/CosyVoice`) / weights (HF `FunAudioLLM/Fun-CosyVoice3-0.5B-2512`) ともに Apache-2.0 を確認済み。生成音声を SaaS で配信して問題なし。NOTICE/LICENSE の同梱を忘れない。

多言語 voice clone OSS で「商用 OK + JP 動く」を満たす選択肢はほぼ本モデル一択 (XTTS-v2 は Coqui 解散で商用契約不可、Fish Speech open weights は NC、OpenVoice v2 / Chatterbox は MIT だが JP 品質が劣る)。
