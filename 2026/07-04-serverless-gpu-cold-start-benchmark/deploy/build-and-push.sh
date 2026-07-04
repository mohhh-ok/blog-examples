#!/usr/bin/env bash
# Submit SDXL and Whisper builds to Cloud Build (project from $GCP_PROJECT_ID),
# then make the Artifact Registry repo publicly readable so RunPod (outside GCP)
# can pull.
# Prereq: gcloud auth (Cloud Build 権限持ちのアカウントで login 済み)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  source .env
fi

: "${GCP_PROJECT_ID:?GCP_PROJECT_ID must be set in .env}"
: "${GCP_REGION:?GCP_REGION must be set in .env}"

TAG="${1:-latest}"
AR_REPO="cold-start-bench"
AR_HOST="${GCP_REGION}-docker.pkg.dev"

echo "[setup] ensure Artifact Registry repo exists"
gcloud artifacts repositories describe "${AR_REPO}" \
    --location="${GCP_REGION}" --project="${GCP_PROJECT_ID}" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "${AR_REPO}" \
    --location="${GCP_REGION}" --project="${GCP_PROJECT_ID}" \
    --repository-format=docker \
    --description="Serverless GPU cold-start benchmark (blog)"

echo "[setup] grant public read on ${AR_REPO} so RunPod can pull"
gcloud artifacts repositories add-iam-policy-binding "${AR_REPO}" \
    --location="${GCP_REGION}" --project="${GCP_PROJECT_ID}" \
    --member="allUsers" \
    --role="roles/artifactregistry.reader" >/dev/null

echo "[build] SDXL (Cloud Build submit, background)"
gcloud builds submit \
  --project="${GCP_PROJECT_ID}" \
  --config=deploy/cloudbuild-sdxl.yaml \
  --substitutions="_TAG=${TAG}" \
  --async \
  .

echo "[build] Whisper (Cloud Build submit, background)"
gcloud builds submit \
  --project="${GCP_PROJECT_ID}" \
  --config=deploy/cloudbuild-whisper.yaml \
  --substitutions="_TAG=${TAG}" \
  --async \
  .

echo
echo "Submitted. Monitor with:"
echo "  gcloud builds list --project=${GCP_PROJECT_ID} --ongoing --format='table(id,status,createTime,duration)'"
echo
echo "When both finish, images will be at:"
echo "  ${AR_HOST}/${GCP_PROJECT_ID}/${AR_REPO}/sdxl:${TAG}"
echo "  ${AR_HOST}/${GCP_PROJECT_ID}/${AR_REPO}/whisper:${TAG}"
