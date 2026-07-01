"""共通: 参照テキスト + 7言語の生成テキスト。

固有プロダクト名・社名は含めない（Whisper の固有名詞ミスとモデルの破綻を切り分けるため）。
"""

REF_TEXT = (
    "本日はお忙しい中お越しいただき、誠にありがとうございます。"
    "それでは、プロジェクトの進捗状況について、簡単にご説明させていただきます。"
)

PROMPTS = {
    "ja": "皆さん、こんにちは。本日は新しい機能についてご紹介します。どうぞよろしくお願いいたします。",
    "en": "Hello everyone. Today, I'd like to introduce a new feature. Thank you for joining us.",
    "zh": "大家好，今天我将为大家介绍一项新功能，感谢您的参与。",
    "ko": "여러분 안녕하세요. 오늘은 새로운 기능을 소개해 드리겠습니다. 잘 부탁드립니다.",
    "fr": "Bonjour à tous. Aujourd'hui, je vais vous présenter une nouvelle fonctionnalité. Merci de votre attention.",
    "es": "Hola a todos. Hoy les voy a presentar una nueva función. Muchas gracias por su atención.",
    "de": "Hallo zusammen. Heute stelle ich Ihnen eine neue Funktion vor. Vielen Dank für Ihre Aufmerksamkeit.",
}
