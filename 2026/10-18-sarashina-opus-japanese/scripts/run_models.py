# /// script
# dependencies = ["anthropic", "requests"]
# ///
"""全問を Sarashina3 mini と Claude Opus 5.5 に逐次で投げ、生のレスポンスを output/raw/<model>/<id>.json に保存する。

- Sarashina は 6 RPM・バースト不可なので、リクエストの開始間隔を SARASHINA_INTERVAL 秒（既定 12）空ける
- 429 は Retry-After 秒待って再送し、output/request_log.jsonl に記録する
- 保存済みの問題は飛ばす（途中で止まっても再実行で続きから）
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

import anthropic
import requests

from common import MAX_TOKENS, MODELS, OPUS_EFFORT, OUTPUT, RAW, load_problems

SARASHINA_URL = "https://api.sarashina.ai/v1/chat/completions"
INTERVAL = float(os.environ.get("SARASHINA_INTERVAL", "12"))
LOG = OUTPUT / "request_log.jsonl"


def now():
    return datetime.now(timezone.utc).isoformat()


def log(entry):
    with LOG.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


class Sarashina:
    def __init__(self):
        self.key = os.environ["SARASHINA_API_KEY"]
        # 直前の実行の最後のリクエストから間隔を空けるため、1 本目も INTERVAL 待つ
        self.last_start = time.monotonic()

    def call(self, pid, prompt):
        # 既定のサンプリング（temperature 0.7, top_p 0.9, repetition_penalty 1.05）を使うため、それらは送らない
        body = {"model": MODELS["sarashina"], "messages": [{"role": "user", "content": prompt}],
                "max_completion_tokens": MAX_TOKENS}
        while True:
            wait = self.last_start + INTERVAL - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self.last_start = time.monotonic()
            started = now()
            r = requests.post(SARASHINA_URL, json=body, timeout=600,
                              headers={"Authorization": f"Bearer {self.key}"})
            entry = {"model": "sarashina", "id": pid, "started_at": started, "ended_at": now(), "status": r.status_code}
            if r.status_code == 429:
                retry_after = float(r.headers.get("Retry-After", "60"))
                log({**entry, "retry_after": retry_after})
                time.sleep(retry_after)
                continue
            log(entry)
            r.raise_for_status()
            return {"requested_at": started, "request": body, "response": r.json()}


class Opus:
    def __init__(self):
        self.client = anthropic.Anthropic()

    def call(self, pid, prompt):
        # temperature は 400（deprecated）、thinking disabled も 400 になるため送らない。effort で thinking を最小にする。
        # 比較のためフォールバック（別モデルへの切り替え）は使わない
        params = {"model": MODELS["opus"], "max_tokens": MAX_TOKENS, "output_config": {"effort": OPUS_EFFORT},
                  "messages": [{"role": "user", "content": prompt}]}
        started = now()
        raw = self.client.messages.with_raw_response.create(**params)
        log({"model": "opus", "id": pid, "started_at": started, "ended_at": now(), "status": raw.http_response.status_code})
        return {"requested_at": started, "request": params, "response": json.loads(raw.http_response.text)}


def main():
    only = set(sys.argv[1:])
    OUTPUT.mkdir(exist_ok=True)
    clients = {"sarashina": Sarashina(), "opus": Opus()}
    for p in load_problems():
        if only and p["id"] not in only:
            continue
        for key, client in clients.items():
            path = RAW / key / f"{p['id']}.json"
            if path.exists():
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            rec = client.call(p["id"], p["prompt"])
            path.write_text(json.dumps({"model_key": key, "id": p["id"], **rec}, ensure_ascii=False, indent=2))
            print(f"{p['id']} {key} saved", flush=True)


if __name__ == "__main__":
    main()
