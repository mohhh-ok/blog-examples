"""問題の素材（法令・判決・青空文庫）を一次出典から取得して SRC_DIR（既定 /tmp/sarashina-blog/src）に置く。

PDF からの本文抽出に pdftotext（poppler）を使う。
"""
import html
import os
import re
import subprocess
import urllib.request
from pathlib import Path

SRC = Path(os.environ.get("SRC_DIR", "/tmp/sarashina-blog/src"))

LAWS = [("412AC0000000061", "10"), ("403AC0000000090", "6"), ("415AC0000000057", "27")]
JUDGMENTS = ["51990", "85547"]
AOZORA = ["000879/files/92_14545", "000121/files/637_13341", "000148/files/799_14972", "000081/files/473_42318"]
# 青空文庫の外字画像の説明 → Unicode の字
GAIJI = {"特のへん＋廴＋聿": "犍", "目＋爭": "睜", "楫のつくり＋戈": "戢"}


def get(url):
    with urllib.request.urlopen(url) as r:
        return r.read()


def aozora_text(raw_html):
    m = re.search(r'<div class="main_text">(.*?)<div class="bibliographical_information">', raw_html, re.S)
    s = m.group(1)

    def gaiji(mm):
        for k, v in GAIJI.items():
            if k in mm.group(0):
                return v
        raise ValueError(f"未対応の外字: {mm.group(0)}")

    s = re.sub(r"<img[^>]*>", gaiji, s)
    s = re.sub(r"<rp>.*?</rp>|<rt>.*?</rt>", "", s, flags=re.S)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", "", s))
    return re.sub(r"\n{2,}", "\n", s).strip()


def main():
    SRC.mkdir(parents=True, exist_ok=True)
    for law_id, art in LAWS:
        (SRC / f"law_{law_id}_{art}.xml").write_bytes(
            get(f"https://laws.e-gov.go.jp/api/1/articles;lawId={law_id};article={art}"))
    for jid in JUDGMENTS:
        pdf = SRC / f"p{jid}.pdf"
        pdf.write_bytes(get(f"https://www.courts.go.jp/assets/hanrei/hanrei-pdf-{jid}.pdf"))
        subprocess.run(["pdftotext", str(pdf), str(SRC / f"p{jid}.txt")], check=True)
    for path in AOZORA:
        name = path.rsplit("/", 1)[1]
        raw = get(f"https://www.aozora.gr.jp/cards/{path}.html").decode("cp932").replace("\r\n", "\n")
        (SRC / f"{name}.txt").write_text(aozora_text(raw))
    # 夢十夜は第一夜だけ使う
    s = (SRC / "799_14972.txt").read_text()
    (SRC / "799_first.txt").write_text(s[: s.index("第二夜")].strip())
    print("sources ->", SRC)


if __name__ == "__main__":
    main()
