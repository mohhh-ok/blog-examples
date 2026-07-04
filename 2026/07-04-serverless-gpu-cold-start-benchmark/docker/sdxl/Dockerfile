# SDXL Base 1.0 image with fp16 weights baked in.
# Base: PyTorch 2.11 + CUDA 12.8. cu124 だと RunPod が同 24GB pool の Blackwell
# MIG (sm_100) に fallback schedule してきたときに warmup が hang → RunPod
# deadline で kill された。cu128 で Blackwell 対応を確保 (L4 sm_89 も同じ image
# で問題なし)。
FROM pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/hf-cache \
    HF_HUB_DISABLE_TELEMETRY=1 \
    HF_HUB_ENABLE_HF_TRANSFER=1 \
    SDXL_MODEL_DIR=/models/sdxl

WORKDIR /app

# System deps kept minimal
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python deps
RUN pip install --no-cache-dir --break-system-packages \
        diffusers==0.31.0 \
        transformers==4.46.3 \
        accelerate==1.1.1 \
        safetensors==0.4.5 \
        hf_transfer==0.1.8 \
        huggingface_hub==0.26.5 \
        fastapi==0.115.5 \
        uvicorn==0.32.1 \
        pydantic==2.10.3 \
        runpod==1.7.7

# Bake SDXL fp16 weights into image (repo variant=fp16, ~6.5GB).
# Using huggingface-cli to fetch a specific variant reliably.
RUN python -c "\
from huggingface_hub import snapshot_download; \
snapshot_download( \
    repo_id='stabilityai/stable-diffusion-xl-base-1.0', \
    local_dir='/models/sdxl', \
    allow_patterns=[ \
        'model_index.json', \
        'scheduler/*', \
        'text_encoder/*fp16*', \
        'text_encoder/config.json', \
        'text_encoder_2/*fp16*', \
        'text_encoder_2/config.json', \
        'tokenizer/*', \
        'tokenizer_2/*', \
        'unet/*fp16*', \
        'unet/config.json', \
        'vae/*fp16*', \
        'vae/config.json', \
    ], \
)"

COPY handlers/sdxl_handler.py /app/handler.py

CMD ["python", "/app/handler.py"]
