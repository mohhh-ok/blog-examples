"""書き直しの追加 10 問（H01〜H10）を data/problems_h.jsonl に組み立てる。

R01〜R10 の判定を本人がやり直すための問題。R01〜R10 と同じ素材（条文・判決の箇所・自作文）は使わない。
内訳は R01〜R10 と同じで、法令 3・最高裁判決 2・自作の悪文 5。指示文も同じ REWRITE_PROMPT を使う。
法令と判決の本文は一次出典から SRC_DIR（既定 /tmp/sarashina-blog/src）に取得して読む。PDF の本文抽出に pdftotext（poppler）を使う。
"""
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path


SRC = Path(os.environ.get("SRC_DIR", "/tmp/sarashina-blog/src"))
OUT = Path(__file__).resolve().parent.parent / "data" / "problems_h.jsonl"

# build_problems.py と同じ。build_problems.py は import すると problems.jsonl を書き出すため写している
SELF = {"type": "自作", "basis": "この実験のために新規に書いた文（Claude Opus 5.5 が作成）。実在の人物・団体・第三者の文章を含まない"}
REWRITE_PROMPT = "次の文章を、意味を変えずに、専門知識のない人が一度読んで分かる文章に書き直してください。\n\n---\n{text}"

# (ID, lawId, 条, 第1項だけか, 題名)
LAWS = [
    ("H01", "129AC0000000089", "95", False, "民法 第95条"),
    ("H02", "322AC0000000049", "20", False, "労働基準法 第20条"),
    ("H03", "351AC0000000057", "9", True, "特定商取引に関する法律 第9条第1項"),
]
# (ID, 判例 ID, 書き出し, 文の数, 題名)
JUDGMENTS = [
    ("H04", "36415", "日本国籍は，我が国の構成員", 3,
     "最高裁判所大法廷 平成20年6月4日判決 平成18(行ツ)135 退去強制令書発付処分取消等請求（国籍法3条1項）（民集62巻6号1367頁）理由の一部"),
    ("H05", "52338", "国民の選挙権又はその行使を制限することは原則として", 2,
     "最高裁判所大法廷 平成17年9月14日判決 平成13(行ツ)82 在外日本人選挙権剥奪違法確認等請求（民集59巻7号2087頁）理由の一部"),
]
BAD = {
    "H06": ("講座の受講料の返金（二重否定・条件の入れ子）",
            "本講座の受講料につきましては、開講日の七日前までに書面にてお申し出いただいた場合に限り、事務手数料として千円を差し引いた額を返金しないわけではございませんが、開講日の前日以降のお申し出につきましては、主催者側の都合による中止の場合を除き、いかなる理由であっても返金には応じかねますので、あらかじめご了承ください。"),
    "H07": ("市の送迎事業のお知らせ（修飾が長い）",
              "昨年度に当市が実施した市内在住の六十五歳以上の単身世帯を対象とする生活実態調査の結果を踏まえて新たに設けられた、買い物や通院などの日常的な外出に支障がある高齢者の自宅まで地域のボランティアが車で送迎を行う事業の利用登録の受付を、来月一日から市役所福祉課の窓口と各地区の公民館で開始します。"),
    "H08": ("病院の予約変更の案内（条件と例外の入れ子）",
            "予約日の前日の午後五時までにお電話でご連絡いただいた場合は、予約の変更を承りますが、初診の方につきましては、紹介状をお持ちでない場合を除き、変更後の予約日が当初の予約日から一か月を超えるときは、紹介状の有効期限の関係で、改めて紹介元の医療機関で紹介状を発行していただく必要がある場合がございますので、ご注意ください。"),
    "H09": ("図書館の貸出規則（受け身・名詞化・部分否定）",
            "貸出期間の延長は、返却期限日以前であり、かつ当該資料に対する他の利用者による予約がなされていない場合においてのみ、一回に限り認められることとされています。延滞中の資料が一点でも存在する利用者に対しては、すべての資料の新規の貸出および延長の手続きが、当該資料の返却が確認されるまでの間、行われないものとします。なお、すべての資料の延長が可能とされているわけではなく、雑誌の最新号および参考図書は延長の対象とはされていません。"),
    "H10": ("社内のメール切り替えの連絡（話し言葉・部分否定）",
            "来週の金曜日の夜からメールのシステムが新しいものに切り替わるんですが、切り替え後に初めてログインするときはパスワードの変更を求められるので、その際は前のパスワードと同じものは使えないのと、八文字以上で英字と数字を両方含めないと登録できないので注意してください。あと、切り替え前に送受信したメールはすべて自動で移されるわけではなくて、受信トレイにあるものだけが移されて、自分で作ったフォルダに入れているものは移されないので、必要なものは木曜日中に受信トレイに戻しておいてもらえると助かります。"),
}


