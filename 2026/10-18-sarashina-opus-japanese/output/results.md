# 集計

## カテゴリ別（GPT 判定。左右入替の 2 回で勝者が一致したものだけを勝ちとする）

| カテゴリ | 問題数 | Sarashina3 mini 勝ち | Claude Opus 5.5 勝ち | 引き分け |
|---|---|---|---|---|
| 書き直し | 10 | 1 | 7 | 2 |
| 敬語 | 4 | 0 | 4 | 0 |
| 自由作文 | 4 | 0 | 4 | 0 |
| 要約 | 4 | 0 | 4 | 0 |
| ニュアンス | 4 | 0 | 4 | 0 |
| 漢字の読み | 14 | 1 | 3 | 10 |
| 合計 | 40 | 2 | 26 | 12 |

## 漢字の読み（機械採点、14 問）

- Sarashina3 mini: 11 / 14
- Claude Opus 5.5: 13 / 14

| id | 正解 | Sarashina3 mini | Claude Opus 5.5 |
|---|---|---|---|
| Y01 | そうさい | そうさい ○ | そうさい ○ |
| Y02 | ぜいじゃく | ぜいじゃく ○ | ぜいじゃく ○ |
| Y03 | とんざ | とんざ ○ | とんざ ○ |
| Y04 | ようやく / ようよう | ようやく ○ | ようやく ○ |
| Y05 | あながち | あながち ○ | あながち ○ |
| Y06 | とつとつ | とつとつ ○ | とつとつ ○ |
| Y07 | のどか | のどか ○ | のどか ○ |
| Y08 | ないがしろ | ないがしろ ○ | なおざり × |
| Y09 | ひとけ | ひとけ ○ | ひとけ ○ |
| Y10 | ついたち | ついたち ○ | ついたち ○ |
| Y11 | なまもの | せいぶつ × | なまもの ○ |
| Y12 | いちば | しじょう × | いちば ○ |
| Y13 | おおごと | だいじ × | おおごと ○ |
| Y14 | うわて | うわて ○ | うわて ○ |

## 書き直しで「意味が変わった」と 2 回とも判定された数

- Sarashina3 mini: 8 / 10
- Claude Opus 5.5: 2 / 10

## 問題ごと

| id | カテゴリ | 判定1（Sarashina が回答1） | 判定2（Opus が回答1） | 結果 | Opus thinking tokens |
|---|---|---|---|---|---|
| R01 | 書き直し | opus | opus | opus | 190 |
| R02 | 書き直し | opus | opus | opus | 161 |
| R03 | 書き直し | opus | opus | opus | 128 |
| R04 | 書き直し | tie | opus | tie | 270 |
| R05 | 書き直し | opus | opus | opus | 325 |
| R06 | 書き直し | tie | tie | tie | 224 |
| R07 | 書き直し | opus | opus | opus | 75 |
| R08 | 書き直し | opus | opus | opus | 15 |
| R09 | 書き直し | opus | opus | opus | 251 |
| R10 | 書き直し | sarashina | sarashina | sarashina | 30 |
| K01 | 敬語 | opus | opus | opus | 41 |
| K02 | 敬語 | opus | opus | opus | 427 |
| K03 | 敬語 | opus | opus | opus | 65 |
| K04 | 敬語 | opus | opus | opus | 79 |
| N01 | 自由作文 | opus | opus | opus | 26 |
| N02 | 自由作文 | opus | opus | opus | 67 |
| N03 | 自由作文 | opus | opus | opus | 271 |
| N04 | 自由作文 | opus | opus | opus | 108 |
| S01 | 要約 | opus | opus | opus | 378 |
| S02 | 要約 | opus | opus | opus | 287 |
| S03 | 要約 | opus | opus | opus | 0 |
| S04 | 要約 | opus | opus | opus | 264 |
| U01 | ニュアンス | opus | opus | opus | 26 |
| U02 | ニュアンス | opus | opus | opus | 28 |
| U03 | ニュアンス | opus | opus | opus | 31 |
| U04 | ニュアンス | opus | opus | opus | 26 |
| Y01 | 漢字の読み | tie | tie | tie | 35 |
| Y02 | 漢字の読み | tie | tie | tie | 0 |
| Y03 | 漢字の読み | tie | tie | tie | 0 |
| Y04 | 漢字の読み | tie | tie | tie | 0 |
| Y05 | 漢字の読み | tie | tie | tie | 0 |
| Y06 | 漢字の読み | tie | tie | tie | 0 |
| Y07 | 漢字の読み | tie | tie | tie | 0 |
| Y08 | 漢字の読み | sarashina | sarashina | sarashina | 0 |
| Y09 | 漢字の読み | tie | tie | tie | 36 |
| Y10 | 漢字の読み | tie | tie | tie | 0 |
| Y11 | 漢字の読み | opus | opus | opus | 17 |
| Y12 | 漢字の読み | opus | opus | opus | 45 |
| Y13 | 漢字の読み | opus | opus | opus | 56 |
| Y14 | 漢字の読み | tie | tie | tie | 0 |

