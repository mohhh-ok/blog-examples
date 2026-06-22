# Fun-CosyVoice 3 セットアップ

Apache 2.0 ライセンス、商用可。Alibaba FunAudioLLM。
multilingual zero-shot voice clone、9 言語 (zh/en/ja/ko/de/es/fr/it/ru) + 18+ 中国方言を公式サポート。
2025-12 正式リリース、bi-directional streaming ~150ms。

## 環境

- Python 3.10 推奨 (公式 README に明記)。本リポは pyenv の 3.11.8 で動作確認
- Mac (CPU/MPS) で動く。CUDA があれば GPU 推論可。
- ディスク 〜10GB (model 0.5B + Matcha-TTS 等の依存)

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

# 3. pretrained_models をダウンロード
# Fun-CosyVoice 3.0 (multilingual zero-shot, 9 言語)
python -c "from modelscope import snapshot_download; \
  snapshot_download('FunAudioLLM/Fun-CosyVoice3-0.5B-2512', \
    local_dir='pretrained_models/Fun-CosyVoice3-0.5B')"

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
