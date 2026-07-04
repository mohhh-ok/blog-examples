# Serverless GPU Cold Start Benchmark

RunPod Serverless L4 vs Cloud Run GPU L4 の cold start / warm 実測。SDXL Base 1.0 と Whisper large-v3 の 2 workload。

## 動機

同一 workload の cold start を RunPod Serverless (Network Volume 構成) と Cloud Run GPU で実測して、どちらがどれだけ速いかを比較する。「RunPod Serverless の "48% cold start が 200ms 以下" の主張が本当か」を確かめる独立ベンチ。

## 測る provider

| provider | GPU | 位置付け |
|---|---|---|
| RunPod Serverless | L4 24GB | cold start ベンチ主役、FlashBoot 有効 |
| Cloud Run GPU | L4 24GB | 対照群、現行 avatar 構成 |

Modal と fal.ai は対象外。Modal は TS orchestrator との親和性が低く実採用不可、fal.ai は L4 を提供していない。

## 測る workload

**メイン: SDXL Base 1.0**
- Diffusers `StableDiffusionXLPipeline`, fp16
- VRAM ~10GB (L4 24GB に余裕で収まる)
- prompt = `"A photo of an astronaut riding a horse"`, steps=25, 1024×1024
- 独立ベンチが少なく、blog 映え

**サブ: Whisper large-v3**
- faster-whisper, fp16
- VRAM ~5GB
- 30s の英語音声 sample を transcribe
- audio 系の cold start 特性を副次的に示す

## 公平性の担保

- **同一 Dockerfile / handler コード**を両 provider で使う (BYO Docker 統一)
- **weight は image に bake** する。runtime での HF Hub download を排除して apples-to-apples を確保 (Modal のように lazy pull で速く見せる provider 独自機構は使わない)
- **同一 payload** を全 fire で使う
- **同一 region** (us-central1 or 最も近い L4 available region)

## 計測する phase

handler 内に境界 timestamp log を仕込み、以下の phase を分解する:

1. `container_start` — container 起動 (RunPod は worker init, Cloud Run は revision init)
2. `import_done` — Python imports (torch / diffusers / faster-whisper) 完了
3. `weights_loaded` — VRAM にモデル load 完了
4. `warmup_done` — 初回 CUDA kernel compile / graph capture 完了
5. `first_inference_done` — payload 処理完了
6. `return` — HTTP response 送信

既存の cold start ベンチはほとんど「total cold time」しか出していないので、内訳の分解がこの記事の独自価値。

## fire プラン

- SDXL: 2 provider × L4 × 3 fire (cold + warm×2) = **6 fire**
- Whisper: 2 provider × L4 × 3 fire = **6 fire**
- 合計 **12 fire**

cold は 15 分以上 idle 後に発火 (RunPod idle timeout / Cloud Run scale-to-zero を跨ぐ)。warm はその直後に連続 2 回。

想定コスト:
- SDXL 1 fire = ~30s @ $0.39/hr (RunPod L4) = $0.003
- Whisper 1 fire = ~5s @ $0.39/hr = $0.0005
- 12 fire 合計 ~$0.05 (fire そのものは無視できる、build/deploy の image storage が主コスト)
- image storage: RunPod は無料枠、GCP Artifact Registry は月 $0.10/GB * 15GB = $1.5/月

## 構成

```
07-04-serverless-gpu-cold-start-benchmark/
├── README.md            (このファイル)
├── docker/
│   ├── sdxl/            (SDXL Dockerfile + weight download)
│   └── whisper/         (Whisper Dockerfile + weight download)
├── handlers/
│   ├── sdxl_handler.py  (RunPod + Cloud Run 共通の inference 関数 + 両 SDK wrapper)
│   └── whisper_handler.py
├── deploy/
│   ├── runpod-*.sh      (RunPod endpoint 作成 / update)
│   └── cloudrun-*.sh    (Cloud Run deploy)
├── scripts/
│   └── fire.ts          (両 provider に打ち込む fire CLI)
├── results/
│   ├── *.jsonl          (raw fire 結果)
│   └── RESULTS.md       (集約された分析)
└── .env.example
```

## 段取り

- [ ] SDXL Dockerfile + handler (境界 log 含む)
- [ ] Whisper Dockerfile + handler
- [ ] RunPod deploy スクリプト
- [ ] Cloud Run deploy スクリプト
- [ ] Fire CLI (TS)
- [ ] 4 endpoint 全て deploy 完了
- [ ] cold + warm×2 を 4 endpoint 全てで実行
- [ ] RESULTS.md にまとめる

## 前提 (次セッションで確認済み・以下で運用)

- RunPod アカウント有り、API key は `.env` (RUNPOD_API_KEY)
- GCP は任意の個人プロジェクト (`.env` の `GCP_PROJECT_ID` に指定)
- fire コスト予算は $30-50 の範囲想定、実際は image storage が支配的で fire は誤差
- egress cost は本記事のスコープ外
