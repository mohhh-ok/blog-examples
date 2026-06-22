# Azure Personal Voice セットアップ

Custom Neural Voice (CNV) ファミリの一部。**Limited Access 申請承認が必須**。

## 前提

1. https://aka.ms/customneural で「Personal Voice」枠の Limited Access を申請
   - 個人 / 企業の用途、consent 取得フロー、データ削除手順を書く
   - 承認まで 1〜2 週間
2. Speech リソースを承認テナント内の region に作成 (japaneast 推奨)

## 環境

```bash
cd envs
python3 -m venv azure
source azure/bin/activate
pip install azure-cognitiveservices-speech requests python-dotenv
cd ..
```

## speaker profile 作成

Personal Voice は SDK ではなく REST API で profile を作る。

```bash
# 1. consent file を作成 (本人の音声で「I agree to use my voice for ...」)
# 2. consent を upload
curl -X POST "https://${REGION}.api.cognitive.microsoft.com/customvoice/consents/<id>?api-version=2024-02-01-preview" \
  -H "Ocp-Apim-Subscription-Key: ${KEY}" \
  -F "audiodata=@consent.wav" \
  -F 'description=PersonalVoice consent' \
  -F 'projectId=<project>' \
  -F 'voiceTalentName=...' \
  -F 'companyName=...' \
  -F 'locale=ja-JP'

# 3. speaker profile を作成 (reference/ref.wav を使う)
curl -X POST "https://${REGION}.api.cognitive.microsoft.com/customvoice/personalvoices/<voice-id>?api-version=2024-02-01-preview" \
  -H "Ocp-Apim-Subscription-Key: ${KEY}" \
  -F "audiodata=@reference/ref.wav" \
  -F 'consentId=<id>' \
  -F 'projectId=<project>'

# 4. 返ってきた speakerProfileId を .env: AZURE_PERSONAL_VOICE_ID に設定
```

詳細は MS Docs: https://learn.microsoft.com/azure/ai-services/speech-service/personal-voice-overview

## 実行

```bash
source envs/azure/bin/activate
python scripts/generate_azure_personal.py
```

## 備考

- voice モデルは `DragonHDLatestNeural` (Phoenix v2, multilingual)。
- xml:lang を切り替えて多言語生成。`<lang xml:lang>` で 1 SSML 内多言語も可能。
- pricing: $0.024/1k chars (output)。consent + profile は無料。
- license: 商用可。**話者本人の明示的 consent が法的に必須** (Responsible AI 規約)。
  SaaS UI に consent flow を組む必要あり。
