"""voice model を作成する (POST /model)。

- type="tts", train_mode="fast", title="voiceid-ab-test"
- visibility="private" を必ず明示 (default 公開事故防止)
- voices=[ref.wav], texts=[REF_TEXT]
- 結果 (model id + レスポンス要点) を output/voiceid_ab/model.json に保存

usage: python create_model.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common_voiceid_ab import REF_TEXT, REF_WAV, RESULTS_DIR, get_api_key

from fish_audio_sdk import Session


def main() -> None:
    api_key = get_api_key()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    session = Session(api_key)
    ref_audio = REF_WAV.read_bytes()
    print(f"[init] ref={REF_WAV} ({len(ref_audio)} bytes)", flush=True)

    try:
        entity = session.create_model(
            visibility="private",  # 明示。default 任せにしない
            type="tts",
            title="voiceid-ab-test",
            train_mode="fast",
            voices=[ref_audio],
            texts=[REF_TEXT],
        )
    except Exception as e:  # noqa: BLE001
        # 失敗レスポンスを生で記録 (有料プラン必須等の判定材料)
        err = {"error": f"{type(e).__name__}: {e}"}
        body = getattr(getattr(e, "response", None), "text", None)
        if body:
            err["response_body"] = body
        (RESULTS_DIR / "model.json").write_text(
            json.dumps(err, ensure_ascii=False, indent=2)
        )
        print(f"[create_model] FAILED: {err}", file=sys.stderr, flush=True)
        sys.exit(1)

    dump = entity.model_dump(mode="json")
    (RESULTS_DIR / "model.json").write_text(
        json.dumps(dump, ensure_ascii=False, indent=2)
    )
    print(f"[created] model id={dump.get('id') or dump.get('_id')}", flush=True)
    print(json.dumps(dump, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
