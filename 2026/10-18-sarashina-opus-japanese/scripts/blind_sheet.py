"""書き直し 10 問の盲検シートを作る。A/B の割り当ては問題ごとにランダムで、対応表は output/blind_key.json に分けて保存する。

書き方の癖でモデルが分からないよう、シートに載せる出力だけを blind_format.normalize の規則で両モデル同じに整える。
削った部分は対応表に記録する。シートの出力先は BLIND_SHEET（既定 /tmp/sarashina-blog/blind-sheet.md）。
判定が終わるまで対応表を開かない。作り直すと割り当てが変わるので、上書きするときは --force を付ける。
--keep-assignment を付けると、今の対応表の A/B の割り当てのまま整形だけをやり直す。
"""
import json
import os
import random
import sys
from pathlib import Path

from blind_format import normalize
from common import OUTPUT, answer_text, load_problems

SHEET = Path(os.environ.get("BLIND_SHEET", "/tmp/sarashina-blog/blind-sheet.md"))
KEY = OUTPUT / "blind_key.json"


def main():
    keep = "--keep-assignment" in sys.argv
    if KEY.exists() and not keep and "--force" not in sys.argv:
        raise SystemExit(f"{KEY} があります。割り当てを作り直すなら --force、今の割り当てのままなら --keep-assignment を付けてください")
    old = json.loads(KEY.read_text()) if keep else {}
    rng = random.SystemRandom()
    key = {}
    lines = ["# 書き直し 10 問の盲検シート", "",
             "1. 各問で、A と B が「元の文章」の意味を変えずに書き直せているか、読みやすいかを見てください。",
             "2. 意味が変わっている・情報が落ちているものは、読みやすくても勝ちにしないでください。",
             "3. 各問の下の「判定:」の行に A / B / 引き分け のどれかを書いてください（理由はメモの行に任意で）。", "",
             "どちらがどのモデルかは伏せてあります。前置きや締めのあいさつ、見出しの記号などは、両方とも同じ規則で外してあります。", ""]
    for p in [p for p in load_problems() if p["category"] == "書き直し"]:
        if keep:
            models = [old[p["id"]]["A"], old[p["id"]]["B"]]
        else:
            models = ["sarashina", "opus"]
            rng.shuffle(models)
        texts, removed = {}, {}
        for m in models:
            texts[m], removed[m] = normalize(answer_text(m, p["id"]))
        key[p["id"]] = {"A": models[0], "B": models[1], "removed": removed}
        lines += [f"## {p['id']}", "", "### 元の文章", "", p["input_text"], "",
                  "### A", "", texts[models[0]], "",
                  "### B", "", texts[models[1]], "",
                  "判定: ", "メモ: ", "", "---", ""]
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    SHEET.write_text("\n".join(lines))
    KEY.write_text(json.dumps(key, ensure_ascii=False, indent=2))
    print("sheet ->", SHEET, "/ key ->", KEY)


if __name__ == "__main__":
    main()
