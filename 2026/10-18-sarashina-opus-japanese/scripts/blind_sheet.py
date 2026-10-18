"""書き直し 10 問の盲検シートを作る。A/B の割り当ては問題ごとにランダムで、対応表は output/blind_key.json に分けて保存する。

各応答は API の出力（common.answer_text）を一切加工せずに全文そのまま載せる。応答の中の見出しとぶつからないよう、
シート側の区切り（問題番号・元の文章・A・B）は Markdown の見出しを使わず「━━」の行で書き、応答の前後には空行だけを入れる。
シートの出力先は BLIND_SHEET（既定 /tmp/sarashina-blog/blind-sheet.md）、対応表は BLIND_KEY（既定 output/blind_key.json）。
判定が終わるまで対応表を開かない。作り直すと割り当てが変わるので、上書きするときは --force を付ける。
--keep-assignment を付けると、今の対応表の A/B の割り当てのままシートだけを作り直す。
"""
import json
import os
import random
import sys
from pathlib import Path

from common import OUTPUT, answer_text, load_problems

SHEET = Path(os.environ.get("BLIND_SHEET", "/tmp/sarashina-blog/blind-sheet.md"))
KEY = Path(os.environ.get("BLIND_KEY", OUTPUT / "blind_key.json"))
BAR = "━" * 16


def begin(label):
    return f"━━ {label} の応答（ここから。全文・無加工） ━━"


def end(label):
    return f"━━ {label} の応答（ここまで） ━━"


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
             "どちらがどのモデルかは伏せてあります。各モデルの応答は、前置き・締め・見出し・補足も含めて全文をそのまま載せ、一文字も手を加えていません。",
             "応答の中の見出しと区別するため、シート側の区切りは「━━」の行で書いています。", ""]
    for p in [p for p in load_problems() if p["category"] == "書き直し"]:
        if keep:
            models = [old[p["id"]]["A"], old[p["id"]]["B"]]
        else:
            models = ["sarashina", "opus"]
            rng.shuffle(models)
        key[p["id"]] = {"A": models[0], "B": models[1]}
        lines += [f"{BAR} {p['id']} {BAR}", "", "━━ 元の文章 ━━", "", p["input_text"], ""]
        for label, m in zip("AB", models):
            lines += [begin(label), "", answer_text(m, p["id"]), "", end(label), ""]
        lines += ["判定: ", "メモ: ", "", "***", ""]
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    SHEET.write_text("\n".join(lines))
    KEY.write_text(json.dumps(key, ensure_ascii=False, indent=2))
    print("sheet ->", SHEET, "/ key ->", KEY)


if __name__ == "__main__":
    main()