## リクエスト

- Sarashina へのリクエスト数: 40（429: 0 回）
- Sarashina の任意の 60 秒間の最大リクエスト数: 5
- Opus の thinking tokens 合計: 3982

## 本人の判定（書き直し、読みやすさのみ）

本人は意味の正しさは判定できないと明言したため、本人の判定は読みやすさだけ。意味は GPT の判定を使う。
R06〜R08 は判定なし（対象外）。R01 は盲検でないため参考として別に載せる。

盲検 6 問（R02・R03・R04・R05・R09・R10）で本人が読みやすいとしたモデル:

- Sarashina3 mini: 2
- Claude Opus 5.5: 4

GPT の読みやすさの判定（各問 2 回、計 12 回）が本人と一致した回数: 9。2 回とも一致した問題: 4 / 6

| id | 盲検 | 本人の判定（逐語） | 本人が読みやすいとしたモデル | GPT 読みやすさ 判定1 / 判定2 | 本人と一致 | GPT 意味保持 Sarashina | GPT 意味保持 Opus | GPT の最終結果 |
|---|---|---|---|---|---|---|---|---|
| R02 | ○ | bがよみやすい。ただし意味の判定はできない | Claude Opus 5.5 | Claude Opus 5.5 / Claude Opus 5.5 | ○ / ○ | × / × | ○ / ○ | Claude Opus 5.5 |
| R03 | ○ | aがよみやすい。これいぜんもこれいこうも、意味の正しさの判定はできない | Sarashina3 mini | Claude Opus 5.5 / Claude Opus 5.5 | × / × | × / × | ○ / ○ | Claude Opus 5.5 |
| R04 | ○ | bがよみやすい | Claude Opus 5.5 | Claude Opus 5.5 / Claude Opus 5.5 | ○ / ○ | × / × | × / ○ | 差なし |
| R05 | ○ | bがよみやすい | Sarashina3 mini | Claude Opus 5.5 / Sarashina3 mini | × / ○ | × / × | ○ / ○ | Claude Opus 5.5 |
| R09 | ○ | どっちもよみにくいなぁ。整理されてるのはBかな | Claude Opus 5.5 | Claude Opus 5.5 / Claude Opus 5.5 | ○ / ○ | ○ / × | ○ / ○ | Claude Opus 5.5 |
| R10 | ○ | Aがいいなぁ。わかりやすい | Claude Opus 5.5 | Claude Opus 5.5 / Claude Opus 5.5 | ○ / ○ | ○ / ○ | × / × | Sarashina3 mini |
| R01 | ×（参考） | aがよみやすい。ただしいみのただしさはしょうじきわからない（元の文章が複雑すぎて判定する気になれない） | Sarashina3 mini | Claude Opus 5.5 / Claude Opus 5.5 | × / × | × / × | ○ / ○ | Claude Opus 5.5 |

判定1 は Sarashina を回答 1、判定2 は Opus を回答 1 に置いた判定。GPT の最終結果は、意味の判定を優先して決めた勝敗（引き分けは「差なし」）。
