# Fish Audio セットアップ

```bash
cd envs
python3 -m venv fish
source fish/bin/activate
pip install fish-audio-sdk python-dotenv
cd ..
```

## voice 登録

1. https://fish.audio/go-api/ で API key 発行 (.env: FISH_API_KEY)
2. https://fish.audio/voice-cloning/ で reference/ref.wav をアップロード
   - 15 秒〜の sample 推奨。10 秒で動くこともある。
   - 登録料 $0.1/voice (one-time)
   - consent 録音が必要 (本人 voice であることの宣言)
3. 払い出された model_id を .env: FISH_MODEL_ID に設定

## 実行

```bash
source envs/fish/bin/activate
python scripts/generate_fish.py
```

## 備考

- backend は s2-pro / s1 / s1-mini。s2-pro が品質最新。
- 言語は自動判定 (text の文字種から推測)。明示指定なし。
- pricing: $0.015/1k bytes (~$15/1M)。最安帯。
- license: 商用可。Fish Speech open weights (CC-BY-NC-SA) とは別 API。
