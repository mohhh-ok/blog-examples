"""SDXL Base 1.0 handler. Same inference() reused by RunPod and Cloud Run wrappers.

Phase timestamps (monotonic seconds from Python process start) are attached to every
response so the fire CLI can subtract from client-side wall clock to derive the
container_init portion of cold start.
"""

import time

PROCESS_START_MONO = time.monotonic()
PROCESS_START_EPOCH = time.time()

import base64
import io
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sdxl")

log.info("process_start epoch=%.6f", PROCESS_START_EPOCH)

import torch
from diffusers import StableDiffusionXLPipeline

IMPORT_DONE_MONO = time.monotonic()
log.info("import_done +%.3fs", IMPORT_DONE_MONO - PROCESS_START_MONO)

MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"
LOCAL_MODEL_DIR = os.environ.get("SDXL_MODEL_DIR", "/models/sdxl")

WEIGHT_PATTERNS = [
    "model_index.json",
    "scheduler/*",
    "text_encoder/config.json",
    "text_encoder/*fp16*",
    "text_encoder_2/config.json",
    "text_encoder_2/*fp16*",
    "tokenizer/*",
    "tokenizer_2/*",
    "unet/config.json",
    "unet/*fp16*",
    "vae/config.json",
    "vae/*fp16*",
]


def _ensure_weights() -> None:
    marker = os.path.join(LOCAL_MODEL_DIR, "model_index.json")
    if os.path.exists(marker):
        log.info("weights present at %s", LOCAL_MODEL_DIR)
        return
    log.info("downloading weights to %s (first-time volume seed)", LOCAL_MODEL_DIR)
    from huggingface_hub import snapshot_download

    os.makedirs(LOCAL_MODEL_DIR, exist_ok=True)
    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=LOCAL_MODEL_DIR,
        allow_patterns=WEIGHT_PATTERNS,
    )


_ensure_weights()
WEIGHTS_READY_MONO = time.monotonic()
log.info("weights_ready +%.3fs", WEIGHTS_READY_MONO - PROCESS_START_MONO)


def _load_pipeline() -> StableDiffusionXLPipeline:
    log.info("loading pipeline from %s", LOCAL_MODEL_DIR)
    pipe = StableDiffusionXLPipeline.from_pretrained(
        LOCAL_MODEL_DIR,
        torch_dtype=torch.float16,
        use_safetensors=True,
        variant="fp16",
    )
    return pipe.to("cuda")


PIPE = _load_pipeline()
WEIGHTS_LOADED_MONO = time.monotonic()
log.info("weights_loaded +%.3fs", WEIGHTS_LOADED_MONO - PROCESS_START_MONO)


def _warmup() -> None:
    with torch.inference_mode():
        PIPE(prompt="warmup", num_inference_steps=1, guidance_scale=0.0, width=512, height=512).images[0]


_warmup()
WARMUP_DONE_MONO = time.monotonic()
log.info("warmup_done +%.3fs", WARMUP_DONE_MONO - PROCESS_START_MONO)


def inference(prompt: str, steps: int = 25, width: int = 1024, height: int = 1024) -> dict:
    inference_started_mono = time.monotonic()
    with torch.inference_mode():
        image = PIPE(prompt=prompt, num_inference_steps=steps, width=width, height=height).images[0]
    inference_done_mono = time.monotonic()
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return_mono = time.monotonic()
    return {
        "image_b64": b64,
        "phase_seconds": {
            "python_start_to_import_done": IMPORT_DONE_MONO - PROCESS_START_MONO,
            "python_start_to_weights_loaded": WEIGHTS_LOADED_MONO - PROCESS_START_MONO,
            "python_start_to_warmup_done": WARMUP_DONE_MONO - PROCESS_START_MONO,
            "inference_only": inference_done_mono - inference_started_mono,
            "python_start_to_return": return_mono - PROCESS_START_MONO,
        },
        "process_start_epoch": PROCESS_START_EPOCH,
        "server_return_epoch": time.time(),
    }


def _main() -> None:
    if os.environ.get("RUNPOD_MODE") == "1":
        import runpod

        def runpod_handler(job: dict) -> dict:
            payload = job.get("input") or {}
            return inference(
                prompt=payload.get("prompt", "A photo of an astronaut riding a horse"),
                steps=int(payload.get("steps", 25)),
                width=int(payload.get("width", 1024)),
                height=int(payload.get("height", 1024)),
            )

        log.info("starting runpod.serverless")
        runpod.serverless.start({"handler": runpod_handler})
        return

    from fastapi import FastAPI
    from pydantic import BaseModel
    import uvicorn

    class SdxlPayload(BaseModel):
        prompt: str = "A photo of an astronaut riding a horse"
        steps: int = 25
        width: int = 1024
        height: int = 1024

    app = FastAPI()

    @app.get("/")
    def health() -> dict:
        return {"status": "ok", "phase_boot_seconds": WARMUP_DONE_MONO - PROCESS_START_MONO}

    @app.post("/infer")
    def infer_endpoint(payload: SdxlPayload) -> dict:
        return inference(payload.prompt, payload.steps, payload.width, payload.height)

    port = int(os.environ.get("PORT", "8080"))
    log.info("starting uvicorn on :%d", port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    _main()
