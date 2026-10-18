"""盲検シートの「判定:」の行を逐語で取り込み、output/human_judgement.json に保存する。

本人の判定は読みやすさだけ（意味の正しさは判定できないと本人が明言したため、意味は GPT の判定を使う）。
各行から読み取った「読みやすいとした回答（A / B）」は Claude が判定の文面から読み取ったもので、READABLE に書いてある。
"""
import json
import os
import re
from pathlib import Path

from common import OUTPUT

SHEET = Path(os.environ.get("BLIND_SHEET", "/tmp/sarashina-blog/blind-sheet.md"))

# 判定の文面から Claude が読み取った「読みやすいとした回答」
READABLE = {"R01": "A", "R02": "B", "R03": "A", "R04": "B", "R05": "B",
            "R09": "B",  # 「どっちもよみにくいなぁ。整理されてるのはBかな」
            "R10": "A"}
# 盲検の集計から外す問題とその理由
NOT_BLIND = {"R01": "判定の前に、AI からの途中報告で Sarashina の書き直しの特徴（2 つの条件を別々の禁止として書いた）を本人が聞いていたため盲検ではない。参考として別に載せる"}
EXCLUDED = {pid: "判定なし（対象外にした）" for pid in ("R06", "R07", "R08")}


def main():
    text = SHEET.read_text()
    lines = dict(re.findall(r"^## (R\d+)\n.*?^判定: ?([^\n]*)$", text, re.M | re.S))
    out = {}
    for pid, line in lines.items():
        rec = {"line": line}
        if pid in EXCLUDED:
            rec["status"] = "excluded"
            rec["reason"] = EXCLUDED[pid]
        else:
            rec["readable"] = READABLE[pid]
            rec["readable_read_by"] = "Claude（判定の文面から読み取り）"
            rec["status"] = "not_blind" if pid in NOT_BLIND else "blind"
            if pid in NOT_BLIND:
                rec["reason"] = NOT_BLIND[pid]
        out[pid] = rec
    (OUTPUT / "human_judgement.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
