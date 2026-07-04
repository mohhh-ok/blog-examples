# 実測結果: RunPod Serverless L4 vs Cloud Run GPU L4 の cold start (n=3〜4)

計測日: 2026-07-04

## TL;DR

- **RunPod SDXL cold は 2 峰分布**: n=4 中 3 回は 12s 台、1 回だけ 61s に跳ねた (~25% の頻度で 5x 遅い)
- **Cloud Run cold は再現性が高い**: variance ±5s、n=3〜4 とも安定
- **20 min idle 後の勝敗はモデルサイズで分かれる**: SDXL は expected value で見ると RunPod ~25s vs Cloud Run 37s、Whisper は RunPod ~3s vs Cloud Run 17s
- **RunPod FlashBoot の eviction タイミングは非公開**、時間ベースではなく動的スケジューリング。ユーザから観測できるのは「時々遅い」という分布だけ

## 構成

|項目 | Cloud Run | RunPod Serverless|
|---|---|---|
|GPU | NVIDIA L4 (24GB) | NVIDIA RTX PRO 6000 Blackwell MIG 1g.24gb *|
|Region / DC | us-central1 | US-IL-1|
|min / max instances | 0 / 1 | 0 / 1|
|Idle timeout | ~15 min (scale-to-zero) | 5s (worker死) + FlashBoot snapshot|
|Weight 配置 | image bake (~15GB image) | Network Volume STANDARD 20GB (HF から seed)|
|Image | `pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime` + Diffusers/faster-whisper|
|Startup config | `--concurrency=1 --cpu=4 --memory=16Gi --no-cpu-throttling` | FLASHBOOT, queue-delay scaler|

\* RunPod は `gpuTypeIds:["NVIDIA L4"]` を指定したが、AMPERE_24 pool (24GB VRAM) の中でスケジューラが Blackwell MIG を割り当てた。PyTorch cu128 (sm_100 対応) で実行できたので測定は問題なし。ただし **L4 純比較ではない** ので注意。

## Workload

- **SDXL Base 1.0** (Diffusers, fp16、prompt="A photo of an astronaut riding a horse", 25 steps, 1024×1024)
- **Whisper large-v3** (faster-whisper, fp16、30s 英語音声を transcribe)

## 4 rounds の測定戦略

- **Round 1 (baked-weights)**: image に weight 焼き込み構成での初回計測、Cloud Run 側は probe warm を "cold" と誤認して非採用
- **Round 2 (FlashBoot warm)**: seed fire 直後 (~2 分) に fire、RunPod は snapshot 復元、Cloud Run は 25 分以上 idle 後の真 cold
- **Round 3 (20 min idle)**: Round 2 から 20 min 待って再 fire
- **Round 4 (32 min idle)**: Round 3 から 32 min 待って再 fire (blog / commit 整備に時間かかった)
- **Round 5 (20 min idle)**: Round 4 から 20 min 待って再 fire

Round 5 で Cloud Run Whisper は HuggingFace CDN の 429 rate limit (試験用 audio URL を全 fire で共有していたため) により 500 error、除外。

## 4 rounds の cold start 実測

|Round | idle | RunPod SDXL | RunPod Whisper | Cloud Run SDXL | Cloud Run Whisper|
|---|---|---|---|---|---|
|R2 | ~2 min | 12.97s | 2.49s | 39.12s | 19.45s|
|R3 | 20 min | **61.47s** | 4.72s | 34.78s | 16.79s|
|R4 | 32 min | 12.86s | 3.58s | 38.13s | 15.97s|
|R5 | 20 min | 12.22s | 3.31s | 40.65s | 500 (skip)|

## 統計まとめ

|endpoint | n | min | median | max | max/min|
|---|---|---|---|---|---|
|RunPod SDXL cold | 4 | 12.22 | 12.86 | 61.47 | **5.0x**|
|RunPod Whisper cold | 4 | 2.49 | 3.44 | 4.72 | 1.9x|
|Cloud Run SDXL cold | 4 | 34.78 | 38.63 | 40.65 | 1.17x|
|Cloud Run Whisper cold | 3 | 15.97 | 16.79 | 19.45 | 1.22x|

## Finding 1: RunPod SDXL cold のばらつきが極端

n=4 のうち R3 だけが 61.47s、他 3 回は 12.22-12.97s の狭い範囲。

|Round | idle | RunPod SDXL cold |
|---|---|---|
|R2 | ~2 min | 12.97s |
|R3 | 20 min | **61.47s** |
|R4 | 32 min | 12.86s |
|R5 | 20 min | 12.22s |

61s は seed 91s (fresh 状態、HF から weight download を含む) から HF download 分 ~30s を引いた値に近い。**発生頻度**: n=4 で 1 回、真の頻度は未確定。

## Finding 2: 時間ベースの単純な cache TTL ではなさそう

R3 (20 min) = 61s だが R5 (20 min) = 12s。同じ 20 min idle でも結果が違う。R4 の 32 min idle は 12s。**より長い idle が確実に遅くなるわけではない**。RunPod docs / community も「FlashBoot eviction は非公開、動的スケジューリング」と回答していて、ユーザ側から時間で予測はできない。

## Finding 3: RunPod Whisper は狭い範囲

n=4 とも 2.49-4.72s の狭い範囲、変動 1.9x のみ。SDXL のような跳ねは観測されず。

## Finding 4: Cloud Run cold は今回の 4 発で ±5s に収まった

|endpoint | n | 実測範囲 | max/min|
|---|---|---|---|
|Cloud Run SDXL cold | 4 | 34.78 - 40.65s | 1.17x|
|Cloud Run Whisper cold | 3 | 15.97 - 19.45s | 1.22x|

