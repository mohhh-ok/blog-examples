#!/usr/bin/env bash
# Deploy SDXL / Whisper to Cloud Run GPU L4 with concurrency=1 / cpu=4 / memory=16Gi.
# Prereq: build-and-push.sh 済み。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  source .env
fi

: "${GCP_PROJECT_ID:?GCP_PROJECT_ID must be set}"
: "${GCP_REGION:?GCP_REGION must be set}"

TAG="${1:-latest}"
AR_REPO="cold-start-bench"
AR_HOST="${GCP_REGION}-docker.pkg.dev"

SDXL_IMAGE="${AR_HOST}/${GCP_PROJECT_ID}/${AR_REPO}/sdxl:${TAG}"
WHISPER_IMAGE="${AR_HOST}/${GCP_PROJECT_ID}/${AR_REPO}/whisper:${TAG}"

deploy() {
  local name="$1"
  local image="$2"
  # avatar-inference と同じ Cloud Run GPU L4 sizing:
  #   --cpu=4 --memory=16Gi --concurrency=1 --min-instances=0 --max-instances=1
  #   --no-gpu-zonal-redundancy --no-cpu-throttling
  # timeout は 600s (SDXL cold で余裕を持たせる).
  gcloud run deploy "${name}" \
    --image="${image}" \
    --region="${GCP_REGION}" \
    --project="${GCP_PROJECT_ID}" \
    --platform=managed \
    --allow-unauthenticated \
    --port=8080 \
    --memory=16Gi \
    --cpu=4 \
    --max-instances=1 \
    --min-instances=0 \
    --concurrency=1 \
    --timeout=600 \
    --gpu=1 \
    --gpu-type=nvidia-l4 \
    --no-gpu-zonal-redundancy \
    --no-cpu-throttling
}

echo "[deploy] SDXL"
deploy sdxl-cold-start-bench "${SDXL_IMAGE}"

echo "[deploy] Whisper"
deploy whisper-cold-start-bench "${WHISPER_IMAGE}"

SDXL_URL=$(gcloud run services describe sdxl-cold-start-bench \
  --region="${GCP_REGION}" --project="${GCP_PROJECT_ID}" --format='value(status.url)')
WHISPER_URL=$(gcloud run services describe whisper-cold-start-bench \
  --region="${GCP_REGION}" --project="${GCP_PROJECT_ID}" --format='value(status.url)')

echo
echo "Done."
echo "  SDXL:    ${SDXL_URL}"
echo "  Whisper: ${WHISPER_URL}"
echo
echo "Add these to .env:"
echo "  CLOUDRUN_SDXL_URL=${SDXL_URL}"
echo "  CLOUDRUN_WHISPER_URL=${WHISPER_URL}"
