"""Whisper large-v3 handler (faster-whisper backend).

Same phase-timestamp contract as sdxl_handler.py. Audio is provided per-fire as an
HTTPS URL (payload.audio_url) so the fire script controls the input sample.
"""

import time

PROCESS_START_MONO = time.monotonic()
PROCESS_START_EPOCH = time.time()

import logging
import os
import tempfile
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("whisper")

log.info("process_start epoch=%.6f", PROCESS_START_EPOCH)

from faster_whisper import WhisperModel

IMPORT_DONE_MONO = time.monotonic()
log.info("import_done +%.3fs", IMPORT_DONE_MONO - PROCESS_START_MONO)

MODEL_ID = "Systran/faster-whisper-large-v3"
LOCAL_MODEL_DIR = os.environ.get("WHISPER_MODEL_DIR", "/models/whisper")


def _ensure_weights() -> None:
    marker = os.path.join(LOCAL_MODEL_DIR, "config.json")
    if os.path.exists(marker):
        log.info("weights present at %s", LOCAL_MODEL_DIR)
        return
    log.info("downloading weights to %s (first-time volume seed)", LOCAL_MODEL_DIR)
    from huggingface_hub import snapshot_download

    os.makedirs(LOCAL_MODEL_DIR, exist_ok=True)
    snapshot_download(repo_id=MODEL_ID, local_dir=LOCAL_MODEL_DIR)


_ensure_weights()
WEIGHTS_READY_MONO = time.monotonic()
log.info("weights_ready +%.3fs", WEIGHTS_READY_MONO - PROCESS_START_MONO)


def _load_model() -> WhisperModel:
    log.info("loading whisper from %s", LOCAL_MODEL_DIR)
    return WhisperModel(LOCAL_MODEL_DIR, device="cuda", compute_type="float16")


MODEL = _load_model()
WEIGHTS_LOADED_MONO = time.monotonic()
log.info("weights_loaded +%.3fs", WEIGHTS_LOADED_MONO - PROCESS_START_MONO)


def _warmup() -> None:
    import numpy as np

    silent = np.zeros(16000, dtype=np.float32)
    list(MODEL.transcribe(silent, beam_size=1)[0])


_warmup()
WARMUP_DONE_MONO = time.monotonic()
log.info("warmup_done +%.3fs", WARMUP_DONE_MONO - PROCESS_START_MONO)


def _download(url: str) -> str:
    fd, path = tempfile.mkstemp(suffix=os.path.splitext(url)[1] or ".wav")
    os.close(fd)
    urllib.request.urlretrieve(url, path)
    return path


def inference(audio_url: str, language: str | None = None, beam_size: int = 5) -> dict:
    fetch_start_mono = time.monotonic()
    audio_path = _download(audio_url)
    fetch_done_mono = time.monotonic()
    segments_iter, info = MODEL.transcribe(
        audio_path,
        language=language,
        beam_size=beam_size,
    )
    segments = [{"start": s.start, "end": s.end, "text": s.text} for s in segments_iter]
    inference_done_mono = time.monotonic()
    os.remove(audio_path)
    return_mono = time.monotonic()
    return {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "segments": segments,
        "text": "".join(s["text"] for s in segments),
        "phase_seconds": {
            "python_start_to_import_done": IMPORT_DONE_MONO - PROCESS_START_MONO,
            "python_start_to_weights_loaded": WEIGHTS_LOADED_MONO - PROCESS_START_MONO,
            "python_start_to_warmup_done": WARMUP_DONE_MONO - PROCESS_START_MONO,
            "fetch_audio": fetch_done_mono - fetch_start_mono,
            "inference_only": inference_done_mono - fetch_done_mono,
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
                audio_url=payload["audio_url"],
                language=payload.get("language"),
                beam_size=int(payload.get("beam_size", 5)),
            )

        log.info("starting runpod.serverless")
        runpod.serverless.start({"handler": runpod_handler})
        return

    from fastapi import FastAPI
    from pydantic import BaseModel
    import uvicorn

    class WhisperPayload(BaseModel):
        audio_url: str
        language: str | None = None
        beam_size: int = 5

    app = FastAPI()

    @app.get("/")
    def health() -> dict:
        return {"status": "ok", "phase_boot_seconds": WARMUP_DONE_MONO - PROCESS_START_MONO}

    @app.post("/infer")
    def infer_endpoint(payload: WhisperPayload) -> dict:
        return inference(payload.audio_url, payload.language, payload.beam_size)

    port = int(os.environ.get("PORT", "8080"))
    log.info("starting uvicorn on :%d", port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    _main()