def get(url):
    with urllib.request.urlopen(url) as r:
        return r.read()


def fetch():
    SRC.mkdir(parents=True, exist_ok=True)
    for _, law_id, art, _, _ in LAWS:
        (SRC / f"law_{law_id}_{art}.xml").write_bytes(
            get(f"https://laws.e-gov.go.jp/api/1/articles;lawId={law_id};article={art}"))
    for _, jid, _, _, _ in JUDGMENTS:
        pdf = SRC / f"p{jid}.pdf"
        pdf.write_bytes(get(f"https://www.courts.go.jp/assets/hanrei/hanrei-pdf-{jid}.pdf"))
        subprocess.run(["pdftotext", str(pdf), str(SRC / f"p{jid}.txt")], check=True)


def law_text(law_id, art, first_paragraph_only):
    """条文を項・号ごとに 1 行にする。第 2 項以降は Paragraph の Num 属性から全角の項番号を行頭に付ける
    （労働基準法など古い法令は本文に項番号が無いため）。"""
    t = (SRC / f"law_{law_id}_{art}.xml").read_text()
    paragraphs = re.findall(r'<Paragraph Num="(\d+)"[^>]*>(.*?)</Paragraph>', t, re.S)
    if first_paragraph_only:
        paragraphs = paragraphs[:1]
    lines = []
    for num, body in paragraphs:
        head = "" if num == "1" else str(num).translate(str.maketrans("0123456789", "０１２３４５６７８９")) + "　"
        sentence_part = body.split("<Item ")[0]
        lines.append(head + "".join(re.findall(r"<Sentence[^>]*>(.*?)</Sentence>", sentence_part)))
        for title, item in re.findall(r"<ItemTitle>(.*?)</ItemTitle>(.*?)</Item>", body, re.S):
            lines.append(title + "　" + "".join(re.findall(r"<Sentence[^>]*>(.*?)</Sentence>", item)))
    return "\n".join(lines)


def judgment_text(jid, start, n_sentences):
    # 改行と改ページ（\f）、ページ番号「- 1 -」を除いて 1 行にする
    t = re.sub(r"- \d+ -", "", (SRC / f"p{jid}.txt").read_text().replace("\n", "").replace("\f", ""))
    i = t.index(start)
    j = i
    for _ in range(n_sentences):
        j = t.index("。", j) + 1
    return t[i:j]


def main():
    fetch()
    problems = []

    def add(pid, text, source):
        problems.append({"id": pid, "category": "書き直し", "prompt": REWRITE_PROMPT.format(text=text),
                         "input_text": text, "source": source, "answer": None})

    for pid, law_id, art, p1, title in LAWS:
        add(pid, law_text(law_id, art, p1), {
            "type": "法令", "title": title, "url": f"https://laws.e-gov.go.jp/law/{law_id}",
            "basis": "法令は著作権法13条1号により著作権の目的とならない。本文は e-Gov 法令API v1 の articles エンドポイントから取得（2026-10-18）"})
    for pid, jid, start, n, title in JUDGMENTS:
        add(pid, judgment_text(jid, start, n), {
            "type": "判決", "title": title, "url": f"https://www.courts.go.jp/hanrei/{jid}/detail2/index.html",
            "pdf": f"https://www.courts.go.jp/assets/hanrei/hanrei-pdf-{jid}.pdf",
            "basis": "判決は著作権法13条3号により著作権の目的とならない。人名を含まない段落を選んだ"})
    for pid, (kind, text) in BAD.items():
        add(pid, text, {**SELF, "title": kind})

    OUT.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in problems))
    print(f"{len(problems)} problems ->", OUT)


if __name__ == "__main__":
    main()
