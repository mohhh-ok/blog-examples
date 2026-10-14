"""共通定義: 参照音声・テキスト・モデル・出力先。

参照音声と生成テキストは 08-26 の記事 (../08-26-fish-voice-clone-consistency) から借りている。
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# 参照音声は 08-26 と同じファイル (筆者本人の声 10.16 秒・24kHz mono・git 管理外)
REF_WAV = Path(os.environ.get("REF_WAV", ROOT.parent / "08-26-fish-voice-clone-consistency" / "reference" / "ref.wav"))
OUT = ROOT / "output"
VOICE_JSON = OUT / "voice.json"

API = "https://api.elevenlabs.io"
VOICE_NAME = "blogtest-ivc-ref10s"
MODEL = "eleven_v4"

# 実験 1: 同一文 x 5 (08-26 第 1 弾 generate.py の GEN_TEXT と同一)
SAME_TEXT = (
    "本日は晴天に恵まれ、公園には多くの家族連れが訪れています。"
    "午後からは気温が上がり、木陰で休む人の姿も見られました。"
    "明日も同じような穏やかな天気が続く見込みです。"
)
SAME_N = 5

# 実験 2: 異文 x 5 (08-26 第 2 弾 generate_varied.py の GEN_TEXTS と同一)
VARIED_TEXTS = [
    (
        "駅前の商店街では、朝から新鮮な野菜や果物を求める人々で賑わっています。"
        "店主たちは威勢のよい掛け声で客を迎え、通りには活気があふれていました。"
        "夕方には特売が始まり、さらに多くの買い物客が訪れる見込みです。"
    ),
    (
        "新しい図書館は、静かな環境と豊富な蔵書で多くの利用者に親しまれています。"
        "窓際の閲覧席からは中庭の緑が眺められ、読書に最適な空間となっています。"
        "週末には子ども向けの読み聞かせ会も開かれる予定です。"
    ),
    (
        "今年の夏祭りは、三年ぶりに花火大会が開催されることになりました。"
        "会場周辺では屋台の準備が進み、地元の人々の期待も高まっています。"
        "当日は混雑が予想されるため、公共交通機関の利用が呼びかけられています。"
    ),
    (
        "山頂からの眺めは素晴らしく、遠くの海岸線まではっきりと見渡すことができました。"
        "澄んだ空気の中、登山者たちはしばらく景色に見入っていました。"
        "下山の際には、足元に十分注意するよう案内が出ています。"
    ),
    (
        "料理教室では、旬の食材を使った家庭料理の作り方を学ぶことができます。"
        "講師が丁寧に手順を説明し、参加者は和やかな雰囲気で調理を楽しんでいました。"
        "来月からは初心者向けの新しいコースも始まるそうです。"
    ),
]

# 実験 3: 7 言語 (08-26 第 5 弾 / 06-19 prompts.py と同一)
LANGS = ["ja", "en", "zh", "ko", "fr", "es", "de"]
ML_TEXTS = {
    "ja": "皆さん、こんにちは。本日は新しい機能についてご紹介します。どうぞよろしくお願いいたします。",
    "en": "Hello everyone. Today, I'd like to introduce a new feature. Thank you for joining us.",
    "zh": "大家好，今天我将为大家介绍一项新功能，感谢您的参与。",
    "ko": "여러분 안녕하세요. 오늘은 새로운 기능을 소개해 드리겠습니다. 잘 부탁드립니다.",
    "fr": "Bonjour à tous. Aujourd'hui, je vais vous présenter une nouvelle fonctionnalité. Merci de votre attention.",
    "es": "Hola a todos. Hoy les voy a presentar una nueva función. Muchas gracias por su atención.",
    "de": "Hallo zusammen. Heute stelle ich Ihnen eine neue Funktion vor. Vielen Dank für Ihre Aufmerksamkeit.",
}


def api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise SystemExit("error: ELEVENLABS_API_KEY is not set")
    return key
