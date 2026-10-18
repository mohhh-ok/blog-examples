# Sarashina3 mini と Claude Opus 5.5 の日本語比較

SB Intuitions の Sarashina3 mini（API）と Anthropic の Claude Opus 5.5 に、同じ日本語の問題 40 問を出して出力を並べ、
GPT に一対比較で判定させる。書き直し 10 問は筆者本人も盲検で判定する。

記事: [Sarashina3 miniとClaude Opus 5.5に同じ日本語の問題40問を出して比べた](https://mohhh-ok.github.io/blog/posts/2026/10-18-aisarashina3-miniとclaude-opus-55に同じ日本語の問題40問を出して比べた/)

Sarashina は API で使えるのが mini だけなので、Anthropic の最上位に近いモデルと Sarashina の小さいモデルの比較になる。

## 問題（`data/problems.jsonl`、40 問）

| カテゴリ | 問題数 | 素材 |
|---|---|---|
| 書き直し | 10 | 法令 3（e-Gov 法令検索）・最高裁判決 2（裁判所の裁判例検索）・自作の悪文 5 |
| 敬語 | 4 | 自作（社名・人名は架空） |
| 自由作文 | 4 | 自作 |
| 要約 | 4 | 青空文庫（蜘蛛の糸・手袋を買いに・夢十夜 第一夜・よだかの星。著者はいずれも没後 70 年以上） |
| ニュアンス | 4 | 自作 |
| 漢字の読み | 14 | 自作。難読語 8 と、文脈で読みが決まる同形異音語 6。正誤は機械で採点 |

- 入力には第三者の著作物と個人情報を入れていない。法令と判決は著作権法 13 条で権利の目的とならない。各問の出典 URL と根拠は `source` に書いてある
- 判決は理由のうち人名を含まない部分を使った
- 漢字の読みに SB Intuitions 製のベンチマーク（JKYB）は使っていない
- 自作の問題（20 問）は Claude Opus 5.5 が書いた。Opus に合う問題になっている可能性がある
- 要約の 4 作品は有名なので、両モデルとも本文を覚えている可能性がある

## 条件

| | Sarashina3 mini | Claude Opus 5.5 |
|---|---|---|
| モデル名 | `sarashina3-mini` | `claude-opus-5-5` |
| エンドポイント | `POST https://api.sarashina.ai/v1/chat/completions` | `POST https://api.anthropic.com/v1/messages` |
| システムプロンプト | なし | なし |
| サンプリング | 既定（temperature 0.7・top_p 0.9・repetition_penalty 1.05） | 既定（指定できない） |
| thinking | なし | adaptive（切れない）。`output_config.effort = "low"` で最小にした |
| 出力上限 | `max_completion_tokens = 8000` | `max_tokens = 8000`（thinking の分を含む） |

「temperature を揃える」と「Opus の thinking を切る」は、Opus 5.5 の API が受け付けないためできなかった。
2026-10-18 に送ったときの返答は次のとおり。

- `temperature: 0.7` を送ると 400: `` `temperature` is deprecated for this model. ``
- `thinking: {"type": "disabled"}` を送ると 400: `"thinking.type.disabled" is not supported for this model. Use "thinking.type.adaptive" and "output_config.effort" to control thinking behavior.`

そこで両モデルとも各社の既定のサンプリングで揃え、Opus の thinking は effort を最も低い `low` にした。
Opus が thinking に使ったトークン数は、レスポンスの `usage.output_tokens_details.thinking_tokens` として問題ごとに保存してある。
Opus には別モデルへのフォールバック（`fallbacks`）を付けていない。比較対象のモデルが入れ替わらないようにするため。

Sarashina3 mini は 6 RPM・バースト不可なので、リクエストは逐次で、開始間隔を 12 秒空けた。429 が返ったら `Retry-After` 秒待つ。

## 判定

- GPT（`gpt-6.1-sol`。2026-10-18 に OpenAI の `/v1/models` で一番新しい主力モデル）にモデル名を伏せて一対比較させた
- 回答 1・回答 2 の左右を入れ替えて 2 回判定し、2 回で勝者が同じならその勝ち、食い違えば引き分け
- 判定プロンプトの全文: `prompts/judge_rewrite.txt`（書き直し）、`prompts/judge_general.txt`（それ以外。観点は `scripts/judge.py` の `CRITERIA`）
- 書き直しは、回答ごとに「元の文章の意味が保たれているか・情報が落ちていないか」を先に判定させ、そのうえで読みやすさを比べさせた。
  勝敗は `scripts/aggregate.py` で決める。意味が保たれた回答が片方だけならそちらの勝ち、両方保たれていれば読みやすいほうの勝ち、両方とも意味が変わっていれば引き分け。
  読みやすくても意味を変えた書き直し（二重否定の読み違えなど）を勝ちにしないため
- 漢字の読みは GPT 判定もするが、主な指標は機械採点の正答率。回答から空白と句読点・括弧を除き、正解（複数の読みを許す問題は全部）と一致すれば正解
- 判定役に Claude は使っていない（自己採点の偏りを避けるため）
- 書き直しは筆者本人も盲検で判定した。A/B の割り当ては問題ごとにランダムで、対応表は `output/blind_key.json`
  - 本人の判定は読みやすさだけ。本人が意味の正しさは判定できないと明言したため、意味は GPT の判定を使う
  - 判定したのは 7 問（R01〜R05・R09・R10）。R06〜R08 は判定なしで対象外にした
  - R01 は、判定の前に AI からの途中報告で Sarashina の書き直しの特徴（2 つの条件を別々の禁止として書いた）を本人が聞いていたため盲検ではない。盲検の集計（6 問）から外し、参考として別に載せる
  - シートの「判定:」の行を `scripts/import_human.py` で逐語のまま `output/human_judgement.json` に取り込んだ。各行から読み取った「読みやすいとした回答（A / B）」は Claude が文面から読み取ったもの（R09 の「整理されてるのはBかな」は B とした）
  - `output/results.md` に、本人の判定を GPT の読みやすさの判定（2 回ぶん）・意味の判定と並べた表がある

集計の結果は `output/results.md`。

## 限界

- GPT 判定には出力をそのまま見せている。Sarashina は「もちろんです。」などの前置きを付け、Opus は Markdown の見出しや太字を使うことが多いため、書き方の癖でモデルの見当がつく場合がある
- 本人用の盲検シートだけは、書き方の癖でモデルが分からないよう、両モデルの出力を同じ規則で整えた（`scripts/blind_format.py`。`output/raw` と記事に載せる出力は加工しない）
  1. 区切り線（`---` だけの行）で出力を区間に分ける
  2. 最初の区切り線より前が 1 段落だけで、書き直し作業そのものに触れている（「書き直」「言い換え」を含む）なら、前置きとして削る
  3. 最後の区切り線より後ろが 1 段落だけで、「このように」で始まるなら、締めの地の文として削る
  4. 見出し・太字を外すと「書き直した文章」などのラベルだけになる行は削る
  5. Markdown を外す。区切り線を消し、見出しの `#` と太字の `**` を外し、箇条書きの記号は「・」にする（入れ子は 1 段ごとに全角空白 1 つで字下げ）。行末の改行用の空白 2 つも消す。番号付きの「1.」は残す
  6. 空行が 2 つ以上続くところは 1 つにする
  7. 段落の区切りを揃える。空行を除いた各行を 1 段落として扱い、段落の間を空行 1 つにする。ただし箇条書き（・）と番号付き（1.）の行が続くところは 1 つのまとまりとし、その中の改行はそのまま残す。Sarashina は段落の区切りを改行だけで書くことが多く、Opus は空行で書くため
  - 本文の後ろに付いた補足・解説（Opus の「補足」の節など）は書き直しの一部として残し、Markdown だけを外した
  - 削った部分は問題・モデルごとに `output/blind_key.json` の `removed` に記録してある。`python3 scripts/blind_sheet.py --keep-assignment` で、今の A/B の割り当てのまま同じ整形を再現できる（`--force` は割り当てから作り直す）
  - 整形した後も残る手がかりがある。Opus は補足節を付けることが多く、その中に「太字にしています」のように元の書式に触れた文がある（段落の区切り方の違いは規則 7 で揃えた）

## 再現手順

依存は [uv](https://docs.astral.sh/uv/) がスクリプト先頭の inline metadata から入れる。PDF の本文抽出に `pdftotext`（poppler）を使う。

```bash
set -a; source ../../.env; set +a      # SARASHINA_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY
python3 scripts/fetch_sources.py       # 法令・判決・青空文庫を /tmp/sarashina-blog/src に取得（SRC_DIR で変更可）
python3 scripts/build_problems.py      # data/problems.jsonl を作る
uv run scripts/run_models.py           # output/raw/{sarashina,opus}/<id>.json と output/request_log.jsonl
uv run scripts/judge.py                # output/judge/<id>_{sarashina,opus}-first.json
python3 scripts/blind_sheet.py         # 盲検シート（/tmp/sarashina-blog/blind-sheet.md）と output/blind_key.json
python3 scripts/import_human.py        # 盲検シートの「判定:」の行を output/human_judgement.json に取り込む
python3 scripts/aggregate.py           # output/results.json と output/results.md（API キー不要）
python3 scripts/render_outputs.py      # outputs.md と outputs/<カテゴリ>.md（全問の問題文・出力・判定。API キー不要）
```

`run_models.py` と `judge.py` は保存済みの問題を飛ばすので、途中で止まっても同じコマンドで続きから回る。問題 ID を引数に渡すとその問題だけを回す。

## 出力

- [`outputs.md`](outputs.md): 全問の問題文、両モデルの出力の全文、GPT の判定 2 回の結果と理由、本人の判定、漢字の正誤を、カテゴリごとの `outputs/<カテゴリ>.md` に読める形で載せた目次。出力は `output/raw` から加工せずに、引用の中に転記している（出力に Markdown の見出しや区切り線が入っているため）
  - 公開の前に、Sarashina の利用規約 第12条に沿って、全問の両モデルの出力に暴力的・わいせつ・差別的な表現、第三者の著作物、実在の個人を特定できる情報が含まれていないことを確認した（2026-10-18）。要約の出力にある作品の引用は青空文庫の著作権切れ作品だけ。K01 の署名例にあるメールアドレスは、問題で与えた架空の社名から作られたドメインと伏せ字（〇〇・xxxx）で、加工せずに載せている
- `output/raw/<model>/<id>.json`: 送ったリクエスト（モデル名・パラメータ）、送信日時、API のレスポンス JSON をそのまま
- `output/request_log.jsonl`: 全リクエストの開始・終了時刻と HTTP ステータス（429 なら `retry_after`）
- `output/judge/<id>_<回答1に置いたモデル>-first.json`: 判定プロンプト全文、GPT の判定（理由つき）、レスポンス JSON
- `output/results.json` / `output/results.md`: 集計
- `output/blind_key.json`: 盲検シートの A/B とモデルの対応表
- `output/human_judgement.json`: 本人の判定（シートの「判定:」の行を逐語で）
