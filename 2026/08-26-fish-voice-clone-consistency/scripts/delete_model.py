"""作成した voice model を削除する (DELETE /model/{id})。

削除の成否レスポンスを output/voiceid_ab/model_delete.json に記録する。

usage: python delete_model.py <model_id>
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common_voiceid_ab import RESULTS_DIR, get_api_key

from fish_audio_sdk import Session
from fish_audio_sdk.exceptions import HttpCodeErr


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: delete_model.py <model_id>", file=sys.stderr)
        sys.exit(2)
    model_id = sys.argv[1]
    api_key = get_api_key()
    session = Session(api_key)

    result: dict = {"model_id": model_id}
    try:
        session.delete_model(model_id)
        result["deleted"] = True
        print(f"[deleted] {model_id}", flush=True)
    except Exception as e:  # noqa: BLE001
        result["deleted"] = False
        result["error"] = f"{type(e).__name__}: {e}"
        print(f"[delete] FAILED: {result['error']}", file=sys.stderr, flush=True)

    # 削除確認: GET が 404 になることを確かめる
    try:
        session.get_model(model_id)
        result["get_after_delete"] = "still exists"
    except HttpCodeErr as e:
        result["get_after_delete"] = f"HttpCodeErr: {e}"
    except Exception as e:  # noqa: BLE001
        result["get_after_delete"] = f"{type(e).__name__}: {e}"

    (RESULTS_DIR / "model_delete.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["deleted"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
