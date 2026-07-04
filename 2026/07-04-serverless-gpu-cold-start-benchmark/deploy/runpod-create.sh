#!/usr/bin/env bash
# Create RunPod Serverless templates + endpoints via REST API.
# Requires RunPod balance ≥ $0.01 (else create-endpoint returns 500).
# Writes the two endpoint IDs into .env in-place.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source .env
: "${RUNPOD_API_KEY:?}"
: "${GCP_PROJECT_ID:?}"

AR_HOST="us-central1-docker.pkg.dev"
AR_REPO="cold-start-bench"
SDXL_IMAGE="${AR_HOST}/${GCP_PROJECT_ID}/${AR_REPO}/sdxl:latest"
WHISPER_IMAGE="${AR_HOST}/${GCP_PROJECT_ID}/${AR_REPO}/whisper:latest"

API="https://rest.runpod.io/v1"
AUTH="Authorization: Bearer ${RUNPOD_API_KEY}"
CT="Content-Type: application/json"

# --- create template ---
create_template() {
  local name="$1" image="$2"
  local body
  body=$(cat <<JSON
{
  "name": "${name}",
  "imageName": "${image}",
  "isServerless": true,
  "category": "NVIDIA",
  "containerDiskInGb": 30,
  "volumeInGb": 0,
  "env": {"RUNPOD_MODE": "1"},
  "ports": []
}
JSON
)
  curl -sS -H "${AUTH}" -H "${CT}" -X POST "${API}/templates" -d "${body}"
}

# --- create endpoint ---
create_endpoint() {
  local name="$1" template_id="$2"
  local body
  body=$(cat <<JSON
{
  "name": "${name}",
  "templateId": "${template_id}",
  "computeType": "GPU",
  "gpuTypeIds": ["NVIDIA L4"],
  "gpuCount": 1,
  "workersMin": 0,
  "workersMax": 1,
  "idleTimeout": 5,
  "flashboot": true,
  "scalerType": "QUEUE_DELAY",
  "scalerValue": 4,
  "executionTimeoutMs": 600000
}
JSON
)
  curl -sS -H "${AUTH}" -H "${CT}" -X POST "${API}/endpoints" -d "${body}"
}

echo "[template] SDXL"
SDXL_TPL=$(create_template "sdxl-cold-start-bench" "${SDXL_IMAGE}" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("id") or d.get("error") or d)')
echo "  templateId=${SDXL_TPL}"

echo "[template] Whisper"
WHISPER_TPL=$(create_template "whisper-cold-start-bench" "${WHISPER_IMAGE}" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("id") or d.get("error") or d)')
echo "  templateId=${WHISPER_TPL}"

echo "[endpoint] SDXL"
SDXL_EP=$(create_endpoint "sdxl-cold-start-bench" "${SDXL_TPL}" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("id") or d.get("error") or d)')
echo "  endpointId=${SDXL_EP}"

echo "[endpoint] Whisper"
WHISPER_EP=$(create_endpoint "whisper-cold-start-bench" "${WHISPER_TPL}" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("id") or d.get("error") or d)')
echo "  endpointId=${WHISPER_EP}"

sed -i '' "s|^RUNPOD_SDXL_ENDPOINT_ID=.*|RUNPOD_SDXL_ENDPOINT_ID=${SDXL_EP}|" .env
sed -i '' "s|^RUNPOD_WHISPER_ENDPOINT_ID=.*|RUNPOD_WHISPER_ENDPOINT_ID=${WHISPER_EP}|" .env

echo
echo "Wrote endpoint IDs to .env:"
grep '^RUNPOD_.*ENDPOINT_ID' .env
