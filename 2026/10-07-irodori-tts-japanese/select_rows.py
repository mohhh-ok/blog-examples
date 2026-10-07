"""JKYB-Parakeet から読み精度の評価に使う 100 行を固定 seed で選ぶ。

入力: JKYB-Parakeet の data/common_kanji_source.jsonl (MIT, Parakeet Inc.)
出力: data/r100.jsonl (選んだ行をそのまま)

usage: python select_rows.py /path/to/common_kanji_source.jsonl
env: SEED (既定 20261007), N (既定 100)
"""

import json
import os
import random
import sys
from pathlib import Path

SEED = int(os.environ.get("SEED", "20261007"))
N = int(os.environ.get("N", "100"))


def main() -> None:
    rows = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines() if line]
    picked = random.Random(SEED).sample(rows, N)
    out = Path(__file__).parent / "data" / "r100.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in picked))
    print(f"{len(rows)} rows -> {len(picked)} picked (seed={SEED}) -> {out}")


if __name__ == "__main__":
    main()
