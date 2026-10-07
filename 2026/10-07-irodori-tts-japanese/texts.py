"""全実験で共通の文と参照音声の書き起こし。生成 (Fish / Irodori) と判定の両方から読む。"""

import json
from pathlib import Path

DATA = Path(__file__).parent / "data"

# 08-27 IndexTTS 記事と同じ文
TEXT_B = "本日は晴天なり。マイクのテスト中です。この音声は、ゼロショット音声合成のサンプルです。"

# 08-27 の c1〜c5 (読み指定なし)
TEXTS_C = {
    "c1": "了解しました。明日の朝、東雲駅で待ち合わせましょう。",
    "c2": "雰囲気のいい店で、代替案について早急に検討した。",
    "c3": "彼は人気のない道を歩いた。",
    "c4": "一日中、日本橋で過ごした。",
    "c5": "今日は八日、明後日は十日です。",
}

# 参照音声の書き起こし (Fish の references.text に送る。Irodori は書き起こしを使わない)
REF_TEXTS = {
    # 08-26 Fish 記事の ref.wav (人手確認済み)
    "r10": (
        "本日はお忙しい中お越しいただき、誠にありがとうございます。"
        "それでは、プロジェクトの進捗状況について、簡単にご説明させていただきます。"
    ),
    # 09-24 Gemini 記事の ref-source (gpt-4o-transcribe の書き起こし)
    "r26": (
        "こんにちは。音声合成の聞き比べに使う声を録音しています。"
        "朝から少し雨が降っていましたが、午後になって晴れてきました。"
        "駅前の喫茶店で温かいコーヒーを飲みながら、のんびり本を読むのが好きです。"
    ),
}


def load_rows(name: str) -> list[dict]:
    """data/r100.jsonl (JKYB-Parakeet から選んだ 100 行) / data/n10.jsonl (数字・英字の 10 行)。"""
    return [json.loads(line) for line in (DATA / f"{name}.jsonl").read_text().splitlines() if line]


def jobs() -> list[dict]:
    """生成の一覧。tag がファイル名、ref が参照音声 (r10 / r26)。"""
    out = []
    for ref in ("r10", "r26"):
        for i in range(1, 6):
            out.append({"exp": "B", "tag": f"b_{ref}_run{i}", "ref": ref, "text": TEXT_B})
    for tag, text in TEXTS_C.items():
        out.append({"exp": "C", "tag": tag, "ref": "r10", "text": text})
    for i, row in enumerate(load_rows("r100"), start=1):
        out.append({"exp": "R", "tag": f"r{i:03d}", "ref": "r10", "text": row["text"], "key": row["key"]})
    for row in load_rows("n10"):
        out.append({"exp": "N", "tag": row["key"].split("_")[0], "ref": "r10", "text": row["text"], "key": row["key"]})
    return out
