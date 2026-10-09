# Capacitor iOS で Web Audio の音が鳴らない件の診断ページと修正例

記事: 【Capacitor】iOSアプリで音が鳴らない・途中から鳴らなくなる原因3つ【Web Audio】（mohhh-ok.github.io/blog・2026-10-09）

- `index.html` — アプリの `public/index.html` と差し替えて開く診断ページ。同梱の mp3 を fetch したときの status / ok と、`navigator.audioSession.type = "ambient"` の有無で AudioContext が running になり時計が進むかを console に出す
- `appAudio.ts` — アプリ全体で 1 つの AudioContext を持ち、画面が一度隠れたら次のタップで作り直す例と、同梱の音声の status 0 を受ける判定

## 診断ページの使い方（シミュレータ）

```bash
C=$(xcrun simctl get_app_container <UDID> <bundle id>)
cp index.html "$C/public/index.html"   # MODE と MP3 を書き換えてから
xcrun simctl launch --console-pty --terminate-running-process <UDID> <bundle id>
```

Capacitor の Debug ビルドなら、JS の console が `⚡️  [log] - [DIAG] ...` の形で出る。

## 実機で JS の console を取る

```bash
DEVICECTL_CHILD_NSUnbufferedIO=YES xcrun devicectl device process launch \
  --console --terminate-existing --device <UDID> <bundle id>
```

`NSUnbufferedIO=YES` が無いと出力がバッファされ、途中から届かない。Debug ビルドはプラグインの戻り値（Preferences に保存した token など）もログに出すので、ログの置き場に注意。
