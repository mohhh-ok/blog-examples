"""Azure Personal Voice で 7 言語生成。

事前:
- Azure Limited Access 申請に承認されていること (Custom Neural Voice -> Personal Voice)
  https://aka.ms/customneural
- Speech リソースを japaneast (など) で作成
- /speaker_profiles REST API で reference/ref.wav から speaker profile を作成 → ID 取得
- envs/azure venv で `pip install azure-cognitiveservices-speech requests python-dotenv`
- .env に AZURE_SPEECH_KEY / AZURE_SPEECH_REGION / AZURE_PERSONAL_VOICE_ID を設定

Personal Voice は SSML 経由で `<mstts:ttsembedding speakerProfileId="...">` を渡す。
モデル: PhoenixV2Neural (multilingual, 91 言語サポート)
"""

import os
import sys
import time
from pathlib import Path

import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prompts import PROMPTS  # noqa: E402

OUT = ROOT / "output" / "azure_personal"
OUT.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

KEY = os.environ["AZURE_SPEECH_KEY"]
REGION = os.environ["AZURE_SPEECH_REGION"]
PROFILE_ID = os.environ["AZURE_PERSONAL_VOICE_ID"]

# xml:lang 用の BCP-47 ロケール
AZURE_LOCALE = {
    "ja": "ja-JP", "en": "en-US", "zh": "zh-CN", "ko": "ko-KR",
    "fr": "fr-FR", "es": "es-ES", "de": "de-DE",
}

SSML_TEMPLATE = """<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='{locale}'>
  <voice name='DragonHDLatestNeural'>
    <mstts:ttsembedding speakerProfileId='{profile_id}'>
      <lang xml:lang='{locale}'>{text}</lang>
    </mstts:ttsembedding>
  </voice>
</speak>"""


def main() -> None:
    cfg = speechsdk.SpeechConfig(subscription=KEY, region=REGION)
    cfg.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm,
    )
    print(f"[init] region={REGION} profile={PROFILE_ID[:8]}...", flush=True)

    for lang, text in PROMPTS.items():
        out = OUT / f"{lang}.wav"
        audio_cfg = speechsdk.audio.AudioOutputConfig(filename=str(out))
        synth = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=audio_cfg)
        ssml = SSML_TEMPLATE.format(
            locale=AZURE_LOCALE[lang], profile_id=PROFILE_ID, text=text,
        )
        t0 = time.time()
        result = synth.speak_ssml_async(ssml).get()
        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            print(f"[{lang}] FAILED: {result.reason} / {result.cancellation_details}", flush=True)
            continue
        print(f"[{lang}] {out.name} ({time.time() - t0:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
