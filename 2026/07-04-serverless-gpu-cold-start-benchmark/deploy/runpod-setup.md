# RunPod Serverless endpoint setup

`build-and-push.sh` で Cloud Build を submit し、Artifact Registry に image が push され
public read 権限が付いた後の、RunPod 側の endpoint 作成手順。

image 参照 (public、Docker Hub 感覚で pull できる):

```
us-central1-docker.pkg.dev/${GCP_PROJECT_ID}/cold-start-bench/sdxl:latest
us-central1-docker.pkg.dev/${GCP_PROJECT_ID}/cold-start-bench/whisper:latest
```

## 1. Endpoint 作成 (console)

https://www.runpod.io/console/serverless から `New Endpoint`。

SDXL / Whisper それぞれで別 endpoint を作る。

- **Endpoint Name**: `sdxl-cold-start-bench` / `whisper-cold-start-bench`
- **Container Image**: 上記の AR パス
- **Container Registry Credentials**: 不要 (AR repo に allUsers reader 付与済み)
- **Container Disk**: 30GB (SDXL は image ~15GB、Whisper は ~7GB)
- **GPU Type**: **NVIDIA L4** (24GB)
- **Workers**:
  - Min: **0** (scale-to-zero、cold start を毎回発生させる)
  - Max: **1**
  - Idle Timeout: **5s** (fire 後すぐ scale down)
- **Advanced**:
  - **FlashBoot**: **On** (RunPod 独自の cold start 高速化。まずは On で計測)
  - **Scaler Type**: Queue Delay
  - **Container Start Command**: (Dockerfile CMD を使うので空欄)
  - **Environment Variables**:
    - `RUNPOD_MODE=1`

作成後、Endpoint ID (`abc123xyz` のような文字列) をコピーして `.env` の `RUNPOD_SDXL_ENDPOINT_ID` / `RUNPOD_WHISPER_ENDPOINT_ID` に入れる。

## 2. FlashBoot Off 版も作る (オプション、ベンチマークの比較として)

同じ image で `-noflashboot` suffix の endpoint を追加作成、FlashBoot: Off に。fire スクリプトから両 endpoint を叩けば「FlashBoot 効果」の実測が取れる。

## 3. Fire

`.env` に endpoint ID をセット後、`pnpm fire runpod sdxl cold` などで発火。詳細は `scripts/fire.ts` を参照。
