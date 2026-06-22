# Cartesia セットアップ

```bash
cd envs
python3 -m venv cartesia
source cartesia/bin/activate
pip install cartesia python-dotenv
cd ..
```

## voice 登録

1. https://play.cartesia.ai/ で API key 発行 (.env: CARTESIA_API_KEY)
2. Voice Library → **Pro Voice Cloning** で reference/ref.wav をアップロード
   - https://www.cartesia.ai/blog/pro-voice-cloning/
   - 学習に数分〜数十分
3. 完成した voice の id を .env: CARTESIA_VOICE_ID に設定

## 実行

```bash
source envs/cartesia/bin/activate
python scripts/generate_cartesia.py
```

## 備考

- Sonic-3 は multilingual。BCP-47 ではなく ISO 2 文字 (ja/en/zh/...) で渡す。
- output_format は wav/raw/mp3 等選択可。本ベンチは wav (24kHz mono pcm_s16le)。
- license: 商用可、slot 無制限 (credits 次第)。
