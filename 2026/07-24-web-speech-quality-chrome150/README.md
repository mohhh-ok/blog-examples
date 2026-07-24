# Web Speech API quality 検証 (Chrome 150)

Chrome 150 で `SpeechRecognitionOptions` に追加された `quality`(デフォルト `"command"`)によって、既存の音声認識コードが無言で結果を返さなくなる問題の最小再現ページ。

記事: [【Chrome】150でWeb Speech APIのonresultが返ってこない問題【quality】](https://mohhh-ok.github.io/blog/posts/2026/07-24-chrome150%E3%81%A7web-speech-api%E3%81%AEonresult%E3%81%8C%E8%BF%94%E3%81%A3%E3%81%A6%E3%81%93%E3%81%AA%E3%81%84%E5%95%8F%E9%A1%8Cquality/)

## 実行

getUserMedia を使うため、file:// ではなくローカルサーバーで開く:

```bash
npx serve .
# または
python3 -m http.server 8000
```

ブラウザ(Chrome 150+)で開き、2つのボタンを押し比べて英語で一言("hello" 等)話す。

- 「quality 未指定」: onstart〜onaudioend まで発火するのに onresult が出ない(Chrome 150 の新デフォルト "command" に落ちる環境の場合)
- 「quality: "dictation"」: interim / final とも正常に流れる