RunPod SDXL は同じ 4 発で 5x 変動、Cloud Run は 1.2x 未満に収まった。ただし n=4 なので「Cloud Run cold は本質的に安定」と一般化するには証拠不足で、より長い観測窓と大サンプルが要る。

## Finding 5: 中央値 vs 最悪ケース (今回の観測範囲)

|endpoint | RunPod median (n=4) | Cloud Run median (n=3-4) | RunPod worst (max) | Cloud Run worst|
|---|---|---|---|---|
|SDXL cold | 12.86s | 38.63s | 61.47s | 40.65s|
|Whisper cold | 3.44s | 16.79s | 4.72s | 19.45s|

**今回の中央値では RunPod のほうが速い**。ただし **SDXL の最悪ケースは Cloud Run のほうが速かった** (61s vs 40s)。ユーザ体感の p50 なら RunPod、tail に耐える設計を組むなら Cloud Run — ただしこの判断は n=4 の一時観測に基づく。

## Finding 6: Registry proximity effect (Round 1 vs Round 2 で確認)

image bake 構成 (Round 1、破棄) vs Network Volume 構成 (Round 2):

|構成 | 場所 | SDXL cold|
|---|---|---|
|image bake | 15GB image を us-central1 AR → RunPod US-NE-1 に pull | 207.65s|
|Network Volume seed | 4GB image pull + HF から volume に 6.5GB download | 91.57s|

**AR → RunPod worker の pull より、HF Hub → volume の download の方が速い** (hf_transfer 有効時、HF は CDN 分散配置されているため)。RunPod で cold を早くしたければ、image を軽く保って weight は Network Volume に置くのが正解。

## Finding 7: Cloud Run redeploy 直後の "偽 cold" は絶対に踏むな

Round 1 で Cloud Run SDXL cold を "1.88s" と観測したが、redeploy 実行 5 分後の fire だったため、startup probe 用に立った container がまだ生存していた。**真 cold を測るには 15 min 以上のクールダウンが必要**。この blog を書く上で最も注意した落とし穴。

## 選び方の判断軸

|状況 | 推奨|
|---|---|
|10GB+ モデル、リクエストが 20 min 以上開くことがある | Cloud Run (tail latency 安定)|
|3GB 以下のモデル、あるいはリクエスト間隔が短い | RunPod (FlashBoot 恩恵)|
|SLO を細かく切りたい | Cloud Run|
|1st cold の速さを最優先 (常時アクティブなサービス) | RunPod|
|複数モデルを 1 endpoint で切り替える | RunPod (Network Volume に weight を並べておく)|
|ユーザ体感の p50 を速くしたい | RunPod (75% の頻度で高速)|
|ユーザ体感の p95 / p99 を安定させたい | Cloud Run|

## 全 fire raw data (n=4 分)

### Round 2 (FlashBoot warm 直後)
|endpoint | cold | warm 1 | warm 2|
|---|---|---|---|
|RunPod SDXL | 12.97 | 10.61 | 12.60|
|RunPod Whisper | 2.49 | 1.59 | 2.31|
|Cloud Run SDXL | 39.12 | 14.54 | 15.60|
|Cloud Run Whisper | 19.45 | 1.14 | 1.14|

### Round 3 (20 min idle)
|endpoint | cold | warm 1 | warm 2|
|---|---|---|---|
|RunPod SDXL | 61.47 | 11.67 | 10.91|
|RunPod Whisper | 4.72 | 1.85 | 2.44|
|Cloud Run SDXL | 34.78 | 11.98 | 12.24|
|Cloud Run Whisper | 16.79 | 1.13 | 1.13|

### Round 4 (32 min idle)
|endpoint | cold | warm 1 | warm 2|
|---|---|---|---|
|RunPod SDXL | 12.86 | 12.44 | 10.83|
|RunPod Whisper | 3.58 | 2.37 | 2.32|
|Cloud Run SDXL | 38.13 | 12.85 | 14.42|
|Cloud Run Whisper | 15.97 | 1.17 | 1.14|

### Round 5 (20 min idle)
|endpoint | cold | warm 1 | warm 2|
|---|---|---|---|
|RunPod SDXL | 12.22 | 10.72 | 10.72|
|RunPod Whisper | 3.31 | 1.47 | 2.32|
|Cloud Run SDXL | 40.65 | 16.72 | 13.15|
|Cloud Run Whisper | 500 error | 500 error | 500 error|

Cloud Run Whisper R5 の 500 は HF Hub の 429 (Narsil/asr_dummy 4 rounds x 3 fires = 12 fetches の rate limit 発動)。cold start 性能とは無関係。

## Seed fires (RunPod, Network Volume 初回 download 込み)
|time | model | wall|
|---|---|---|
|07:46:38 | runpod/sdxl | 91.57s|
|07:46:38 | runpod/whisper | 66.45s|

## Caveats

- **RunPod GPU の実体は Blackwell MIG**: 純 L4 vs L4 の比較ではない
- **n=3〜4 per condition**: 統計的信頼区間は取れず、傾向のみ。RunPod SDXL の 61s が 1/4 で出た値は sampling 精度が低い
- **FlashBoot cache eviction ロジックは非公開**、時間だけでは予測不可
- **client の地理**: 東京の Mac からで、RunPod US-IL-1 / Cloud Run us-central1 とも約 150ms RTT
- **PyTorch 2.11 + cu128 前提**: SDXL は cu124 で試すと Blackwell MIG で hang するので、Blackwell に fallback される可能性のある RunPod では cu128+ image が必須
- **HF Hub の rate limit**: 同一 audio URL を全 fire で使うと Cloud Run 側 IP がまとめて弾かれる。production では audio を image / volume に固定するか、S3/GCS 経由で fetch する
