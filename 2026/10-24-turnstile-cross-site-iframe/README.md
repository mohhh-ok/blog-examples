# 他サイトに置いた自前ドメインの iframe の中で Cloudflare Turnstile を動かす

設置先のページ X に、自前ドメイン Y の iframe を置き、その中で Turnstile を描画したときに token が取れるか、Siteverify の `hostname` がどちらになるかを確かめた。対照として、X のページに同じ sitekey で直接描画したときのエラーも見た。

記事: [【Cloudflare】他社サイトに置いたiframeの中でTurnstileが動くか試した](https://mohhh-ok.github.io/blog/posts/2026/10-24-cloudflare他社サイトに置いたiframeの中でturnstileが動くか試した/)

## 中身

- `src/pages.ts`: 3 つのページ (Y に直接・X の中の Y の iframe・X に直接)。widget の結果を Y の `/report` に送る
- `src/servers.ts`: Y (https) と X (http) のサーバー。届いた token ごとに Siteverify を投げ、jsonl に 1 行ずつ書く。token と secret は書かない
- `src/manual.ts`: 手で押す版。普段使いのブラウザで 3 ページを開いて押す
- `src/auto.ts`: Playwright 版。手元では token が取れなかった (600010)
- `results/`: 2026-10-24 に流した結果。Y のホスト名は `widget.example.com` に置き換えてある

## 必要なもの

- Node.js 24 以上 (`.ts` をそのまま動かす)
- Turnstile の widget 1 つ (sitekey と secret)。ホスト名には Y だけを登録し、X は登録しない。テスト用の sitekey (`1x000...`) はホスト名を見ないので使えない
- Y のホスト名を 127.0.0.1 に向ける設定 (`/etc/hosts`) と、ブラウザが信頼する証明書 ([mkcert](https://github.com/FiloSottile/mkcert) など)
- X には `lvh.me` を使う。公開 DNS で 127.0.0.1 を返すドメインで、Y と別のサイト (eTLD+1 が違う) になる

## 使い方

```sh
# 手で押す版。Chrome と Safari で、表示される 3 つの URL を順に開く
TURNSTILE_SITE_KEY=... TURNSTILE_SECRET_KEY=... node src/manual.ts \
  --widget-host widget.example.com --cert <証明書.pem> --key <鍵.pem> \
  --out /tmp/turnstile-iframe/manual.jsonl --browsers chrome,safari --max-minutes 10

# Playwright 版 (npm install が要る)
TURNSTILE_SITE_KEY=... TURNSTILE_SECRET_KEY=... node src/auto.ts \
  --widget-host widget.example.com --cert <証明書.pem> --key <鍵.pem> \
  --out /tmp/turnstile-iframe/auto.jsonl --browser chromium --channel chrome --headed 1
```

開く順:

1. `https://<widget-host>:4719/direct.html`: Y に直接。Y が登録済みで token が取れることを確かめる
2. `http://lvh.me:4718/embed.html`: X の中の Y の iframe
3. `http://lvh.me:4718/direct.html`: X に直接 (対照)。押さずにエラー番号を見る

ポートは `--widget-port` (既定 4719)・`--embed-port` (既定 4718) で変えられる。

## 計測のときとの違い

計測に使ったスクリプトから、次の 2 点を変えている。

- 結果の行に `referrer` と `ancestorOrigins` を足した。計測の回は記録しておらず、iframe の行の親ページをログだけでは示せなかった
- 止まる条件に X に直接 (3 番) の結果を足した。計測の回は Y に直接と iframe の 2 ページが揃った時点で止まったため、Safari の 3 番を取れなかった
