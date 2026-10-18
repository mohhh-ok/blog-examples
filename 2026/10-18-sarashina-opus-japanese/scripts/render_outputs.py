"""全問の問題文・両モデルの出力・GPT の判定・本人の判定を、読める Markdown に書き出す。API キー不要。

- outputs.md: 目次（カテゴリごとのファイルと問題 ID へのリンク）
- outputs/<カテゴリ>.md: 各問の全文。各問の見出しの前に <a id="r01"> のようなアンカーを置く
- outputs/rewrite_h.md: 人が読む用に別に作った書き直し H01〜H10（40 問とは別）

モデルの出力は output/raw から加工せずに載せる。出力自体に Markdown の見出しや区切り線が入っているため、
ページの見出し構造を崩さないよう、各行の頭に "> " を付けて引用の中に入れる（中の Markdown はそのまま表示される）。
"""
import json

from common import JUDGE, OUTPUT, PROBLEMS_H, ROOT, answer_text, load_problems

FILES = {"書き直し": "rewrite", "敬語": "keigo", "自由作文": "writing", "要約": "summary",
         "ニュアンス": "nuance", "漢字の読み": "reading"}
NAMES = {"sarashina": "Sarashina3 mini", "opus": "Claude Opus 5.5"}
SLOT = {"1": "回答 1", "2": "回答 2", "tie": "差なし"}


def quote(text):
    return "\n".join("> " + line if line.strip() else ">" for line in text.strip().split("\n"))


def source_line(s):
    parts = [s["type"]]
    if s.get("title"):
        parts.append(s["title"])
    line = "出典: " + " / ".join(parts)
    if s.get("url"):
        line += f"（{s['url']}）"
    return line


def judge_block(p):
    out = ["#### GPT の判定（gpt-6.1-sol、左右を入れ替えて 2 回）", ""]
    for n, first in enumerate(("sarashina", "opus"), 1):
        r = json.loads((JUDGE / f"{p['id']}_{first}-first.json").read_text())
        a1, a2 = NAMES[r["answer1_model"]], NAMES[r["answer2_model"]]
        j = r["judgement"]
        out.append(f"判定 {n}（回答 1 = {a1}、回答 2 = {a2}）")
        out.append("")
        if p["category"] == "書き直し":
            for key, name in (("answer1", a1), ("answer2", a2)):
                ok = "保たれている" if j[key]["meaning_preserved"] else "変わった・情報が落ちた"
                out.append(f"- {name} の意味: {ok}。{j[key]['issues']}")
            out.append(f"- 読みやすいほう: {SLOT[j['readability_better']]}。{j['readability_reason']}")
        else:
            out.append(f"- よいほう: {SLOT[j['winner']]}。{j['reason']}")
        out.append("")
    return out


def human_block(h, key, invalid_note=None):
    out = ["#### 本人の判定（読みやすさのみ）", ""]
    if invalid_note and h["status"] != "excluded":
        out += [invalid_note, ""]
    if h["status"] == "excluded":
        out.append(h["reason"])
    else:
        picked = key.get(h["readable"])
        out.append(f"「{h['line']}」→ 読みやすいとしたのは {NAMES[picked]}" if picked
                   else f"「{h['line']}」→ Claude が「差なし」と読んだ")
        if h["status"] == "not_blind":
            out += ["", h["reason"]]
    return out + [""]


def problem_page(title, ps, final, human, key, invalid_note=None):
    page = [title, "", "[目次に戻る](../outputs.md)", ""]
    for p in ps:
        f = final[p["id"]]
        page += [f'<a id="{p["id"].lower()}"></a>', "", f"## {p['id']}", "", source_line(p["source"]), ""]
        if p["category"] == "要約":
            head, body = p["prompt"].split("\n\n---\n", 1)
            page += ["### 問題文", "", head, "", f"<details><summary>本文（{len(body)} 字）</summary>", "",
                     quote(body), "", "</details>", ""]
        else:
            page += ["### 問題文", "", quote(p["prompt"]), ""]
        for m in ("sarashina", "opus"):
            page += [f"### {NAMES[m]} の出力", "", quote(answer_text(m, p["id"])), ""]
        if p.get("answer"):
            page += ["#### 正誤（機械採点）", "", f"正解: {' / '.join(p['answer'])}", ""]
            for m in ("sarashina", "opus"):
                rd = f["reading"][m]
                page.append(f"- {NAMES[m]}: {rd['output'].strip()}（{'正解' if rd['correct'] else '不正解'}）")
            page.append("")
        page += judge_block(p)
        winner = {"sarashina": NAMES["sarashina"], "opus": NAMES["opus"], "tie": "引き分け"}[f["final"]]
        page += [f"GPT の判定の結果: {winner}", ""]
        h = human.get(p["id"])
        if h:
            page += human_block(h, key[p["id"]], invalid_note)
        page += ["---", ""]
    return page


def main():
    problems = load_problems()
    results = json.loads((OUTPUT / "results.json").read_text())
    final = {r["id"]: r for r in results["per_problem"]}
    human = json.loads((OUTPUT / "human_judgement.json").read_text())
    key = json.loads((OUTPUT / "blind_key.json").read_text())
    invalid = ("この判定は無効にした。盲検シートの整形で Opus の「補足」の節が本文と地続きになり、補足の位置づけが読み取れないまま判定したため。"
               "人が読む用に別に作った [H01〜H10](rewrite_h.md) で判定し直した。")

    (ROOT / "outputs").mkdir(exist_ok=True)
    index = ["# 全問の問題と出力", "",
             "Sarashina3 mini と Claude Opus 5.5 に出した 40 問の問題文、両モデルの出力の全文、GPT の判定を載せています。",
             "出力は API のレスポンス（`output/raw`）から加工せずに転記し、引用の中に入れています。"
             "計測は 2026-10-18。条件と判定方法は [README](README.md) にあります。", ""]
    for cat, fname in FILES.items():
        ps = [p for p in problems if p["category"] == cat]
        index.append(f"- [{cat}](outputs/{fname}.md)（{len(ps)} 問）: "
                     + " ".join(f"[{p['id']}](outputs/{fname}.md#{p['id'].lower()})" for p in ps))
        page = problem_page(f"# {cat}（{len(ps)} 問）", ps, final, human, key, invalid if cat == "書き直し" else None)
        (ROOT / "outputs" / f"{fname}.md").write_text("\n".join(page))
    if "h" in results:
        ps = load_problems(PROBLEMS_H)
        final_h = {r["id"]: r for r in results["h"]["per_problem"]}
        human_h = json.loads((OUTPUT / "human_judgement_h.json").read_text())
        key_h = json.loads((OUTPUT / "blind_key_h.json").read_text())
        index += ["", "40 問とは別に、本人が読みやすさを判定するために作った書き直しの 10 問です。",
                  "R01〜R10 とは別の素材で、指示文は同じです。", "",
                  f"- [人が読む用の書き直し](outputs/rewrite_h.md)（{len(ps)} 問）: "
                  + " ".join(f"[{p['id']}](outputs/rewrite_h.md#{p['id'].lower()})" for p in ps)]
        page = problem_page(f"# 人が読む用の書き直し（{len(ps)} 問）", ps, final_h, human_h, key_h)
        (ROOT / "outputs" / "rewrite_h.md").write_text("\n".join(page))
    (ROOT / "outputs.md").write_text("\n".join(index) + "\n")
    print("outputs.md + outputs/*.md")


if __name__ == "__main__":
    main()
