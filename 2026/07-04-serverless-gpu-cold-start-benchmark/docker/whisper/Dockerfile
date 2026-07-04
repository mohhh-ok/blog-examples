# Whisper large-v3 (faster-whisper) image with weights baked in.
# faster-whisper needs CTranslate2 which links to CUDA/cuDNN — base image provides both.
# cu128 に統一 (RunPod が Blackwell MIG に schedule してきても動くよう SDXL と揃える)。
FROM pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/hf-cache \
    HF_HUB_DISABLE_TELEMETRY=1 \
    HF_HUB_ENABLE_HF_TRANSFER=1 \
    WHISPER_MODEL_DIR=/models/whisper

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --break-system-packages \
        faster-whisper==1.1.0 \
        hf_transfer==0.1.8 \
        huggingface_hub==0.26.5 \
        numpy==1.26.4 \
        fastapi==0.115.5 \
        uvicorn==0.32.1 \
        pydantic==2.10.3 \
        runpod==1.7.7

RUN python -c "\
from huggingface_hub import snapshot_download; \
snapshot_download( \
    repo_id='Systran/faster-whisper-large-v3', \
    local_dir='/models/whisper', \
)"

COPY handlers/whisper_handler.py /app/handler.py

CMD ["python", "/app/handler.py"]
