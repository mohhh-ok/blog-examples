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

## 本人の判定 R01〜R10（無効）

この判定は無効にした。盲検シートの整形（Markdown の見出しと太字を外した）で、Opus の「補足」の節が本文と地続きになり、本文が補足とセットで書かれていることが読み取れないまま判定したため。判定し直した結果は「本人の判定 H01〜H10」の節。
本人の判定は読みやすさだけ。R06〜R08 は判定なし（対象外）。R01 は盲検でないため参考として別に載せる。

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

## 人が読む用の書き直し H01〜H10（GPT 判定）

R01〜R10 とは別の法令 3・最高裁判決 2・自作の悪文 5。指示文は R01〜R10 と同じ。40 問の集計には入れていない。

| id | 素材 | GPT 意味保持 Sarashina | GPT 意味保持 Opus | 判定1 | 判定2 | 結果 |
|---|---|---|---|---|---|---|
| H01 | 法令 / 民法 第95条 | × / × | ○ / ○ | opus | opus | opus |
| H02 | 法令 / 労働基準法 第20条 | × / × | ○ / × | opus | tie | tie |
| H03 | 法令 / 特定商取引に関する法律 第9条第1項 | × / × | ○ / ○ | opus | opus | opus |
| H04 | 判決 / 最高裁判所大法廷 平成20年6月4日判決 平成18(行ツ)135 退去強制令書発付処分取消等請求（国籍法3条1項）（民集62巻6号1367頁）理由の一部 | × / × | ○ / ○ | opus | opus | opus |
| H05 | 判決 / 最高裁判所大法廷 平成17年9月14日判決 平成13(行ツ)82 在外日本人選挙権剥奪違法確認等請求（民集59巻7号2087頁）理由の一部 | × / × | ○ / ○ | opus | opus | opus |
| H06 | 自作 / 講座の受講料の返金（二重否定・条件の入れ子） | × / × | × / × | tie | tie | tie |
| H07 | 自作 / 市の送迎事業のお知らせ（修飾が長い） | × / × | ○ / ○ | opus | opus | opus |
| H08 | 自作 / 病院の予約変更の案内（条件と例外の入れ子） | × / × | ○ / ○ | opus | opus | opus |
| H09 | 自作 / 図書館の貸出規則（受け身・名詞化・部分否定） | × / × | × / × | tie | tie | tie |
| H10 | 自作 / 社内のメール切り替えの連絡（話し言葉・部分否定） | ○ / ○ | ○ / ○ | opus | opus | opus |

- 結果: Sarashina3 mini 0、Claude Opus 5.5 7、引き分け 3
- 2 回とも「意味が保たれている」: Sarashina3 mini 1 / 10、Claude Opus 5.5 7 / 10

## 本人の判定 H01〜H10（読みやすさのみ）

本人の判定は読みやすさだけで、意味の正しさは判定していない。意味は GPT の判定だけ。
判定する問題は本人が選んだ（H06・H08・H10 は判定なし）。H07 の判定は Claude が「差なし」と読んだ。

盲検 7 問（H01・H02・H03・H04・H05・H07・H09）で本人が読みやすいとしたモデル:

- Sarashina3 mini: 5
- Claude Opus 5.5: 1
- 差なし: 1

GPT の読みやすさの判定（各問 2 回、計 14 回）が本人と一致した回数: 3。2 回とも一致した問題: 1 / 7

| id | 盲検 | 本人の判定（逐語） | 本人が読みやすいとしたモデル | GPT 読みやすさ 判定1 / 判定2 | 本人と一致 | GPT 意味保持 Sarashina | GPT 意味保持 Opus | GPT の最終結果 |
|---|---|---|---|---|---|---|---|---|
| H01 | ○ | Aがよみやすい | Sarashina3 mini | Claude Opus 5.5 / Claude Opus 5.5 | × / × | × / × | ○ / ○ | Claude Opus 5.5 |
| H02 | ○ | Aがすんなりよめる | Sarashina3 mini | Claude Opus 5.5 / Claude Opus 5.5 | × / × | × / × | ○ / × | 差なし |
| H03 | ○ | A | Sarashina3 mini | Claude Opus 5.5 / Claude Opus 5.5 | × / × | × / × | ○ / ○ | Claude Opus 5.5 |
| H04 | ○ | Bが読者に寄り添っていて読みやすいと思った | Sarashina3 mini | Claude Opus 5.5 / Claude Opus 5.5 | × / × | × / × | ○ / ○ | Claude Opus 5.5 |
| H05 | ○ | Bは無駄に伸ばして理解を妨げてる。Aが良い | Sarashina3 mini | Claude Opus 5.5 / Sarashina3 mini | × / ○ | × / × | ○ / ○ | Claude Opus 5.5 |
| H07 | ○ | 用途による。文章としてはAで十分だと思うが、チラシなどの場合はBとして構成されていた方がいいかな。 | 差なし | Claude Opus 5.5 / Claude Opus 5.5 | × / × | × / × | ○ / ○ | Claude Opus 5.5 |
| H09 | ○ | Bやな。 | Claude Opus 5.5 | Claude Opus 5.5 / Claude Opus 5.5 | ○ / ○ | × / × | × / × | 差なし |

判定1 は Sarashina を回答 1、判定2 は Opus を回答 1 に置いた判定。GPT の最終結果は、意味の判定を優先して決めた勝敗（引き分けは「差なし」）。
