"""盲検シートに載せる前に、両モデルの出力を同じ規則で整える。output/raw と記事に載せる出力は加工しない。

規則（両モデル共通。適用の順番どおり）:
1. 区切り線（--- だけの行）で出力を区間に分ける
2. 最初の区切り線より前が 1 段落だけで、その段落が書き直し作業そのものに触れている
   （「書き直」「言い換え」を含む）なら、前置きとして削る
3. 最後の区切り線より後ろが 1 段落だけで、「このように」で始まるなら、締めの地の文として削る
4. 見出し・太字を外した結果が「書き直した文章」などのラベルだけの行は削る
5. Markdown を外す: 区切り線は消す、見出しの # と太字の ** を外す、箇条書きの記号（- / *）は「・」にする
   （入れ子は字下げ 1 段ごとに全角空白 1 つ）、行末の改行用の空白 2 つを消す。番号付きの「1.」はそのまま残す
6. 空行が 2 つ以上続くところは 1 つにする
7. 段落の区切りを揃える。空行を除いた各行を 1 段落として扱い、段落の間を空行 1 つにする。
   ただし箇条書き（・）と番号付き（1.）の行が続くところは 1 つのまとまりとし、その中の改行はそのまま残す

本文の後ろに付いた補足・解説（「補足」の節など）は書き直しの一部として残し、Markdown だけを外す。
"""
import re

HR = re.compile(r"^\s*---\s*$")
LABEL = re.compile(r"^(書き直した文章|書き直し後の文章|書き直し後|書き直した文|言い換えた文章)[:：]?$")


def _paragraphs(lines):
    return [p for p in "\n".join(lines).split("\n\n") if p.strip()]


def normalize(text):
    """整えた本文と、削った部分のリストを返す。"""
    removed = []
    lines = text.strip().split("\n")
    hr_idx = [i for i, line in enumerate(lines) if HR.match(line)]

    if hr_idx:
        head = lines[: hr_idx[0]]
        paras = _paragraphs(head)
        if len(paras) == 1 and re.search(r"書き直|言い換え", paras[0]):
            removed.append({"rule": "前置き", "text": paras[0].strip()})
            lines = lines[hr_idx[0]:]
            hr_idx = [i for i, line in enumerate(lines) if HR.match(line)]
    if hr_idx:
        tail = lines[hr_idx[-1] + 1:]
        paras = _paragraphs(tail)
        if len(paras) == 1 and paras[0].strip().startswith("このように"):
            removed.append({"rule": "締め", "text": paras[0].strip()})
            lines = lines[: hr_idx[-1]]

    out = []
    for line in lines:
        if HR.match(line):
            continue
        s = re.sub(r"^#+\s*", "", line)
        s = s.replace("**", "")
        m = re.match(r"^(\s*)[-*]\s+(.*)$", s)
        if m:
            depth = len(m.group(1).replace("\t", "  ")) // 2
            s = "　" * depth + "・" + m.group(2)
        s = s.rstrip()
        if LABEL.match(s.strip()):
            removed.append({"rule": "見出しラベル", "text": line.strip()})
            continue
        out.append(s)
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
    return _uniform_paragraphs(body), removed


LIST_ITEM = re.compile(r"^(　*・|\d+\.\s)")


def _uniform_paragraphs(body):
    blocks = []
    for line in body.split("\n"):
        if not line.strip():
            continue
        if LIST_ITEM.match(line) and blocks and LIST_ITEM.match(blocks[-1][-1]):
            blocks[-1].append(line)
        else:
            blocks.append([line])
    return "\n\n".join("\n".join(b) for b in blocks)
